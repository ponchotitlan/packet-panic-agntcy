# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Agente Detector: grafo LangGraph con acceso a la red vía pyATS.

El detector es un agente tipo ReAct: recibe una instrucción en lenguaje
natural del supervisor, decide qué herramientas de red invocar y devuelve
un diagnóstico claro. Las herramientas provienen del servidor MCP de pyATS
(`detector.tools.mcp_client`); si el MCP no está disponible, recurre a
datos *dummy*. Como las herramientas MCP se cargan de forma asíncrona, el
grafo se construye de forma perezosa en la primera invocación.
"""

import logging

from langgraph.prebuilt import create_react_agent
from ioa_observe.sdk.decorators import agent, graph

from common.llm import get_llm
from detector.tools.langchain_tools import get_detector_tools

logger = logging.getLogger("packetpanic.detector.agent")

_SYSTEM_PROMPT = (
    "Eres un Agente Detector de un NOC (Network Operations Center). "
    "Tienes acceso directo a los dispositivos de red mediante herramientas "
    "de pyATS (Cisco). Tu trabajo es:\n"
    "1. Interpretar la solicitud del supervisor (un dispositivo, una "
    "interfaz, un sitio o un síntoma).\n"
    "2. Llamar a las herramientas adecuadas para obtener datos reales de la "
    "red. Usa `pyats_run_show_command` para ejecutar comandos show (por "
    "ejemplo 'show interfaces', 'show ip interface brief', 'show version'), "
    "`pyats_ping_from_network_device` para probar conectividad y "
    "`pyats_show_logging` para revisar logs.\n"
    "3. Responder con un resumen técnico breve y accionable en español: "
    "incluye los valores relevantes (utilización, errores, pérdida de "
    "paquetes, latencia, estado de interfaz) y un veredicto claro.\n"
    "Si no encuentras el dispositivo o la interfaz, dilo explícitamente y "
    "sugiere los nombres válidos que devuelven las herramientas. "
    "No inventes datos: básate solo en lo que devuelven las herramientas.\n\n"
    "REGLAS DE SELECCIÓN DE HERRAMIENTAS (obligatorias):\n"
    "- Las herramientas como `pyats_run_show_command`, "
    "`pyats_ping_from_network_device` y `pyats_show_logging` ABREN una "
    "conexión SSH/Telnet a cada dispositivo. Úsalas SOLO cuando necesites "
    "datos en vivo de un dispositivo CONCRETO que el supervisor mencionó.\n"
    "- `pyats_list_devices` SOLO lee el inventario del testbed y NO se "
    "conecta a ningún dispositivo. Es la única herramienta válida para "
    "preguntas sobre inventario, lista de dispositivos, nombres, sitios, "
    "OS, tipo, plataforma o conexiones configuradas.\n"
    "- Cuando la solicitud sea listar/enumerar el inventario o saber qué "
    "dispositivos existen, llama EXCLUSIVAMENTE a `pyats_list_devices` UNA "
    "sola vez y devuelve la lista en un formato legible. NUNCA invoques "
    "herramientas que se conecten a los dispositivos (ni show commands, ni "
    "ping, ni logging) para responder a una solicitud de inventario.\n"
    "- No intentes conectarte a todos los dispositivos. Conéctate únicamente "
    "a los dispositivos estrictamente necesarios para la tarea pedida.\n\n"
    "CONOCIMIENTO DEL DISPOSITIVO (obligatorio antes de enviar comandos):\n"
    "- Antes de ejecutar comandos para leer o aplicar configuración en un "
    "dispositivo, identifica su sistema operativo (OS), tipo, plataforma y "
    "fabricante. Si no los conoces, consúltalos primero con "
    "`pyats_list_devices` (que reporta `os`, `type`, `platform` y "
    "`connections`).\n"
    "- Adapta SIEMPRE la sintaxis de los comandos al OS/fabricante del "
    "dispositivo. Por ejemplo: en IOS/IOS-XE usa 'show ip interface brief', "
    "'show running-config'; en NX-OS usa 'show ip interface brief' y "
    "'show running-config'; en IOS-XR usa 'show ipv4 interface brief' y "
    "'show running-config'; en Junos usa 'show interfaces terse' y "
    "'show configuration'. No asumas comandos de IOS para equipos que no "
    "sean Cisco IOS.\n"
    "- Para aplicar o empujar configuración, usa el modo de configuración y "
    "la sintaxis propios de ese OS/fabricante (por ejemplo, "
    "'configure terminal' en IOS/NX-OS, 'configure' y 'commit' en IOS-XR y "
    "Junos). Verifica que el dispositivo soporte el comando antes de "
    "enviarlo.\n"
    "- Si la sintaxis correcta para ese OS/fabricante es ambigua o el "
    "dispositivo no soporta el comando, dilo explícitamente en lugar de "
    "enviar un comando que pueda fallar o ser rechazado."
)


@agent(name="detector_agent", description="Agente con acceso a los dispositivos del NOC")
class DetectorAgent:
    """Encapsula el grafo ReAct del detector."""

    def __init__(self) -> None:
        # El grafo se construye de forma perezosa porque las herramientas
        # MCP de pyATS se cargan de forma asíncrona.
        self._agent = None

    @graph(name="detector_graph")
    def build_graph(self, tools):
        """Construye el agente ReAct con las herramientas de red enlazadas.

        Args:
            tools: Herramientas de red (MCP de pyATS o dummy de respaldo).

        Returns:
            El grafo ReAct compilado.
        """
        return create_react_agent(
            get_llm(),
            tools=tools,
            prompt=_SYSTEM_PROMPT,
        )

    async def _ensure_agent(self):
        """Construye el grafo en la primera invocación y lo cachea."""
        if self._agent is None:
            tools = await get_detector_tools()
            self._agent = self.build_graph(tools)
        return self._agent

    async def initialize(self) -> None:
        """Carga las herramientas MCP y construye el grafo de forma anticipada.

        Pensado para llamarse una vez al arrancar el servidor, de modo que
        las herramientas del MCP de pyATS se carguen en el init y no en la
        primera invocación del supervisor.
        """
        await self._ensure_agent()

    async def ainvoke(self, prompt: str) -> str:
        """Procesa una instrucción y devuelve el diagnóstico en texto.

        Args:
            prompt: Instrucción en lenguaje natural enviada por el supervisor.

        Returns:
            str: Diagnóstico técnico generado por el agente.
        """
        logger.debug("Detector recibió: %s", prompt)
        agent_graph = await self._ensure_agent()
        result = await agent_graph.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )
        messages = result.get("messages", [])
        if not messages:
            return "El detector no produjo respuesta."
        return messages[-1].content
