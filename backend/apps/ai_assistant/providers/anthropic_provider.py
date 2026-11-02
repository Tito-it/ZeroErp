# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Implementazione provider AI per Anthropic (Claude).
#        Usa l'SDK ufficiale anthropic per comunicare con l'API.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.conf import settings

from apps.ai_assistant.providers.base import AIProvider
from apps.ai_assistant.types import ProviderResponse, ToolCall, TokenUsage

if TYPE_CHECKING:
    import anthropic

logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    """Provider AI basato su Anthropic Claude API.

    La chiave API viene letta da settings.AI_API_KEY (env var).
    Il client viene inizializzato lazy al primo utilizzo.
    """

    def __init__(self) -> None:
        self._client: anthropic.Anthropic | None = None

    # Scopo: Inizializza il client Anthropic lazy, solo al primo uso.
    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise ImportError(
                    "Il pacchetto 'anthropic' non e' installato. "
                    "Aggiungerlo a requirements.in e rieseguire pip-compile."
                ) from exc

            api_key = getattr(settings, "AI_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "AI_API_KEY non configurata. Impostare la variabile d'ambiente."
                )
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    # Scopo: Invia messaggi all'API Anthropic e normalizza la risposta
    #        nel formato ProviderResponse condiviso.
    def send_message(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
        model: str,
        max_tokens: int,
    ) -> ProviderResponse:
        client = self._get_client()

        # Prepara i parametri della chiamata
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        # Includi tools solo se il catalogo non e' vuoto
        if tools:
            kwargs["tools"] = tools

        response = client.messages.create(**kwargs)

        # Normalizza content blocks Anthropic in ProviderResponse
        content_text: str | None = None
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                content_text = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        input=block.input,
                    )
                )

        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return ProviderResponse(
            content=content_text,
            tool_calls=tool_calls,
            usage=usage,
            stop_reason=response.stop_reason,
        )

    # Scopo: Genera embedding via provider dedicato.
    #        Anthropic non ha API embedding native; questa implementazione
    #        e' un placeholder da completare in Fase 2.5b con il provider
    #        embedding scelto (Voyage AI, sentence-transformers, ecc.).
    def generate_embedding(self, text: str) -> list[float]:
        raise NotImplementedError(
            "Anthropic non fornisce API embedding native. "
            "Configurare AI_EMBEDDING_PROVIDER per usare un provider embedding dedicato."
        )
