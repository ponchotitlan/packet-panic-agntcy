# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Herramientas LangChain que exponen la red al Agente Detector.

Estas son envolturas finas sobre `detector.tools.dummy_network`. Cuando
migres a un servidor MCP, mantén estas firmas y cambia el cuerpo por
llamadas al cliente MCP; el grafo del detector no necesitará cambios.
"""

import json

from langchain_core.tools import tool

from detector.tools import dummy_network


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


# Lista de herramientas que se enlazan al LLM del detector.
DETECTOR_TOOLS = [list_devices, device_health, interface_stats, link_diagnostics]
