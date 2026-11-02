# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per i tool Fase 4 (scrittura con conferma).
#        Verifica registrazione, requires_confirmation, preview,
#        e pattern conferma nel service.
# ------------------------------------------------------------

# Indice test:
# 1. test_crea_pratica_registered_with_confirmation
# 2. test_cambia_stato_registered_with_confirmation
# 3. test_aggiungi_nota_registered_with_confirmation
# 4. test_write_tools_hanno_gemello_di_scrittura
# 5. test_preview_returns_summary
# 6. test_confirmation_flow

import unittest
from unittest.mock import MagicMock, patch

from django.core.cache.backends.locmem import LocMemCache

from apps.ai_assistant.services import ai_assistant_service, tool_registry
from apps.ai_assistant.providers.mock_provider import MockProvider
from apps.ai_assistant.types import ToolCall
from apps.core.services.permissions_resolver import PermissionResolver


class TestFase4ToolRegistration(unittest.TestCase):
    """Verifica tool Fase 4 registrati con requires_confirmation."""

    def setUp(self):
        tool_registry.clear_registry()
        tool_registry.populate_registry()

    def tearDown(self):
        tool_registry.clear_registry()

    # Scopo: crea_pratica deve essere registrato con conferma.
    def test_crea_pratica_registered_with_confirmation(self):
        tool = tool_registry.get_tool_by_name("crea_pratica")
        self.assertIsNotNone(tool)
        self.assertTrue(tool.requires_confirmation)

    # Scopo: cambia_stato_pratica deve essere registrato con conferma.
    def test_cambia_stato_registered_with_confirmation(self):
        tool = tool_registry.get_tool_by_name("cambia_stato_pratica")
        self.assertIsNotNone(tool)
        self.assertTrue(tool.requires_confirmation)

    # Scopo: aggiungi_nota_pratica deve essere registrato con conferma.
    def test_aggiungi_nota_registered_with_confirmation(self):
        tool = tool_registry.get_tool_by_name("aggiungi_nota_pratica")
        self.assertIsNotNone(tool)
        self.assertTrue(tool.requires_confirmation)

    # Scopo: I tool in scrittura hanno per gemello un endpoint di SCRITTURA:
    #        e' da li' che il loro permesso chiede `TUTTO` (o l'azione di
    #        processo). Un gemello `GET` farebbe scrivere un operatore in
    #        sola lettura — il difetto che il vecchio `required_level` scritto
    #        a mano non sapeva impedire.
    def test_write_tools_hanno_gemello_di_scrittura(self):
        for name in ["crea_pratica", "cambia_stato_pratica", "aggiungi_nota_pratica"]:
            tool = tool_registry.get_tool_by_name(name)
            self.assertEqual(tool.endpoint.metodo, "POST", name)

    # Scopo: preview deve restituire summary e details.
    def test_preview_returns_summary(self):
        tool = tool_registry.get_tool_by_name("crea_pratica")
        request = MagicMock()
        result = tool.preview(
            {"tipo_prestazione_id": 1, "priorita_id": 2, "descrizione": "Test"},
            request,
        )
        self.assertIn("summary", result)
        self.assertIn("details", result)
        self.assertIn("Test", result["summary"])


class TestConfirmationFlow(unittest.TestCase):
    """Verifica il flusso conferma nel service."""

    def setUp(self):
        # Cache conferme isolata in-process (no Redis: regola CI "test senza servizi").
        patcher = patch.object(ai_assistant_service, "cache", LocMemCache("ai-test-fase4", {}))
        patcher.start()
        self.addCleanup(patcher.stop)

        ai_assistant_service.clear_conversations()
        tool_registry.clear_registry()
        tool_registry.populate_registry()

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

    # Scopo: Verifica che il tool con conferma restituisca requires_confirmation
    #        e che __confirm__ esegua l'operazione.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "check_azione", return_value=True)
    @patch.object(PermissionResolver, "get_livello_area", return_value="TUTTO")
    def test_confirmation_flow(self, mock_livello, mock_azione, mock_disabled, mock_log, mock_provider):
        # Provider simula tool_call per crea_pratica
        provider = MockProvider(
            tool_response=ToolCall(
                id="tc_1", name="crea_pratica",
                input={"tipo_prestazione_id": 1, "priorita_id": 2, "descrizione": "Test AI"},
            ),
            default_response="Vuoi confermare la creazione della pratica?",
        )
        mock_provider.return_value = provider

        # Step 1: query che attiva il tool con conferma
        result = ai_assistant_service.query(
            user=self.user, request=self.request,
            message="crea una pratica di test",
        )

        # Deve avere un'azione di conferma
        confirm_actions = [a for a in result["actions"] if a["type"] == "confirm"]
        self.assertTrue(len(confirm_actions) > 0, "Deve avere azione confirm")
        conv_id = result["conversation_id"]

        # Verifica che la conferma pendente sia stata salvata in cache (per scope).
        owner_user_id, owner_identita_id = ai_assistant_service._extract_scope(
            self.user, self.request
        )
        scope = {
            "conversation_id": conv_id,
            "owner_user_id": owner_user_id,
            "owner_identita_id": owner_identita_id,
        }
        self.assertIsNotNone(ai_assistant_service._get_pending_confirmation(**scope))

        # Step 2: conferma — deve eseguire (mockiamo il service pratiche)
        with patch("apps.pratiche.services.pratiche_service.crea_pratica", return_value=42):
            result2 = ai_assistant_service.query(
                user=self.user, request=self.request,
                message="__confirm__",
                conversation_id=conv_id,
            )

            self.assertIn("42", result2["response"])

        # La conferma pendente deve essere stata rimossa dalla cache.
        self.assertIsNone(ai_assistant_service._get_pending_confirmation(**scope))
