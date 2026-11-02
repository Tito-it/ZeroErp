# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per il prompt builder AI.
#        Verifica struttura prompt, contesto operatore,
#        data corrente e assenza dati DB.
# ------------------------------------------------------------

# Indice test:
# 1. test_prompt_contains_role
# 2. test_prompt_contains_constraints
# 3. test_prompt_contains_current_date
# 4. test_prompt_contains_operator_name
# 5. test_prompt_contains_tool_names
# 6. test_prompt_no_tools
# 7. test_prompt_operator_fallback_username

import unittest
from typing import Any
from unittest.mock import MagicMock

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.ai_assistant.services.prompt_builder import build_system_prompt, reset_static_context_cache
from apps.ai_assistant.tools.base import AITool, EndpointGemello
from apps.core.api.base_views import DomainAPIView


class _GemelloView(DomainAPIView):
    area_funzionale = "pratiche"


class _DummyTool(AITool):
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        return {}


class TestPromptBuilder(unittest.TestCase):
    """Test build_system_prompt."""

    def setUp(self):
        reset_static_context_cache()
        self.user = MagicMock()
        self.user.first_name = "Marco"
        self.user.last_name = "Rossi"
        self.user.username = "mrossi"

    # Scopo: Il prompt deve contenere il ruolo dell'assistente.
    def test_prompt_contains_role(self):
        prompt = build_system_prompt(self.user, [])
        self.assertIn("ZeroERP", prompt)
        self.assertIn("NON sei un assistente generico", prompt)

    # Scopo: Il prompt deve contenere i vincoli operativi.
    def test_prompt_contains_constraints(self):
        prompt = build_system_prompt(self.user, [])
        self.assertIn("SACRI", prompt)
        self.assertIn("senza conferma esplicita", prompt)

    # Scopo: Il prompt deve contenere la data corrente.
    def test_prompt_contains_current_date(self):
        prompt = build_system_prompt(self.user, [])
        self.assertIn(oggi_aziendale().isoformat(), prompt)

    # Scopo: Il prompt deve contenere il nome dell'operatore.
    def test_prompt_contains_operator_name(self):
        prompt = build_system_prompt(self.user, [])
        self.assertIn("Marco Rossi", prompt)

    # Scopo: Il prompt deve elencare i tool disponibili.
    def test_prompt_contains_tool_names(self):
        t1 = _DummyTool(name="cerca_pratiche", description="d", input_schema={}, endpoint=EndpointGemello(_GemelloView, "GET"))
        t2 = _DummyTool(name="cerca_soggetti", description="d", input_schema={}, endpoint=EndpointGemello(_GemelloView, "GET"))
        prompt = build_system_prompt(self.user, [t1, t2])
        self.assertIn("cerca_pratiche", prompt)
        self.assertIn("cerca_soggetti", prompt)
        self.assertIn("2 STRUMENTI", prompt)

    # Scopo: Senza tool il prompt non menziona strumenti.
    def test_prompt_no_tools(self):
        prompt = build_system_prompt(self.user, [])
        self.assertNotIn("STRUMENTI", prompt)

    # Scopo: Se nome/cognome mancano, usa username.
    def test_prompt_operator_fallback_username(self):
        user = MagicMock()
        user.first_name = ""
        user.last_name = ""
        user.username = "operatore1"
        prompt = build_system_prompt(user, [])
        self.assertIn("operatore1", prompt)
