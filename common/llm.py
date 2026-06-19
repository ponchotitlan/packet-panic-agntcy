# Copyright Packet Panic Contributors
# SPDX-License-Identifier: Apache-2.0

"""Acceso al modelo de lenguaje a través de LiteLLM.

LiteLLM permite cambiar de proveedor (OpenAI, Azure, Groq, NVIDIA NIM,
etc.) usando una única interfaz, configurada con la variable de entorno
`LLM_MODEL`.
"""

from functools import lru_cache

from langchain_litellm import ChatLiteLLM

from config.config import LLM_MODEL


@lru_cache(maxsize=1)
def get_llm() -> ChatLiteLLM:
    """Devuelve una instancia cacheada del cliente de chat LiteLLM.

    Returns:
        ChatLiteLLM: Cliente configurado con el modelo de `LLM_MODEL`.
    """
    return ChatLiteLLM(model=LLM_MODEL, temperature=0.2)
