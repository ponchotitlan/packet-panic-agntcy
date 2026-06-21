# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Agente Supervisor del NOC.

El supervisor es el cerebro de orquestación: recibe la consulta del
operador, decide si necesita datos de la red y, en ese caso, delega en el
Agente Detector vía A2A (sobre SLIM por defecto). Finalmente sintetiza una
respuesta clara para el operador.
"""

import functools
import json
import logging
from uuid import uuid4

from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    TextPart,
)
from agntcy_app_sdk.factory import AgntcyFactory
from agntcy_app_sdk.semantic.a2a.protocol import A2AProtocol
from ioa_observe.sdk.decorators import agent
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from common.directory import discover_agent_by_skill
from common.llm import get_llm
from config.config import (
    A2A_REQUEST_TIMEOUT,
    DEFAULT_MESSAGE_TRANSPORT,
    TRANSPORT_SERVER_ENDPOINT,
)
from supervisor.errors import RemoteAgentNoResponseError, TransportTimeoutError

logger = logging.getLogger("packetpanic.supervisor.agent")

# Capacidad OASF con la que el supervisor descubre al detector en el directorio
# (en lugar de importar su AgentCard local).
_DETECTOR_SKILL = "performance_monitoring"

_SUPERVISOR_SYSTEM_PROMPT = (
    "Eres el Agente Supervisor de un NOC (Network Operations Center). "
    "Atiendes a un operador humano. No tienes acceso directo a los "
    "dispositivos: para obtener datos de la red debes delegar en el Agente "
    "Detector mediante la herramienta `query_detector`.\n"
    "Reglas:\n"
    "- Si la consulta requiere telemetría, inventario o diagnóstico de la "
    "red, llama a `query_detector` con una instrucción clara y específica.\n"
    "- Si la consulta es general o conversacional, respóndela directamente.\n"
    "- Cuando recibas la respuesta del detector, redáctala para el operador "
    "en español, de forma breve, técnica y accionable."
)


def _build_send_message_request(prompt: str) -> SendMessageRequest:
    """Construye una solicitud A2A de envío de mensaje a partir de texto."""
    return SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message=Message(
                messageId=str(uuid4()),
                role=Role.user,
                parts=[Part(TextPart(text=prompt))],
            ),
        ),
    )


def _parse_a2a_response(response: object) -> str:
    """Extrae el texto de una respuesta A2A de forma tolerante a su forma.

    Args:
        response: Objeto devuelto por `client.send_message`.

    Returns:
        str: Texto concatenado de las partes del mensaje.

    Raises:
        RemoteAgentNoResponseError: Si no se encuentra texto utilizable.
    """
    result = getattr(getattr(response, "root", response), "result", response)

    # El resultado puede ser un Message (con parts) o un Task (con history).
    candidates = []
    if hasattr(result, "parts") and result.parts:
        candidates = result.parts
    elif hasattr(result, "history") and result.history:
        last = result.history[-1]
        candidates = getattr(last, "parts", []) or []

    texts: list[str] = []
    for part in candidates:
        inner = getattr(part, "root", part)
        text = getattr(inner, "text", None)
        if text:
            texts.append(text)

    if not texts:
        raise RemoteAgentNoResponseError("El detector no devolvió texto.")
    return "\n".join(texts)


@agent(name="supervisor_agent", description="Supervisor del NOC que delega en el detector")
class SupervisorAgent:
    """Orquesta la conversación y la delegación hacia el detector."""

    def __init__(self, factory: AgntcyFactory) -> None:
        self.factory = factory
        # Descubre al detector en el Agent Directory por su capacidad OASF.
        detector_card = discover_agent_by_skill(_DETECTOR_SKILL)
        self._detector_topic = A2AProtocol.create_agent_topic(detector_card)
        self._tools = [self._make_query_detector_tool()]
        self._llm = get_llm().bind_tools(self._tools)

    @property
    def detector_topic(self) -> str:
        """Tópico A2A del detector descubierto en el Agent Directory."""
        return self._detector_topic

    def _make_query_detector_tool(self):
        """Crea la herramienta LangChain que delega en el detector."""

        agent_self = self

        @tool
        async def query_detector(instruction: str) -> str:
            """Envía una instrucción al Agente Detector del NOC para obtener
            inventario, salud, contadores de interfaz o diagnóstico de
            enlaces, y devuelve su respuesta."""
            return await agent_self.send_to_detector(instruction)

        return query_detector

    async def send_to_detector(self, instruction: str) -> str:
        """Envía una instrucción al detector por A2A y devuelve su respuesta.

        Args:
            instruction: Instrucción en lenguaje natural para el detector.

        Returns:
            str: Respuesta textual del detector.

        Raises:
            TransportTimeoutError: Si la solicitud excede el tiempo límite.
            RemoteAgentNoResponseError: Si el detector no devuelve carga útil.
        """
        transport = self.factory.create_transport(
            DEFAULT_MESSAGE_TRANSPORT,
            endpoint=TRANSPORT_SERVER_ENDPOINT,
            # SLIM requiere un nombre ruteable para el enrutamiento punto a punto.
            name="default/default/supervisor",
        )
        # El SDK invoca `transport.request(topic, message)` sin timeout, por lo
        # que usaría el valor por defecto de 6 s. El detector ejecuta un ciclo
        # ReAct con LLM que suele tardar más, así que fijamos el timeout
        # configurado (A2A_REQUEST_TIMEOUT) sobre la instancia del transporte.
        if hasattr(transport, "request"):
            transport.request = functools.partial(
                transport.request, timeout=A2A_REQUEST_TIMEOUT
            )
        client = await self.factory.create_client(
            "A2A",
            agent_topic=self._detector_topic,
            transport=transport,
        )

        request = _build_send_message_request(instruction)
        try:
            response = await client.send_message(request)
        except TimeoutError as exc:
            raise TransportTimeoutError(str(exc)) from exc
        except AttributeError as exc:
            # Cuando la sesión SLIM agota el tiempo de espera, el transporte
            # registra el error y devuelve `None`. El protocolo A2A intenta
            # entonces acceder a `response.payload` sobre ese `None`, lo que
            # produce un `AttributeError` dentro de `send_message`. Lo
            # tratamos como el timeout que realmente es.
            raise TransportTimeoutError(
                f"El detector no respondió en {A2A_REQUEST_TIMEOUT} s."
            ) from exc
        if response is None:
            raise TransportTimeoutError(
                f"El detector no respondió en {A2A_REQUEST_TIMEOUT} s."
            )
        return _parse_a2a_response(response)

    async def execute_agent_with_llm(self, user_prompt: str) -> str:
        """Procesa la consulta del operador, delegando si es necesario.

        Args:
            user_prompt: Consulta en lenguaje natural del operador.

        Returns:
            str: Respuesta final redactada para el operador.
        """
        messages = [
            SystemMessage(content=_SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        ai_message = await self._llm.ainvoke(messages)

        # Si el modelo no pidió herramientas, su respuesta es la final.
        if not ai_message.tool_calls:
            return ai_message.content

        messages.append(ai_message)

        # Ejecuta cada llamada a `query_detector` y agrega el resultado.
        # Anthropic exige que cada `tool_use` sea seguido por un `tool_result`
        # con el mismo id, por lo que usamos `ToolMessage` (no `HumanMessage`).
        for call in ai_message.tool_calls:
            instruction = call["args"].get("instruction", user_prompt)
            logger.info("Supervisor delega en el detector: %s", instruction)
            try:
                detector_reply = await self.send_to_detector(instruction)
            except (TransportTimeoutError, RemoteAgentNoResponseError) as exc:
                detector_reply = f"El detector no respondió correctamente: {exc}"

            messages.append(
                ToolMessage(content=detector_reply, tool_call_id=call["id"])
            )

        # Segunda pasada: el LLM sintetiza la respuesta final para el operador.
        final = await get_llm().ainvoke(messages)
        return final.content
