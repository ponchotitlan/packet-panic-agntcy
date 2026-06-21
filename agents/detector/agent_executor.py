# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Adaptador A2A: conecta el protocolo A2A con el grafo del Detector."""

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import UnsupportedOperationError
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from detector.agent import DetectorAgent

logger = logging.getLogger("packetpanic.detector.executor")


class DetectorAgentExecutor(AgentExecutor):
    """Ejecuta el `DetectorAgent` en respuesta a las solicitudes A2A."""

    def __init__(self, agent: DetectorAgent | None = None) -> None:
        self.agent = agent or DetectorAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Procesa una solicitud A2A y publica el diagnóstico como evento.

        Args:
            context: Contexto de la solicitud con el mensaje del supervisor.
            event_queue: Cola para emitir la respuesta del agente.
        """
        prompt = context.get_user_input()
        if not prompt:
            logger.warning("Solicitud sin prompt válido.")
            await event_queue.enqueue_event(
                new_agent_text_message("No se recibió una instrucción válida.")
            )
            return

        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        try:
            diagnosis = await self.agent.ainvoke(prompt)
            await event_queue.enqueue_event(new_agent_text_message(diagnosis))
        except Exception as exc:  # noqa: BLE001 - se reporta como error A2A
            logger.exception("Error al generar el diagnóstico: %s", exc)
            await event_queue.enqueue_event(
                new_agent_text_message(f"Error en el detector: {exc}")
            )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """La cancelación no está soportada por este agente."""
        raise ServerError(error=UnsupportedOperationError())
