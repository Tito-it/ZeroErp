# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per il registro strumenti AI.
#        Verifica registrazione, filtro permessi (via PermissionResolver),
#        blacklist e recupero per nome.
# ------------------------------------------------------------

# Indice test:
# 1. test_register_and_get_all
# 2. test_get_tool_by_name
# 3. test_get_tool_by_name_not_found
# 4. test_filter_by_area_permission
# 5. test_filter_blocks_bloccato
# 6. test_filter_write_tool_requires_tutto
# 7. test_tool_without_area_available_to_all
# 8. test_blacklist_disables_tool
# 9. test_clear_registry
# 10. test_is_allowed_read_tool_lettura
# 11. test_is_allowed_blocked
# 12. test_is_allowed_write_requires_tutto
# 13. test_is_allowed_blacklist
# 14. test_is_allowed_required_action

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from apps.ai_assistant.services import tool_registry
from apps.ai_assistant.tools.base import AITool
from apps.core.services.permissions_resolver import PermissionResolver


class _DummyTool(AITool):
    """Tool di test che non fa nulla."""

    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        return {"ok": True}


def _mock_livello(livello_map: dict[str, str]):
    """Crea un side_effect per PermissionResolver.get_livello_area
    che restituisce il livello dalla mappa per area."""
    def _side_effect(user, area, *, cache=None):
        return livello_map.get(area, "BLOCCATO")
    return _side_effect


class TestToolRegistry(unittest.TestCase):
    """Test tool_registry."""

    def setUp(self):
        tool_registry.clear_registry()

    def tearDown(self):
        tool_registry.clear_registry()

    # Scopo: Verifica registrazione e recupero di tutti i tool.
    def test_register_and_get_all(self):
        t1 = _DummyTool(name="t1", description="d1", input_schema={}, required_area="pratiche")
        t2 = _DummyTool(name="t2", description="d2", input_schema={}, required_area="anagrafiche")
        tool_registry.register_tools([t1, t2])
        self.assertEqual(len(tool_registry.get_all_tools()), 2)

    # Scopo: Verifica recupero per nome.
    def test_get_tool_by_name(self):
        t = _DummyTool(name="cerca_test", description="d", input_schema={}, required_area=None)
        tool_registry.register_tool(t)
        found = tool_registry.get_tool_by_name("cerca_test")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "cerca_test")

    # Scopo: Verifica None per tool inesistente.
    def test_get_tool_by_name_not_found(self):
        self.assertIsNone(tool_registry.get_tool_by_name("non_esiste"))

    # Scopo: Verifica che il filtro permessi includa solo tool
    #        per aree accessibili all'utente.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area")
    def test_filter_by_area_permission(self, mock_livello, mock_disabled):
        mock_livello.side_effect = _mock_livello({"pratiche": "LETTURA"})

        t1 = _DummyTool(name="t_pratiche", description="d", input_schema={}, required_area="pratiche")
        t2 = _DummyTool(name="t_vendite", description="d", input_schema={}, required_area="vendite")
        tool_registry.register_tools([t1, t2])

        tools = tool_registry.get_tools_for_user(MagicMock())
        names = [t.name for t in tools]
        self.assertIn("t_pratiche", names)
        self.assertNotIn("t_vendite", names)

    # Scopo: Verifica che BLOCCATO escluda il tool.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area")
    def test_filter_blocks_bloccato(self, mock_livello, mock_disabled):
        mock_livello.side_effect = _mock_livello({"pratiche": "BLOCCATO"})

        t = _DummyTool(name="t_bloccato", description="d", input_schema={}, required_area="pratiche")
        tool_registry.register_tool(t)

        tools = tool_registry.get_tools_for_user(MagicMock())
        self.assertEqual(len(tools), 0)

    # Scopo: Verifica che un tool in scrittura richieda TUTTO.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area")
    def test_filter_write_tool_requires_tutto(self, mock_livello, mock_disabled):
        mock_livello.side_effect = _mock_livello({"pratiche": "LETTURA"})

        t = _DummyTool(
            name="t_write", description="d", input_schema={},
            required_area="pratiche", required_level="TUTTO",
        )
        tool_registry.register_tool(t)

        tools = tool_registry.get_tools_for_user(MagicMock())
        self.assertEqual(len(tools), 0)

    # Scopo: Verifica che un tool senza area sia disponibile a tutti.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area")
    def test_tool_without_area_available_to_all(self, mock_livello, mock_disabled):
        mock_livello.side_effect = _mock_livello({})

        t = _DummyTool(name="t_public", description="d", input_schema={}, required_area=None)
        tool_registry.register_tool(t)

        tools = tool_registry.get_tools_for_user(MagicMock())
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "t_public")

    # Scopo: Verifica che la blacklist disabiliti un tool.
    @patch.object(tool_registry, "_get_disabled_tools", return_value={"t_disabled"})
    @patch.object(PermissionResolver, "get_livello_area")
    def test_blacklist_disables_tool(self, mock_livello, mock_disabled):
        mock_livello.side_effect = _mock_livello({"pratiche": "TUTTO"})

        t1 = _DummyTool(name="t_disabled", description="d", input_schema={}, required_area="pratiche")
        t2 = _DummyTool(name="t_enabled", description="d", input_schema={}, required_area="pratiche")
        tool_registry.register_tools([t1, t2])

        tools = tool_registry.get_tools_for_user(MagicMock())
        names = [t.name for t in tools]
        self.assertNotIn("t_disabled", names)
        self.assertIn("t_enabled", names)

    # Scopo: Verifica che clear_registry svuoti il catalogo.
    def test_clear_registry(self):
        t = _DummyTool(name="t_clear", description="d", input_schema={}, required_area=None)
        tool_registry.register_tool(t)
        self.assertEqual(len(tool_registry.get_all_tools()), 1)
        tool_registry.clear_registry()
        self.assertEqual(len(tool_registry.get_all_tools()), 0)

    # --- is_tool_allowed_for_user (predicato condiviso filtro/ri-check) ---

    # Scopo: tool di lettura su area LETTURA → permesso.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area")
    def test_is_allowed_read_tool_lettura(self, mock_livello, mock_disabled):
        mock_livello.side_effect = _mock_livello({"pratiche": "LETTURA"})
        t = _DummyTool(name="t_r", description="d", input_schema={}, required_area="pratiche")
        self.assertTrue(tool_registry.is_tool_allowed_for_user(MagicMock(), t))

    # Scopo: area BLOCCATO → negato.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area")
    def test_is_allowed_blocked(self, mock_livello, mock_disabled):
        mock_livello.side_effect = _mock_livello({"pratiche": "BLOCCATO"})
        t = _DummyTool(name="t_b", description="d", input_schema={}, required_area="pratiche")
        self.assertFalse(tool_registry.is_tool_allowed_for_user(MagicMock(), t))

    # Scopo: tool in scrittura → richiede TUTTO (LETTURA negato, TUTTO permesso).
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area")
    def test_is_allowed_write_requires_tutto(self, mock_livello, mock_disabled):
        t = _DummyTool(
            name="t_w", description="d", input_schema={},
            required_area="pratiche", required_level="TUTTO",
        )
        mock_livello.side_effect = _mock_livello({"pratiche": "LETTURA"})
        self.assertFalse(tool_registry.is_tool_allowed_for_user(MagicMock(), t))
        mock_livello.side_effect = _mock_livello({"pratiche": "TUTTO"})
        self.assertTrue(tool_registry.is_tool_allowed_for_user(MagicMock(), t))

    # Scopo: tool in blacklist → negato anche con permessi pieni.
    @patch.object(PermissionResolver, "get_livello_area")
    def test_is_allowed_blacklist(self, mock_livello):
        mock_livello.side_effect = _mock_livello({"pratiche": "TUTTO"})
        t = _DummyTool(name="t_disabled", description="d", input_schema={}, required_area="pratiche")
        self.assertFalse(
            tool_registry.is_tool_allowed_for_user(
                MagicMock(), t, disabled={"t_disabled"}
            )
        )

    # Scopo: azione di processo fine (granularità come la UI): con area TUTTO ma
    #        azione disabilitata → negato; azione abilitata → permesso.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "check_azione")
    @patch.object(PermissionResolver, "get_livello_area")
    def test_is_allowed_required_action(self, mock_livello, mock_azione, mock_disabled):
        mock_livello.side_effect = _mock_livello({"pratiche": "TUTTO"})
        t = _DummyTool(
            name="t_act", description="d", input_schema={},
            required_area="pratiche", required_level="TUTTO",
            required_action="cambia_stato_pratica",
        )
        mock_azione.return_value = False
        self.assertFalse(tool_registry.is_tool_allowed_for_user(MagicMock(), t))
        mock_azione.return_value = True
        self.assertTrue(tool_registry.is_tool_allowed_for_user(MagicMock(), t))
