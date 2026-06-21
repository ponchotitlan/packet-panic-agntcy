# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Fuente de datos *dummy* de la red para el Agente Detector.

Este módulo simula el acceso real a los dispositivos del NOC. Cuando
conectes un servidor MCP más adelante, solo tendrás que reemplazar las
funciones de este archivo (`get_device_inventory`, `get_interface_stats`,
`diagnose_link`, `get_device_health`) por llamadas al cliente MCP.

Los datos son *determinísticos*: se generan con una semilla derivada del
nombre del dispositivo/interfaz, de modo que las consultas repetidas
devuelvan siempre el mismo resultado durante una demo.
"""

from __future__ import annotations

import hashlib
from typing import Any

# Inventario simulado del NOC. Cada dispositivo vive en un sitio y tiene
# una lista de interfaces. Esto es lo que un servidor MCP expondría.
_INVENTORY: dict[str, dict[str, Any]] = {
    "core-rtr-01": {
        "site": "DC-1",
        "role": "core-router",
        "vendor": "Cisco",
        "model": "ASR-9000",
        "mgmt_ip": "10.0.1.1",
        "interfaces": ["TenGigE0/0/0/0", "TenGigE0/0/0/1", "Bundle-Ether1"],
    },
    "core-rtr-02": {
        "site": "DC-2",
        "role": "core-router",
        "vendor": "Juniper",
        "model": "MX480",
        "mgmt_ip": "10.0.2.1",
        "interfaces": ["xe-0/0/0", "xe-0/0/1", "ae0"],
    },
    "dist-sw-01": {
        "site": "DC-1",
        "role": "distribution-switch",
        "vendor": "Arista",
        "model": "7050X3",
        "mgmt_ip": "10.0.1.10",
        "interfaces": ["Ethernet1", "Ethernet2", "Port-Channel1"],
    },
    "edge-fw-01": {
        "site": "DC-2",
        "role": "firewall",
        "vendor": "Palo Alto",
        "model": "PA-5220",
        "mgmt_ip": "10.0.2.20",
        "interfaces": ["ethernet1/1", "ethernet1/2"],
    },
}


def _seed(*parts: str) -> int:
    """Genera una semilla entera estable a partir de varias cadenas."""
    raw = "|".join(parts).encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest(), 16)


def _scaled(seed: int, offset: int, low: float, high: float) -> float:
    """Mapea una semilla a un valor flotante dentro de [low, high]."""
    bucket = (seed >> (offset * 8)) % 1000 / 1000.0
    return round(low + bucket * (high - low), 2)


def get_device_inventory() -> list[dict[str, Any]]:
    """Lista todos los dispositivos administrados por el NOC.

    Returns:
        list[dict]: Inventario con sitio, rol, fabricante e interfaces.
    """
    return [{"device": name, **meta} for name, meta in _INVENTORY.items()]


def get_device_health(device: str) -> dict[str, Any]:
    """Devuelve métricas de salud simuladas para un dispositivo.

    Args:
        device: Nombre del dispositivo (por ejemplo, "core-rtr-01").

    Returns:
        dict: CPU, memoria, temperatura, uptime y estado general. Si el
        dispositivo no existe, devuelve un error estructurado.
    """
    meta = _INVENTORY.get(device)
    if not meta:
        return {"error": f"Dispositivo desconocido: {device}", "known": list(_INVENTORY)}

    seed = _seed(device, "health")
    cpu = _scaled(seed, 1, 5, 95)
    mem = _scaled(seed, 2, 20, 90)
    temp = _scaled(seed, 3, 28, 68)
    status = "healthy"
    if cpu > 85 or mem > 85 or temp > 60:
        status = "degraded"

    return {
        "device": device,
        "site": meta["site"],
        "cpu_utilization_pct": cpu,
        "memory_utilization_pct": mem,
        "temperature_c": temp,
        "uptime_days": int(_scaled(seed, 4, 1, 400)),
        "status": status,
    }


def get_interface_stats(device: str, interface: str) -> dict[str, Any]:
    """Devuelve contadores simulados de una interfaz.

    Args:
        device: Nombre del dispositivo.
        interface: Nombre de la interfaz (por ejemplo, "TenGigE0/0/0/0").

    Returns:
        dict: Estado operativo, utilización, errores y descartes. Si el
        dispositivo o la interfaz no existen, devuelve un error.
    """
    meta = _INVENTORY.get(device)
    if not meta:
        return {"error": f"Dispositivo desconocido: {device}", "known": list(_INVENTORY)}
    if interface not in meta["interfaces"]:
        return {
            "error": f"Interfaz desconocida en {device}: {interface}",
            "known": meta["interfaces"],
        }

    seed = _seed(device, interface, "iface")
    in_errors = int(_scaled(seed, 1, 0, 500))
    out_errors = int(_scaled(seed, 2, 0, 300))
    utilization = _scaled(seed, 3, 1, 99)
    oper_status = "up" if seed % 11 != 0 else "down"

    return {
        "device": device,
        "interface": interface,
        "oper_status": oper_status,
        "admin_status": "up",
        "speed_gbps": 10,
        "utilization_pct": utilization,
        "in_errors": in_errors,
        "out_errors": out_errors,
        "in_discards": int(_scaled(seed, 4, 0, 200)),
        "out_discards": int(_scaled(seed, 5, 0, 150)),
    }


def diagnose_link(device: str, interface: str) -> dict[str, Any]:
    """Ejecuta un diagnóstico de enlace simulado (latencia y pérdida).

    Args:
        device: Nombre del dispositivo.
        interface: Nombre de la interfaz a diagnosticar.

    Returns:
        dict: Latencia, jitter, pérdida de paquetes y veredicto. Si el
        dispositivo o la interfaz no existen, devuelve un error.
    """
    stats = get_interface_stats(device, interface)
    if "error" in stats:
        return stats

    seed = _seed(device, interface, "link")
    packet_loss = _scaled(seed, 1, 0, 8)
    latency = _scaled(seed, 2, 0.4, 45)
    jitter = _scaled(seed, 3, 0.1, 12)

    if stats["oper_status"] == "down":
        verdict = "critical: enlace caído (oper_status=down)"
    elif packet_loss > 2 or latency > 30:
        verdict = "warning: degradación detectada (pérdida/latencia altas)"
    else:
        verdict = "ok: el enlace opera dentro de los parámetros normales"

    return {
        "device": device,
        "interface": interface,
        "packet_loss_pct": packet_loss,
        "latency_ms": latency,
        "jitter_ms": jitter,
        "oper_status": stats["oper_status"],
        "verdict": verdict,
    }
