# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Servidor del Agente Detector.

Expone el `DetectorAgentExecutor` como servidor A2A. El transporte es
configurable: por defecto usa SLIM (a través de la AgntcyFactory). Si se
fija `DEFAULT_MESSAGE_TRANSPORT=A2A`, sirve por HTTP nativo con Starlette.
"""

import asyncio
import logging

import config.logging_config  # noqa: F401 - configura logging al importar
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from agntcy_app_sdk.app_sessions import AppContainer
from agntcy_app_sdk.factory import AgntcyFactory
from agntcy_app_sdk.semantic.a2a.protocol import A2AProtocol
from dotenv import load_dotenv
from ioa_observe.sdk import Observe
from ioa_observe.sdk.instruments import Instruments
from uvicorn import Config, Server

from config.config import (
    DEFAULT_MESSAGE_TRANSPORT,
    DETECTOR_AGENT_HOST,
    DETECTOR_AGENT_PORT,
    OTEL_SDK_DISABLED,
    OTLP_HTTP_ENDPOINT,
    TRANSPORT_SERVER_ENDPOINT,
)
from agents.detector.agent import DetectorAgent
from agents.detector.agent_executor import DetectorAgentExecutor
from agents.detector.card import AGENT_CARD

load_dotenv()

logger = logging.getLogger("packetpanic.detector.server")

# Inicializa el Observe SDK (OpenTelemetry) y exporta las trazas al colector
# OTLP/HTTP antes de crear la factory para instrumentar correctamente.
#
# Para la demo dejamos solo la instrumentación de LangChain: así las trazas
# muestran con claridad el uso del LLM, las herramientas (MCP de pyATS) y los
# spans de agente. Las llamadas agente-a-agente (A2A/SLIM) y los decoradores
# `@agent`/`@graph` se instrumentan aparte (vía la AgntcyFactory y el SDK), por
# lo que se conservan. Restringir aquí evita el ruido de los instrumentadores
# HTTP (requests/urllib3) que generan un span por cada petición saliente.
Observe.init(
    "packetpanic.detector",
    api_endpoint=OTLP_HTTP_ENDPOINT,
    enabled=not OTEL_SDK_DISABLED,
    instruments={Instruments.LANGCHAIN},
)

# Factory multi-protocolo/multi-transporte de AGNTCY.
factory = AgntcyFactory("packetpanic.detector", enable_tracing=not OTEL_SDK_DISABLED)


async def main() -> None:
    """Arranca el servidor del detector con el transporte configurado."""
    # Carga las herramientas del MCP de pyATS y construye el grafo en el
    # arranque, para que la primera invocación del supervisor no pague el
    # coste de inicialización.
    agent = DetectorAgent()
    await agent.initialize()

    request_handler = DefaultRequestHandler(
        agent_executor=DetectorAgentExecutor(agent),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=AGENT_CARD, http_handler=request_handler
    )

    if DEFAULT_MESSAGE_TRANSPORT == "A2A":
        logger.info(
            "Detector escuchando por HTTP en %s:%s",
            DETECTOR_AGENT_HOST,
            DETECTOR_AGENT_PORT,
        )
        config = Config(
            app=server.build(),
            host=DETECTOR_AGENT_HOST,
            port=DETECTOR_AGENT_PORT,
            loop="asyncio",
        )
        await Server(config).serve()
        return

    # Transporte conectable (SLIM por defecto) vía la AgntcyFactory.
    topic = A2AProtocol.create_agent_topic(AGENT_CARD)
    transport = factory.create_transport(
        DEFAULT_MESSAGE_TRANSPORT,
        endpoint=TRANSPORT_SERVER_ENDPOINT,
        # SLIM requiere un nombre ruteable (org/namespace/agente).
        name="default/default/" + topic,
    )

    app_session = factory.create_app_session()
    app_session.add_app_container(
        "packetpanic-detector",
        AppContainer(server, transport=transport, topic=topic),
    )

    logger.info(
        "Detector registrado en %s vía %s (tópico: %s)",
        TRANSPORT_SERVER_ENDPOINT,
        DEFAULT_MESSAGE_TRANSPORT,
        topic,
    )
    await app_session.start_session("packetpanic-detector", keep_alive=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Detector detenido por el usuario.")
