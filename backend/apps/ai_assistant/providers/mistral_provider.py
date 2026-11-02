# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Stub provider AI per Mistral (EU).
#        Implementazione da completare quando necessario.
#        Mistral e' un'opzione per installazioni che richiedono
#        residenza dati in EU (GDPR).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.ai_assistant.providers.base import AIProvider
from apps.ai_assistant.types import ProviderResponse


class MistralProvider(AIProvider):
    """Provider AI per Mistral — stub da implementare."""

    # Scopo: Placeholder per invio messaggi a Mistral API.
    def send_message(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
        model: str,
        max_tokens: int,
    ) -> ProviderResponse:
        raise NotImplementedError(
            "MistralProvider non ancora implementato. "
            "Usare AI_PROVIDER=anthropic o AI_PROVIDER=mock."
        )

    # Scopo: Placeholder per generazione embedding via Mistral API.
    def generate_embedding(self, text: str) -> list[float]:
        raise NotImplementedError(
            "MistralProvider embedding non ancora implementato."
        )
