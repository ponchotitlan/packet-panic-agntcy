# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Configuración de logging compartida por ambos agentes."""

import logging

from config.config import LOGGING_LEVEL

_CONFIGURED = False


def setup_logging() -> None:
    """Configura el logging raíz una sola vez.

    Es idempotente: invocarlo varias veces no duplica los handlers.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.basicConfig(
        level=getattr(logging, LOGGING_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    _CONFIGURED = True


# Ejecuta la configuración al importar para que los módulos que solo
# hacen `import config.logging_config` queden configurados.
setup_logging()
