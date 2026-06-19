# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Configuración central del sistema de dos agentes para el NOC.

Carga las variables de entorno y expone los parámetros de transporte,
del proveedor de LLM y de los endpoints HTTP de cada agente.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # Carga desde `.env` si existe.

# Raíz del repositorio (dos niveles por encima de este archivo).
_REPO_ROOT = Path(__file__).resolve().parent.parent

# --- Agent Directory (registros OASF) ---
# Carpeta desde la que se descubren agentes por sus capacidades. Coincide con
# la fuente que se publica en el AGNTCY Agent Directory (ver
# `scripts/directory_demo.sh`). Configurable para apuntar, por ejemplo, a un
# volumen montado (`/oasf/agents`).
OASF_RECORDS_DIR = os.getenv("OASF_RECORDS_DIR", str(_REPO_ROOT / "oasf" / "agents"))

# --- Transporte de mensajería (A2A sobre SLIM por defecto) ---
DEFAULT_MESSAGE_TRANSPORT = os.getenv("DEFAULT_MESSAGE_TRANSPORT", "SLIM")
TRANSPORT_SERVER_ENDPOINT = os.getenv(
    "TRANSPORT_SERVER_ENDPOINT", "http://localhost:46357"
)

# --- Agente Detector (servidor A2A) ---
DETECTOR_AGENT_HOST = os.getenv("DETECTOR_AGENT_HOST", "localhost")
DETECTOR_AGENT_PORT = int(os.getenv("DETECTOR_AGENT_PORT", "9999"))

# --- Agente Supervisor (API HTTP / cliente A2A) ---
SUPERVISOR_HOST = os.getenv("SUPERVISOR_HOST", "0.0.0.0")
SUPERVISOR_PORT = int(os.getenv("SUPERVISOR_PORT", "8000"))

# --- Servidor MCP de pyATS (consultas reales a la red) ---
# Cuando está habilitado, el Agente Detector carga sus herramientas desde el
# servidor MCP de pyATS en lugar de los datos *dummy*.
PYATS_MCP_ENABLED = os.getenv("PYATS_MCP_ENABLED", "true").lower() == "true"
# Transporte del servidor MCP: "http" (streamable HTTP, ruta /mcp) o "sse".
PYATS_MCP_TRANSPORT = os.getenv("PYATS_MCP_TRANSPORT", "http")
PYATS_MCP_HOST = os.getenv("PYATS_MCP_HOST", "0.0.0.0")
PYATS_MCP_PORT = int(os.getenv("PYATS_MCP_PORT", "8082"))
# URL completa para alcanzar el servidor MCP. En Docker Compose el host es el
# nombre del servicio (`pyats-mcp`). Si se deja vacía, se deriva de host/puerto.
PYATS_MCP_URL = os.getenv("PYATS_MCP_URL", "")

# --- Proveedor de LLM (gestionado vía LiteLLM) ---
# Ejemplos: "openai/gpt-4o", "azure/<deployment>", "groq/<modelo>".
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

# --- Observabilidad ---
OTLP_HTTP_ENDPOINT = os.getenv("OTLP_HTTP_ENDPOINT", "http://localhost:4318")
OTEL_SDK_DISABLED = os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true"

# --- Tiempos de espera ---
# El detector ejecuta un ciclo ReAct (LLM + herramientas pyATS/MCP) que puede
# tardar bastante, por lo que el valor por defecto es generoso. Ajustable con
# la variable de entorno `A2A_REQUEST_TIMEOUT` (en segundos).
A2A_REQUEST_TIMEOUT = int(os.getenv("A2A_REQUEST_TIMEOUT", "120"))

# --- Nivel de logs ---
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()
