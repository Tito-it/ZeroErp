# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per il MockProvider.
#        Verifica la struttura ProviderResponse, il conteggio
#        chiamate, la simulazione tool_call e l'embedding mock.
# ------------------------------------------------------------

# Indice test:
# 1. test_send_message_returns_provider_response
# 2. test_send_message_records_parameters
# 3. test_send_message_increments_call_count
# 4. test_send_message_with_tool_response
# 5. test_send_message_tool_response_only_first_call
# 6. test_generate_embedding_returns_1024_floats
# 7. test_generate_embedding_is_deterministic
# 8. test_custom_default_response

import unittest

from apps.ai_assistant.providers.base import EMBEDDING_DIMENSIONS
from apps.ai_assistant.providers.mock_provider import MockProvider
from apps.ai_assistant.types import ToolCall


class TestMockProvider(unittest.TestCase):
    """Test MockProvider."""

    def setUp(self):
        self.provider = MockProvider()
        self.base_kwargs = {
            "messages": [{"role": "user", "content": "test"}],
            "tools": [],
            "system": "system prompt",
            "model": "test-model",
            "max_tokens": 1024,
        }

    # Scopo: Verifica che la risposta abbia la struttura ProviderResponse.
    def test_send_message_returns_provider_response(self):
        result = self.provider.send_message(**self.base_kwargs)
        self.assertIn("content", result)
        self.assertIn("tool_calls", result)
        self.assertIn("usage", result)
        self.assertIn("stop_reason", result)
        self.assertEqual(result["stop_reason"], "end_turn")
        self.assertIsInstance(result["content"], str)
        self.assertIsInstance(result["tool_calls"], list)
        self.assertEqual(len(result["tool_calls"]), 0)

    # Scopo: Verifica che i parametri inviati siano registrati.
    def test_send_message_records_parameters(self):
        self.provider.send_message(**self.base_kwargs)
        self.assertEqual(self.provider.last_messages, self.base_kwargs["messages"])
        self.assertEqual(self.provider.last_system, "system prompt")
        self.assertEqual(self.provider.last_tools, [])

    # Scopo: Verifica che call_count si incrementi.
    def test_send_message_increments_call_count(self):
        self.assertEqual(self.provider.call_count, 0)
        self.provider.send_message(**self.base_kwargs)
        self.assertEqual(self.provider.call_count, 1)
        self.provider.send_message(**self.base_kwargs)
        self.assertEqual(self.provider.call_count, 2)

    # Scopo: Verifica che con tool_response configurato, la prima chiamata
    #        restituisca una tool_call.
    def test_send_message_with_tool_response(self):
        tool = ToolCall(id="t1", name="cerca_pratiche", input={"stato": "APERTA"})
        provider = MockProvider(tool_response=tool)
        result = provider.send_message(**self.base_kwargs)
        self.assertEqual(result["stop_reason"], "tool_use")
        self.assertIsNone(result["content"])
        self.assertEqual(len(result["tool_calls"]), 1)
        self.assertEqual(result["tool_calls"][0]["name"], "cerca_pratiche")

    # Scopo: Verifica che la tool_response venga restituita solo alla prima
    #        chiamata, poi la risposta diventa testuale.
    def test_send_message_tool_response_only_first_call(self):
        tool = ToolCall(id="t1", name="test_tool", input={})
        provider = MockProvider(tool_response=tool)
        # Prima chiamata: tool_call
        r1 = provider.send_message(**self.base_kwargs)
        self.assertEqual(r1["stop_reason"], "tool_use")
        # Seconda chiamata: risposta testuale
        r2 = provider.send_message(**self.base_kwargs)
        self.assertEqual(r2["stop_reason"], "end_turn")
        self.assertIsNotNone(r2["content"])

    # Scopo: Verifica che l'embedding mock sia un vettore della dimensione configurata.
    def test_generate_embedding_returns_correct_dimensions(self):
        embedding = self.provider.generate_embedding("testo di test")
        self.assertEqual(len(embedding), EMBEDDING_DIMENSIONS)
        self.assertTrue(all(isinstance(v, float) for v in embedding))

    # Scopo: Verifica che lo stesso testo produca lo stesso embedding.
    def test_generate_embedding_is_deterministic(self):
        e1 = self.provider.generate_embedding("stessa frase")
        e2 = self.provider.generate_embedding("stessa frase")
        self.assertEqual(e1, e2)

    # Scopo: Verifica che il messaggio di default sia personalizzabile.
    def test_custom_default_response(self):
        provider = MockProvider(default_response="risposta custom")
        result = provider.send_message(**self.base_kwargs)
        self.assertEqual(result["content"], "risposta custom")
