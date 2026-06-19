# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""AgentCard del Detector: el manifiesto A2A de sus capacidades."""

from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from config.config import DETECTOR_AGENT_HOST, DETECTOR_AGENT_PORT

AGENT_SKILL = AgentSkill(
    id="network_diagnostics",
    name="Diagnóstico de Red",
    description=(
        "Consulta inventario, salud de dispositivos, contadores de "
        "interfaces y diagnostica enlaces (pérdida de paquetes, latencia)."
    ),
    tags=["noc", "diagnostico", "red", "telemetria"],
    examples=[
        "¿Hay pérdida de paquetes en la interfaz TenGigE0/0/0/0 de core-rtr-01?",
        "Dame la salud de core-rtr-02",
        "Lista los dispositivos del sitio DC-2",
        "Revisa los errores de la interfaz ae0 en core-rtr-02",
    ],
)

AGENT_CARD = AgentCard(
    name="NOC Detector Agent",
    id="noc-detector-agent",
    description=(
        "Agente con acceso a los dispositivos del NOC. Ejecuta diagnósticos "
        "de red en vivo y devuelve telemetría accionable."
    ),
    version="0.1.0",
    url=f"http://{DETECTOR_AGENT_HOST}:{DETECTOR_AGENT_PORT}/",
    capabilities=AgentCapabilities(streaming=False),
    skills=[AGENT_SKILL],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
)
