# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Agente Detector: grafo LangGraph con acceso (simulado) a la red.

El detector es un agente tipo ReAct: recibe una instrucción en lenguaje
natural del supervisor, decide qué herramientas de red invocar y devuelve
un diagnóstico claro. Las herramientas hoy usan datos *dummy*; mañana
pueden apuntar a un servidor MCP sin tocar este grafo.
"""

import logging

from langgraph.prebuilt import create_react_agent
from ioa_observe.sdk.decorators import agent, graph

from common.llm import get_llm
from detector.tools.langchain_tools import DETECTOR_TOOLS

logger = logging.getLogger("packetpanic.detector.agent")

_SYSTEM_PROMPT = (
    "Eres un Agente Detector de un NOC (Network Operations Center). "
    "Tienes acceso directo a los dispositivos de red mediante herramientas. "
    "Tu trabajo es:\n"
    "1. Interpretar la solicitud del supervisor (un dispositivo, una "
    "interfaz, un sitio o un síntoma).\n"
    "2. Llamar a las herramientas adecuadas para obtener datos reales de la "
    "red (inventario, salud, contadores de interfaz o diagnóstico de enlace).\n"
    "3. Responder con un resumen técnico breve y accionable en español: "
    "incluye los valores relevantes (utilización, errores, pérdida de "
    "paquetes, latencia) y un veredicto claro.\n"
    "Si no encuentras el dispositivo o la interfaz, dilo explícitamente y "
    "sugiere los nombres válidos que devuelven las herramientas. "
    "No inventes datos: básate solo en lo que devuelven las herramientas."
)


@agent(name="detector_agent", description="Agente con acceso a los dispositivos del NOC")
class DetectorAgent:
    """Encapsula el grafo ReAct del detector."""

    def __init__(self) -> None:
        self._agent = self.build_graph()

    @graph(name="detector_graph")
    def build_graph(self):
        """Construye el agente ReAct con las herramientas de red enlazadas."""
        return create_react_agent(
            get_llm(),
            tools=DETECTOR_TOOLS,
            prompt=_SYSTEM_PROMPT,
        )

    async def ainvoke(self, prompt: str) -> str:
        """Procesa una instrucción y devuelve el diagnóstico en texto.

        Args:
            prompt: Instrucción en lenguaje natural enviada por el supervisor.

        Returns:
            str: Diagnóstico técnico generado por el agente.
        """
        logger.debug("Detector recibió: %s", prompt)
        result = await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )
        messages = result.get("messages", [])
        if not messages:
            return "El detector no produjo respuesta."
        return messages[-1].content
