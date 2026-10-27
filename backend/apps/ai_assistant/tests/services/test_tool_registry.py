# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per il registro strumenti AI.
#        Verifica registrazione, blacklist, recupero per nome e il filtro
#        permessi: il permesso di un tool e' quello del suo ENDPOINT GEMELLO,
#        deciso dalla stessa regola di `ZeroERPPermission`
#        (brief-db-area-funzionale-assistente-ai §5.2).
# Note: `PermissionResolver` MOCKATO: si prova cio' che la catena DECIDE dato
#       un livello, non come il livello viene risolto. I gemelli sono view
#       FABBRICATE nel test, con gli stessi attributi dichiarativi di quelle
#       vere (`area_funzionale`, `post_permission`, `skip_area_check`).
# ------------------------------------------------------------

# Indice test:
# 1. test_register_and_get_all
# 2. test_get_tool_by_name
# 3. test_get_tool_by_name_not_found
# 4. test_filter_by_area_permission
# 5. test_filter_blocks_bloccato
# 6. test_filter_write_tool_requires_tutto
# 7. test_gemello_skip_area_check_disponibile_senza_livelli
# 8. test_blacklist_disables_tool
# 9. test_clear_registry
# 10. test_is_allowed_read_tool_lettura
# 11. test_is_allowed_blocked
# 12. test_is_allowed_write_requires_tutto
# 13. test_is_allowed_blacklist
# 14. test_is_allowed_gemello_con_azione_decide_solo_l_azione
# 15. test_is_allowed_gemello_admin_solo_super_admin
# 16. test_is_allowed_superuser_django_come_la_ui
# 17. test_is_allowed_permission_class_non_valutabile_nega

import unittest
from typing import Any
from unittest.mock import ANY, patch

from rest_framework.permissions import IsAuthenticated

from apps.ai_assistant.services import tool_registry
from apps.ai_assistant.tools.base import AITool, EndpointGemello
from apps.core.api.base_views import AdminAPIView, DomainAPIView
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova


class _DummyTool(AITool):
    """Tool di test che non fa nulla."""

    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        return {"ok": True}


# --- Gemelli fabbricati: la forma delle view vere, senza il loro corpo ---

class _PraticheView(DomainAPIView):
    area_funzionale = "pratiche"


class _VenditeView(DomainAPIView):
    area_funzionale = "vendite"


class _PraticaStatoView(DomainAPIView):
    area_funzionale = "pratiche"
    post_permission = "cambia_stato_pratica"


class _LookupView(DomainAPIView):
    skip_area_check = True


class _AdminView(AdminAPIView):
    pass


# Permission class DRF senza `valuta`: la regola non la sa valutare fuori da
# una richiesta.
class _NonValutabileView(DomainAPIView):
    permission_classes = [IsAuthenticated]
    area_funzionale = "pratiche"


def _tool(name: str, view: type, metodo: str = "GET") -> _DummyTool:
    return _DummyTool(
        name=name, description="d", input_schema={},
        endpoint=EndpointGemello(view, metodo),
    )


def _mock_livello(livello_map: dict[str, str]):
    """Crea un side_effect per PermissionResolver.get_livello_area
    che restituisce il livello dalla mappa per area."""
    def _side_effect(user, area, *, cache=None):
        return livello_map.get(area, "BLOCCATO")
    return _side_effect


# ⚠️ Dal 2026-09-25 un tool passa anche dal livello sull'assistente (§5.3):
#    i test di questa classe provano il filtro del GEMELLO, e danno TUTTO su
#    `ai_assistant` DICHIARANDOLO in ogni mappa. La semantica dei due livelli
#    insieme sta in `test_livelli_assistente.py`.
_AI_TUTTO = {"ai_assistant": "TUTTO"}


class TestToolRegistry(unittest.TestCase):
    """Test tool_registry."""

    def setUp(self):
        tool_registry.clear_registry()
        for nome, valore in (
            ("get_ruolo_applicativo", RUOLO_APPLICATIVO_OPERATORE),
            ("is_super_admin", False),
            ("check_azione", False),
        ):
            patcher = patch.object(PermissionResolver, nome, return_value=valore)
            setattr(self, f"mock_{nome}", patcher.start())
            self.addCleanup(patcher.stop)
        patcher = patch.object(PermissionResolver, "get_livello_area")
        self.mock_livello = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_livello.side_effect = _mock_livello(dict(_AI_TUTTO))

    def tearDown(self):
        tool_registry.clear_registry()

    # Scopo: Verifica registrazione e recupero di tutti i tool.
    def test_register_and_get_all(self):
        tool_registry.register_tools([
            _tool("t1", _PraticheView), _tool("t2", _VenditeView),
        ])
        self.assertEqual(len(tool_registry.get_all_tools()), 2)

    # Scopo: Verifica recupero per nome.
    def test_get_tool_by_name(self):
        tool_registry.register_tool(_tool("cerca_test", _PraticheView))
        found = tool_registry.get_tool_by_name("cerca_test")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "cerca_test")

    # Scopo: Verifica None per tool inesistente.
    def test_get_tool_by_name_not_found(self):
        self.assertIsNone(tool_registry.get_tool_by_name("non_esiste"))

    # Scopo: Il filtro include solo i tool il cui gemello e' accessibile.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_filter_by_area_permission(self, _mock_disabled):
        self.mock_livello.side_effect = _mock_livello({"pratiche": "LETTURA", **_AI_TUTTO})
        tool_registry.register_tools([
            _tool("t_pratiche", _PraticheView), _tool("t_vendite", _VenditeView),
        ])

        names = [t.name for t in tool_registry.get_tools_for_user(operatore_di_prova(user_id=7))]
        self.assertIn("t_pratiche", names)
        self.assertNotIn("t_vendite", names)

    # Scopo: BLOCCATO esclude il tool.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_filter_blocks_bloccato(self, _mock_disabled):
        self.mock_livello.side_effect = _mock_livello({"pratiche": "BLOCCATO", **_AI_TUTTO})
        tool_registry.register_tool(_tool("t_bloccato", _PraticheView))

        self.assertEqual(tool_registry.get_tools_for_user(operatore_di_prova(user_id=7)), [])

    # Scopo: Un gemello POST chiede `add`, che `LETTURA` non concede.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_filter_write_tool_requires_tutto(self, _mock_disabled):
        self.mock_livello.side_effect = _mock_livello({"pratiche": "LETTURA", **_AI_TUTTO})
        tool_registry.register_tool(_tool("t_write", _PraticheView, "POST"))

        self.assertEqual(tool_registry.get_tools_for_user(operatore_di_prova(user_id=7)), [])

    # Scopo: Un gemello `skip_area_check` (lookup cross-dominio) si apre come
    #        lo apre la UI: senza nessun livello d'area.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_gemello_skip_area_check_disponibile_senza_livelli(self, _mock_disabled):
        tool_registry.register_tool(_tool("t_lookup", _LookupView))

        tools = tool_registry.get_tools_for_user(operatore_di_prova(user_id=7))
        self.assertEqual([t.name for t in tools], ["t_lookup"])
        # Nessun livello di DOMINIO: l'unico chiesto e' quello sull'assistente.
        self.assertEqual(
            {c.args[1] for c in self.mock_livello.call_args_list}, {"ai_assistant"},
        )

    # Scopo: La blacklist disabilita un tool.
    @patch.object(tool_registry, "_get_disabled_tools", return_value={"t_disabled"})
    def test_blacklist_disables_tool(self, _mock_disabled):
        self.mock_livello.side_effect = _mock_livello({"pratiche": "TUTTO", **_AI_TUTTO})
        tool_registry.register_tools([
            _tool("t_disabled", _PraticheView), _tool("t_enabled", _PraticheView),
        ])

        names = [t.name for t in tool_registry.get_tools_for_user(operatore_di_prova(user_id=7))]
        self.assertNotIn("t_disabled", names)
        self.assertIn("t_enabled", names)

    # Scopo: clear_registry svuota il catalogo.
    def test_clear_registry(self):
        tool_registry.register_tool(_tool("t_clear", _PraticheView))
        self.assertEqual(len(tool_registry.get_all_tools()), 1)
        tool_registry.clear_registry()
        self.assertEqual(len(tool_registry.get_all_tools()), 0)

    # --- is_tool_allowed_for_user (predicato condiviso filtro/ri-check) ---

    # Scopo: gemello GET su area LETTURA → permesso.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_is_allowed_read_tool_lettura(self, _mock_disabled):
        self.mock_livello.side_effect = _mock_livello({"pratiche": "LETTURA", **_AI_TUTTO})
        t = _tool("t_r", _PraticheView)
        self.assertTrue(tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=7), t))

    # Scopo: area BLOCCATO → negato.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_is_allowed_blocked(self, _mock_disabled):
        self.mock_livello.side_effect = _mock_livello({"pratiche": "BLOCCATO", **_AI_TUTTO})
        t = _tool("t_b", _PraticheView)
        self.assertFalse(tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=7), t))

    # Scopo: gemello POST → richiede TUTTO (LETTURA negato, TUTTO permesso).
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_is_allowed_write_requires_tutto(self, _mock_disabled):
        t = _tool("t_w", _PraticheView, "POST")
        self.mock_livello.side_effect = _mock_livello({"pratiche": "LETTURA", **_AI_TUTTO})
        self.assertFalse(tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=7), t))
        self.mock_livello.side_effect = _mock_livello({"pratiche": "TUTTO", **_AI_TUTTO})
        self.assertTrue(tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=7), t))

    # Scopo: tool in blacklist → negato anche con permessi pieni.
    def test_is_allowed_blacklist(self):
        self.mock_livello.side_effect = _mock_livello({"pratiche": "TUTTO", **_AI_TUTTO})
        t = _tool("t_disabled", _PraticheView)
        self.assertFalse(
            tool_registry.is_tool_allowed_for_user(
                operatore_di_prova(user_id=7), t, disabled={"t_disabled"}
            )
        )

    # Scopo: gemello con `post_permission` → decide SOLO l'azione, come nella
    #        UI: il livello d'area non si guarda. Fino al 2026-09-24 il tool
    #        chiedeva area `TUTTO` IN PIU' dell'azione, e un operatore a cui
    #        l'azione era concessa in `LETTURA` cambiava stato dalla UI ma non
    #        dall'assistente.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_is_allowed_gemello_con_azione_decide_solo_l_azione(self, _mock_disabled):
        self.mock_livello.side_effect = _mock_livello({"pratiche": "LETTURA", **_AI_TUTTO})
        t = _tool("t_act", _PraticaStatoView, "POST")

        self.mock_check_azione.return_value = False
        self.assertFalse(tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=7), t))
        self.mock_check_azione.return_value = True
        self.assertTrue(tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=7), t))
        self.mock_check_azione.assert_called_with(
            ANY, "cambia_stato_pratica", cache=ANY,
        )
        # Il livello su `pratiche` non si guarda: l'unico chiesto e' quello
        # sull'assistente (il tool scrive, quindi `TUTTO`).
        self.assertEqual(
            {c.args[1] for c in self.mock_livello.call_args_list}, {"ai_assistant"},
        )

    # Scopo: gemello `AdminAPIView` → solo SUPER_ADMIN, qualunque livello
    #        d'area abbia l'operatore (e' il caso di `cerca_operatori`).
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_is_allowed_gemello_admin_solo_super_admin(self, _mock_disabled):
        self.mock_livello.side_effect = _mock_livello({"pratiche": "TUTTO", **_AI_TUTTO})
        t = _tool("t_admin", _AdminView)

        self.assertFalse(tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=7), t))
        self.mock_is_super_admin.return_value = True
        self.assertTrue(tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=7), t))

    # Scopo: il superuser Django passa, come passa dalla UI.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_is_allowed_superuser_django_come_la_ui(self, _mock_disabled):
        t = _tool("t_su", _PraticheView, "POST")
        self.assertTrue(
            tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=7, is_superuser=True), t)
        )

    # Scopo: una permission class senza `valuta` non si sa valutare fuori da
    #        una richiesta → fail-closed, anche con area TUTTO.
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_is_allowed_permission_class_non_valutabile_nega(self, _mock_disabled):
        self.mock_livello.side_effect = _mock_livello({"pratiche": "TUTTO", **_AI_TUTTO})
        t = _tool("t_nv", _NonValutabileView)
        self.assertFalse(tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=7), t))
