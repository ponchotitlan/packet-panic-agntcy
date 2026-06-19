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
from uvicorn import Config, Server

from config.config import (
    DEFAULT_MESSAGE_TRANSPORT,
    DETECTOR_AGENT_HOST,
    DETECTOR_AGENT_PORT,
    OTEL_SDK_DISABLED,
    TRANSPORT_SERVER_ENDPOINT,
)
from detector.agent_executor import DetectorAgentExecutor
from detector.card import AGENT_CARD

load_dotenv()

logger = logging.getLogger("packetpanic.detector.server")

# Factory multi-protocolo/multi-transporte de AGNTCY.
factory = AgntcyFactory("packetpanic.detector", enable_tracing=not OTEL_SDK_DISABLED)


async def main() -> None:
    """Arranca el servidor del detector con el transporte configurado."""
    request_handler = DefaultRequestHandler(
        agent_executor=DetectorAgentExecutor(),
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
