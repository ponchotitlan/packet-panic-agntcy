# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Configuración central del sistema de dos agentes para el NOC.

Carga las variables de entorno y expone los parámetros de transporte,
del proveedor de LLM y de los endpoints HTTP de cada agente.
"""

import os

from dotenv import load_dotenv

load_dotenv()  # Carga desde `.env` si existe.

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

# --- Proveedor de LLM (gestionado vía LiteLLM) ---
# Ejemplos: "openai/gpt-4o", "azure/<deployment>", "groq/<modelo>".
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

# --- Observabilidad ---
OTLP_HTTP_ENDPOINT = os.getenv("OTLP_HTTP_ENDPOINT", "http://localhost:4318")
OTEL_SDK_DISABLED = os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true"

# --- Tiempos de espera ---
A2A_REQUEST_TIMEOUT = int(os.getenv("A2A_REQUEST_TIMEOUT", "60"))

# --- Nivel de logs ---
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()
