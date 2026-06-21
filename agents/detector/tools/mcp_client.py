# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Cliente del servidor MCP de pyATS para el Agente Detector.

Carga las herramientas que expone el servidor `pyATS_MCP` (FastMCP) y las
convierte en herramientas LangChain listas para enlazarse al grafo ReAct
del detector. De esta forma el agente consulta la red real (vía pyATS) en
lugar de los datos *dummy*.
"""

import logging

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from config.config import (
    PYATS_MCP_HOST,
    PYATS_MCP_PORT,
    PYATS_MCP_TRANSPORT,
    PYATS_MCP_URL,
)

logger = logging.getLogger("packetpanic.detector.mcp")

# Mapea el transporte del servidor pyATS al nombre que usa
# langchain-mcp-adapters y a la ruta HTTP correspondiente.
_TRANSPORT_MAP = {
    "http": ("streamable_http", "/mcp"),
    "streamable_http": ("streamable_http", "/mcp"),
    "sse": ("sse", "/sse"),
}


def _resolve_endpoint() -> tuple[str, str]:
    """Determina la URL y el transporte del servidor MCP de pyATS.

    Returns:
        tuple[str, str]: La URL completa y el nombre de transporte que
        entiende langchain-mcp-adapters.
    """
    transport, path = _TRANSPORT_MAP.get(
        PYATS_MCP_TRANSPORT.lower(), ("streamable_http", "/mcp")
    )

    if PYATS_MCP_URL:
        return PYATS_MCP_URL, transport

    # `0.0.0.0` es una dirección de escucha, no es ruteable como cliente.
    host = "localhost" if PYATS_MCP_HOST in ("0.0.0.0", "") else PYATS_MCP_HOST
    return f"http://{host}:{PYATS_MCP_PORT}{path}", transport


async def load_pyats_tools() -> list[BaseTool]:
    """Conecta con el servidor MCP de pyATS y devuelve sus herramientas.

    Returns:
        list[BaseTool]: Herramientas LangChain que invocan las operaciones
        de pyATS (listar dispositivos, ejecutar show commands, ping, etc.).
    """
    url, transport = _resolve_endpoint()
    logger.info("Cargando herramientas MCP de pyATS desde %s (%s)", url, transport)

    client = MultiServerMCPClient(
        {
            "pyats": {
                "url": url,
                "transport": transport,
            }
        }
    )
    tools = await client.get_tools()
    logger.info("Herramientas MCP de pyATS cargadas: %s", [t.name for t in tools])
    return tools
