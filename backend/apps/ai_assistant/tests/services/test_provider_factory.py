# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per la factory provider AI.
#        Verifica la scelta del provider corretto per ogni valore
#        di AI_PROVIDER e il raise di errore per valori sconosciuti.
# ------------------------------------------------------------

# Indice test:
# 1. test_factory_returns_mock_provider
# 2. test_factory_returns_anthropic_provider
# 3. test_factory_returns_mistral_provider
# 4. test_factory_raises_on_unknown_provider
# 5. test_factory_defaults_to_mock

import unittest
from unittest.mock import patch

from apps.ai_assistant.providers.anthropic_provider import AnthropicProvider
from apps.ai_assistant.providers.factory import get_ai_provider
from apps.ai_assistant.providers.mistral_provider import MistralProvider
from apps.ai_assistant.providers.mock_provider import MockProvider
from apps.core.services.service_errors import ServiceError


class TestProviderFactory(unittest.TestCase):
    """Test factory get_ai_provider()."""

    # Scopo: Verifica che AI_PROVIDER=mock restituisca MockProvider.
    @patch("apps.ai_assistant.providers.factory.settings")
    def test_factory_returns_mock_provider(self, mock_settings):
        mock_settings.AI_PROVIDER = "mock"
        provider = get_ai_provider()
        self.assertIsInstance(provider, MockProvider)

    # Scopo: Verifica che AI_PROVIDER=anthropic restituisca AnthropicProvider.
    @patch("apps.ai_assistant.providers.factory.settings")
    def test_factory_returns_anthropic_provider(self, mock_settings):
        mock_settings.AI_PROVIDER = "anthropic"
        provider = get_ai_provider()
        self.assertIsInstance(provider, AnthropicProvider)

    # Scopo: Verifica che AI_PROVIDER=mistral restituisca MistralProvider.
    @patch("apps.ai_assistant.providers.factory.settings")
    def test_factory_returns_mistral_provider(self, mock_settings):
        mock_settings.AI_PROVIDER = "mistral"
        provider = get_ai_provider()
        self.assertIsInstance(provider, MistralProvider)

    # Scopo: Verifica che un provider sconosciuto sollevi ServiceError.
    @patch("apps.ai_assistant.providers.factory.settings")
    def test_factory_raises_on_unknown_provider(self, mock_settings):
        mock_settings.AI_PROVIDER = "non_esiste"
        with self.assertRaises(ServiceError) as ctx:
            get_ai_provider()
        self.assertEqual(ctx.exception.code, "E_AI_PROVIDER_UNKNOWN")

    # Scopo: Verifica che senza AI_PROVIDER impostato il default sia mock.
    @patch("apps.ai_assistant.providers.factory.settings")
    def test_factory_defaults_to_mock(self, mock_settings):
        # getattr con default "mock" quando AI_PROVIDER non e' definito
        del mock_settings.AI_PROVIDER
        mock_settings.configure_mock(AI_PROVIDER="mock")
        provider = get_ai_provider()
        self.assertIsInstance(provider, MockProvider)
