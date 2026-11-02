# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per l'endpoint API AIQueryView.
#        Verifica envelope risposta, guard AI_ENABLED,
#        e codici errore.
# ------------------------------------------------------------

# Indice test:
# 1. test_query_disabled_returns_501
# 2. test_query_success_returns_envelope
# 3. test_query_empty_message_returns_400

import json
import unittest
from unittest.mock import MagicMock, patch


from apps.ai_assistant.api.views import AIQueryView


class TestAIQueryAPI(unittest.TestCase):
    """Test AIQueryView."""

    def _make_request(self, payload: dict) -> MagicMock:
        """Crea un mock Request DRF con body JSON."""
        request = MagicMock()
        request.body = json.dumps(payload).encode("utf-8")
        request.content_type = "application/json"
        request.META = {
            "HTTP_CONTENT_TYPE": "application/json",
            "CONTENT_TYPE": "application/json",
        }
        request.user = MagicMock()
        request.user.id = 1
        request.user.first_name = "Test"
        request.user.last_name = "User"
        request.user.username = "testuser"
        request.user.is_authenticated = True
        return request

    # Scopo: Con AI_ENABLED=False, l'endpoint deve restituire errore.
    @patch("apps.ai_assistant.api.views.settings")
    def test_query_disabled_returns_error(self, mock_settings):
        mock_settings.AI_ENABLED = False

        view = AIQueryView()
        request = self._make_request({"message": "test"})

        # Il guard ErrorManager.require solleva ServiceError
        from apps.core.services.service_errors import ServiceError
        with self.assertRaises(ServiceError) as ctx:
            view.post(request)
        self.assertEqual(ctx.exception.code, "E_AI_DISABLED")

    # Scopo: Con AI attiva e provider mock, verifica envelope di successo.
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.tool_registry._get_disabled_tools", return_value=set())
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_livello_area", return_value="BLOCCATO")
    @patch("apps.ai_assistant.api.views.settings")
    def test_query_success_returns_envelope(
        self, mock_settings, mock_perms, mock_disabled, mock_provider, mock_log
    ):
        mock_settings.AI_ENABLED = True
        mock_settings.AI_MODEL = "test-model"
        mock_settings.AI_MAX_TOKENS = 1024
        mock_settings.AI_CONVERSATION_TTL = 900
        mock_settings.AI_PROVIDER = "mock"
        mock_settings.AI_CONTEXT_FILE = ""

        from apps.ai_assistant.providers.mock_provider import MockProvider
        mock_provider.return_value = MockProvider(default_response="Risposta test")

        from apps.ai_assistant.services import ai_assistant_service
        ai_assistant_service.clear_conversations()

        request = self._make_request({"message": "ciao"})

        # handle_post_json gestisce il parsing, qui testiamo il flusso diretto
        from apps.ai_assistant.services.prompt_builder import reset_static_context_cache
        reset_static_context_cache()

        result = ai_assistant_service.query(
            user=request.user,
            request=request,
            message="ciao",
        )

        self.assertIn("conversation_id", result)
        self.assertEqual(result["response"], "Risposta test")
        self.assertIsInstance(result["tools_used"], list)
        self.assertIsInstance(result["actions"], list)
        self.assertIn("has_more", result)
