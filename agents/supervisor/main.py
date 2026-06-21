# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""API HTTP del Agente Supervisor (FastAPI).

Expone el endpoint `/agent/prompt` que el operador (o la UI) usa para
enviar consultas al NOC. Internamente delega en el `SupervisorAgent`.
"""

import logging

import config.logging_config  # noqa: F401 - configura logging al importar
import uvicorn
from agntcy_app_sdk.factory import AgntcyFactory
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ioa_observe.sdk import Observe
from ioa_observe.sdk.instruments import Instruments
from ioa_observe.sdk.tracing import session_start
from pydantic import BaseModel

from config.config import (
    OTEL_SDK_DISABLED,
    OTLP_HTTP_ENDPOINT,
    SUPERVISOR_HOST,
    SUPERVISOR_PORT,
)
from agents.supervisor.agent import SupervisorAgent
from agents.supervisor.errors import RemoteAgentNoResponseError, TransportTimeoutError

logger = logging.getLogger("packetpanic.supervisor.main")
load_dotenv()

# Inicializa el Observe SDK (OpenTelemetry) y exporta las trazas al colector
# OTLP/HTTP. Debe ejecutarse antes de crear la factory para que el tracing
# quede correctamente instrumentado.
#
# Para la demo dejamos solo la instrumentación de LangChain: así las trazas
# muestran con claridad el uso del LLM, las herramientas (MCP de pyATS) y los
# spans de agente. Las llamadas agente-a-agente (A2A/SLIM) y los decoradores
# `@agent`/`@graph` se instrumentan aparte (vía la AgntcyFactory y el SDK), por
# lo que se conservan. Restringir aquí evita el ruido de los instrumentadores
# HTTP (requests/urllib3) que generan un span por cada petición saliente.
Observe.init(
    "packetpanic.supervisor",
    api_endpoint=OTLP_HTTP_ENDPOINT,
    enabled=not OTEL_SDK_DISABLED,
    instruments={Instruments.LANGCHAIN},
)

# Factory de AGNTCY compartida por el supervisor.
factory = AgntcyFactory("packetpanic.supervisor", enable_tracing=not OTEL_SDK_DISABLED)

app = FastAPI(title="Packet Panic — NOC Supervisor")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supervisor_agent = SupervisorAgent(factory=factory)


@app.on_event("startup")
async def log_detector_registration() -> None:
    """Registra el detector descubierto para verificar la conectividad.

    No es bloqueante ni fatal: solo confirma en los logs que el supervisor
    resolvió al detector en el Agent Directory. Si la línea no aparece, la
    causa de los timeouts está en el descubrimiento/registro, no en el LLM.
    """
    try:
        logger.info(
            "Supervisor listo. Detector descubierto en el tópico A2A: %s",
            supervisor_agent.detector_topic,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo resolver el detector al arrancar: %s", exc)


class PromptRequest(BaseModel):
    """Cuerpo de la solicitud de consulta del operador."""

    prompt: str


@app.post("/agent/prompt")
async def handle_prompt(request: PromptRequest) -> dict:
    """Procesa una consulta del operador a través del supervisor.

    Args:
        request: Contiene el prompt del operador.

    Returns:
        dict: Respuesta del agente y el identificador de sesión de trazas.

    Raises:
        HTTPException: 400 entrada inválida, 504 timeout del detector,
        502 respuesta vacía del detector, 500 otros errores.
    """
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="El prompt no puede estar vacío.")

    try:
        with session_start() as session_id:
            result = await supervisor_agent.execute_agent_with_llm(request.prompt)
            return {"response": result, "session_id": session_id["executionID"]}
    except TransportTimeoutError as exc:
        logger.error("Timeout del detector: %s", exc)
        raise HTTPException(status_code=504, detail="El detector no respondió a tiempo.")
    except RemoteAgentNoResponseError as exc:
        logger.error("Detector sin respuesta: %s", exc)
        raise HTTPException(status_code=502, detail="El detector no devolvió respuesta.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error procesando el prompt: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error interno: {exc}")


@app.get("/health")
async def health_check() -> dict:
    """Endpoint de salud del supervisor."""
    return {"status": "ok"}


@app.get("/suggested-prompts")
async def suggested_prompts() -> dict:
    """Devuelve ejemplos de consultas para la UI."""
    return {
        "prompts": [
            "¿Hay pérdida de paquetes en TenGigE0/0/0/0 de core-rtr-01?",
            "Dame la salud de core-rtr-02",
            "Lista los dispositivos del sitio DC-2",
            "Revisa los errores de la interfaz ae0 en core-rtr-02",
        ]
    }


if __name__ == "__main__":
    uvicorn.run(
        "agents.supervisor.main:app",
        host=SUPERVISOR_HOST,
        port=SUPERVISOR_PORT,
        reload=False,
    )
