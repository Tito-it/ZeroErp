# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per il servizio principale AI assistant.
#        Verifica il flusso completo con provider mock:
#        input → tool_call → tool_result → risposta finale.
# ------------------------------------------------------------

# Indice test:
# 1. test_query_returns_ai_query_result
# 2. test_query_empty_message_raises
# 3. test_query_too_long_raises
# 4. test_query_with_tool_call
# 5. test_query_conversation_reuse
# 6. test_query_max_iterations

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from apps.ai_assistant.providers.mock_provider import MockProvider
from apps.ai_assistant.services import ai_assistant_service
from apps.ai_assistant.services import tool_registry
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ai_assistant.tools.base import AITool
from apps.ai_assistant.types import ToolCall
from apps.core.services.service_errors import ServiceError


class _DummySearchTool(AITool):
    """Tool di test che restituisce risultati fissi."""

    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        return {
            "count": 1,
            "results": [
                {"id": 42, "codice": "PRA-001", "descrizione": "Test pratica", "stato": "APERTA"}
            ],
        }


class TestAIAssistantService(unittest.TestCase):
    """Test ai_assistant_service.query()."""

    def setUp(self):
        ai_assistant_service.clear_conversations()
        tool_registry.clear_registry()

        self.user = MagicMock()
        self.user.id = 1
        self.user.first_name = "Test"
        self.user.last_name = "User"
        self.user.username = "testuser"

        self.request = MagicMock()
        self.request.user = self.user

    def tearDown(self):
        ai_assistant_service.clear_conversations()
        tool_registry.clear_registry()

    # Scopo: Verifica che una query semplice restituisca AIQueryResult.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="BLOCCATO")
    def test_query_returns_ai_query_result(self, mock_perms, mock_disabled, mock_log, mock_provider):
        mock_provider.return_value = MockProvider(default_response="Ciao, sono l'assistente.")

        result = ai_assistant_service.query(
            user=self.user,
            request=self.request,
            message="ciao",
        )

        self.assertIn("conversation_id", result)
        self.assertIn("response", result)
        self.assertEqual(result["response"], "Ciao, sono l'assistente.")
        self.assertIsInstance(result["tools_used"], list)
        self.assertIsInstance(result["actions"], list)

    # Scopo: Messaggio vuoto deve sollevare ServiceError.
    def test_query_empty_message_raises(self):
        with self.assertRaises(ServiceError) as ctx:
            ai_assistant_service.query(
                user=self.user,
                request=self.request,
                message="",
            )
        self.assertEqual(ctx.exception.code, "E_AI_QUERY_EMPTY")

    # Scopo: Messaggio troppo lungo deve sollevare ServiceError.
    def test_query_too_long_raises(self):
        with self.assertRaises(ServiceError) as ctx:
            ai_assistant_service.query(
                user=self.user,
                request=self.request,
                message="x" * 2001,
            )
        self.assertEqual(ctx.exception.code, "E_AI_QUERY_TOO_LONG")

    # Scopo: Verifica il flusso completo con tool_call:
    #        provider simula tool_call → service esegue tool →
    #        provider risponde con testo finale.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="LETTURA")
    def test_query_with_tool_call(self, mock_perms, mock_disabled, mock_log, mock_provider):
        # Registra tool di test
        tool = _DummySearchTool(
            name="cerca_pratiche", description="d", input_schema={},
            required_area="pratiche",
            route_template={"name": "pratiche-dettaglio", "params": {"id": "{id}"}},
        )
        tool_registry.register_tool(tool)

        # Provider mock che simula tool_call alla prima chiamata
        provider = MockProvider(
            tool_response=ToolCall(
                id="tc_1", name="cerca_pratiche", input={"stato": "APERTA"}
            ),
            default_response="Ho trovato 1 pratica aperta.",
        )
        mock_provider.return_value = provider

        result = ai_assistant_service.query(
            user=self.user,
            request=self.request,
            message="mostrami le pratiche aperte",
        )

        self.assertIn("cerca_pratiche", result["tools_used"])
        self.assertEqual(result["response"], "Ho trovato 1 pratica aperta.")
        # Verifica azioni di navigazione estratte
        self.assertTrue(len(result["actions"]) > 0)
        self.assertEqual(result["actions"][0]["type"], "navigate")

    # Scopo: Verifica che la stessa conversation_id riusi i messaggi.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="BLOCCATO")
    def test_query_conversation_reuse(self, mock_perms, mock_disabled, mock_log, mock_provider):
        provider = MockProvider(default_response="Risposta 1")
        mock_provider.return_value = provider

        r1 = ai_assistant_service.query(
            user=self.user, request=self.request, message="prima domanda",
        )
        conv_id = r1["conversation_id"]

        provider2 = MockProvider(default_response="Risposta 2")
        mock_provider.return_value = provider2

        r2 = ai_assistant_service.query(
            user=self.user, request=self.request, message="seconda domanda",
            conversation_id=conv_id,
        )
        self.assertEqual(r2["conversation_id"], conv_id)

        # Il provider deve aver ricevuto i messaggi precedenti
        # (user + assistant dalla prima query + user dalla seconda)
        self.assertTrue(len(provider2.last_messages) >= 3)

    # Scopo: Verifica che il limite iterazioni produca risposta parziale.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="LETTURA")
    @patch.object(ai_assistant_service, "MAX_TOOL_ITERATIONS", 2)
    def test_query_max_iterations(self, mock_perms, mock_disabled, mock_log, mock_provider):
        tool = _DummySearchTool(
            name="cerca_pratiche", description="d", input_schema={},
            required_area="pratiche",
        )
        tool_registry.register_tool(tool)

        # Provider che restituisce SEMPRE tool_call (non termina mai)
        provider = MockProvider(
            tool_response=ToolCall(id="tc_loop", name="cerca_pratiche", input={}),
        )
        # Override: restituisci sempre tool_call, anche dopo la prima
        original_send = provider.send_message

        def always_tool_call(**kwargs):
            from apps.ai_assistant.types import ProviderResponse, TokenUsage
            return ProviderResponse(
                content=None,
                tool_calls=[ToolCall(id=f"tc_{provider.call_count}", name="cerca_pratiche", input={})],
                usage=TokenUsage(input_tokens=10, output_tokens=5),
                stop_reason="tool_use",
            )

        provider.send_message = always_tool_call
        mock_provider.return_value = provider

        result = ai_assistant_service.query(
            user=self.user, request=self.request, message="loop infinito",
        )
        self.assertTrue(result["has_more"])
        self.assertIn("limite", result["response"].lower())
