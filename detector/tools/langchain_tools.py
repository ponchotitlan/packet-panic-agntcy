# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Herramientas LangChain que exponen la red al Agente Detector.

El detector prefiere las herramientas reales del servidor MCP de pyATS
(`detector.tools.mcp_client`). Si el servidor MCP está deshabilitado o no se
puede alcanzar, recurre a las envolturas *dummy* sobre
`detector.tools.dummy_network` para que la demo siga funcionando.
"""

import json
import logging

from langchain_core.tools import BaseTool, tool

from config.config import PYATS_MCP_ENABLED
from detector.tools import dummy_network
from detector.tools.mcp_client import load_pyats_tools

logger = logging.getLogger("packetpanic.detector.tools")


@tool
def list_devices() -> str:
    """Lista todos los dispositivos administrados por el NOC con su sitio,
    rol, fabricante e interfaces disponibles."""
    return json.dumps(dummy_network.get_device_inventory(), ensure_ascii=False)


@tool
def device_health(device: str) -> str:
    """Obtiene métricas de salud (CPU, memoria, temperatura, uptime) de un
    dispositivo por su nombre, por ejemplo "core-rtr-01"."""
    return json.dumps(dummy_network.get_device_health(device), ensure_ascii=False)


@tool
def interface_stats(device: str, interface: str) -> str:
    """Obtiene contadores de una interfaz (estado, utilización, errores y
    descartes) dado el dispositivo y el nombre de la interfaz."""
    return json.dumps(
        dummy_network.get_interface_stats(device, interface), ensure_ascii=False
    )


@tool
def link_diagnostics(device: str, interface: str) -> str:
    """Ejecuta un diagnóstico de enlace (latencia, jitter, pérdida de
    paquetes y veredicto) para una interfaz de un dispositivo."""
    return json.dumps(
        dummy_network.diagnose_link(device, interface), ensure_ascii=False
    )


# Herramientas *dummy* usadas como respaldo si el servidor MCP no está
# disponible.
DUMMY_TOOLS = [list_devices, device_health, interface_stats, link_diagnostics]


async def get_detector_tools() -> list[BaseTool]:
    """Devuelve las herramientas de red para el Agente Detector.

    Prefiere las herramientas reales del servidor MCP de pyATS. Si el MCP
    está deshabilitado o no responde, recurre a las herramientas *dummy*.

    Returns:
        list[BaseTool]: Herramientas a enlazar al grafo del detector.
    """
    if not PYATS_MCP_ENABLED:
        logger.info("MCP de pyATS deshabilitado; usando herramientas dummy.")
        return DUMMY_TOOLS

    try:
        mcp_tools = await load_pyats_tools()
    except Exception as exc:  # noqa: BLE001 - degradar a dummy ante fallo MCP
        logger.warning(
            "No se pudo conectar al MCP de pyATS (%s); usando herramientas dummy.",
            exc,
        )
        return DUMMY_TOOLS

    if not mcp_tools:
        logger.warning(
            "El MCP de pyATS no expuso herramientas; usando herramientas dummy."
        )
        return DUMMY_TOOLS

    return mcp_tools
