# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Descubrimiento de agentes en el Agent Directory (registros OASF).

En lugar de importar el `AgentCard` local de un agente peer, los consumidores
descubren las capacidades disponibles a partir de los registros OASF del
directorio. La carpeta `oasf/agents/` es la fuente que se publica en el AGNTCY
Agent Directory (ver `scripts/directory_demo.sh`); cada registro OASF embebe su
`AgentCard` A2A en el módulo `integration/a2a`, por lo que reconstruir el card
descubierto es directo.
"""

import json
import logging
from pathlib import Path

from a2a.types import AgentCard

from config.config import OASF_RECORDS_DIR

logger = logging.getLogger("packetpanic.directory")

# Nombre del módulo OASF que transporta el AgentCard A2A embebido.
_A2A_MODULE_NAME = "integration/a2a"


class AgentNotFoundError(Exception):
    """Ningún registro OASF del directorio coincide con la búsqueda."""


def _load_records(records_dir: Path) -> list[dict]:
    """Carga los registros OASF (`*.json`) del directorio indicado.

    Args:
        records_dir: Carpeta que contiene los registros OASF.

    Returns:
        list[dict]: Registros OASF decodificados; los ilegibles se omiten.
    """
    records: list[dict] = []
    for path in sorted(records_dir.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Registro OASF ilegible %s: %s", path, exc)
    return records


def _to_agent_card(record: dict) -> AgentCard | None:
    """Extrae el `AgentCard` A2A embebido en un registro OASF.

    Args:
        record: Registro OASF decodificado.

    Returns:
        AgentCard | None: El card reconstruido, o `None` si el registro no
        publica un módulo `integration/a2a` con `card_data`.
    """
    for module in record.get("modules", []):
        if module.get("name") == _A2A_MODULE_NAME:
            card_data = (module.get("data") or {}).get("card_data")
            if card_data:
                return AgentCard.model_validate(card_data)
    return None


def _capabilities(record: dict) -> str:
    """Devuelve skills y dominios OASF del registro como texto buscable."""
    skills = [skill.get("name", "") for skill in record.get("skills", [])]
    domains = [domain.get("name", "") for domain in record.get("domains", [])]
    return " ".join(skills + domains).lower()


def discover_agents(records_dir: Path | None = None) -> list[AgentCard]:
    """Descubre todos los agentes A2A publicados en el directorio.

    Args:
        records_dir: Carpeta de registros; por defecto `OASF_RECORDS_DIR`.

    Returns:
        list[AgentCard]: Cards de los agentes descubiertos.
    """
    base = records_dir or Path(OASF_RECORDS_DIR)
    cards: list[AgentCard] = []
    for record in _load_records(base):
        card = _to_agent_card(record)
        if card is not None:
            cards.append(card)
    return cards


def discover_agent_by_skill(skill: str, records_dir: Path | None = None) -> AgentCard:
    """Descubre el primer agente cuyo registro OASF declara una capacidad.

    La búsqueda es por subcadena contra las skills y los dominios OASF del
    registro (p. ej. "performance_monitoring" o "network_operations").

    Args:
        skill: Subcadena de la capacidad OASF a buscar.
        records_dir: Carpeta de registros; por defecto `OASF_RECORDS_DIR`.

    Returns:
        AgentCard: Card A2A del agente descubierto.

    Raises:
        AgentNotFoundError: Si ningún registro del directorio coincide.
    """
    base = records_dir or Path(OASF_RECORDS_DIR)
    needle = skill.lower()
    for record in _load_records(base):
        if needle in _capabilities(record):
            card = _to_agent_card(record)
            if card is not None:
                logger.info(
                    "Directorio: descubierto '%s' por capacidad '%s'.",
                    card.name,
                    skill,
                )
                return card
    raise AgentNotFoundError(
        f"Ningún agente del directorio declara la capacidad '{skill}'."
    )
