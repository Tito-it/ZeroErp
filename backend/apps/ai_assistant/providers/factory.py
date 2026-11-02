# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory per istanziare il provider AI corretto
#        in base alla configurazione AI_PROVIDER in settings.
# ------------------------------------------------------------

from __future__ import annotations

from django.conf import settings

from apps.ai_assistant.providers.base import AIProvider
from apps.core.services.error_manager import ErrorManager


# Scopo: Restituisce l'istanza del provider AI configurato.
#        Legge AI_PROVIDER da settings e istanzia il provider corrispondente.
#        Raise ServiceError se il provider non e' riconosciuto.
def get_ai_provider() -> AIProvider:
    provider_name = getattr(settings, "AI_PROVIDER", "mock")

    if provider_name == "anthropic":
        from apps.ai_assistant.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()

    if provider_name == "mistral":
        from apps.ai_assistant.providers.mistral_provider import MistralProvider
        return MistralProvider()

    if provider_name == "mock":
        from apps.ai_assistant.providers.mock_provider import MockProvider
        return MockProvider()

    ErrorManager.raise_error(
        code="E_AI_PROVIDER_UNKNOWN",
        message=f"Provider AI non riconosciuto: {provider_name}",
        detail=f"Valori ammessi: anthropic, mistral, mock. Ricevuto: {provider_name}",
    )
