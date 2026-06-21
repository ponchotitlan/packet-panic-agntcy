# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Errores del supervisor y utilidades para clasificarlos."""


class TransportTimeoutError(Exception):
    """El agente remoto no respondió dentro del tiempo permitido."""


class RemoteAgentNoResponseError(Exception):
    """El agente remoto respondió sin una carga útil utilizable."""


def is_timeout_error(exc: BaseException) -> bool:
    """Indica si la excepción corresponde a un timeout de transporte."""
    text = str(exc).lower()
    return isinstance(exc, (TimeoutError, TransportTimeoutError)) or "timeout" in text


def is_no_payload_error(exc: BaseException) -> bool:
    """Indica si la excepción corresponde a una respuesta vacía/ inválida."""
    text = str(exc).lower()
    return isinstance(exc, RemoteAgentNoResponseError) or "no response" in text
