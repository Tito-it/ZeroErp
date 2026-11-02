# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il tool `cerca_billing_account` restringe agli stessi emittenti del
#        suo gemello della UI, `BillingAccountLookupView`.
#
# 🔴 PERCHE' ESISTE (2026-09-24). Tool e view risolvono lo scope emittente
#    ciascuno per conto suo, e l'avevano risolto in due modi: la view coi
#    soggetto_ruolo_id (`get_emittenti_sr_ids`), il tool con le PK
#    (`get_emittenti_pk_ids`). La query confronta con
#    `script.fn_check_ba_visible_for_emittenti`, che vuole i soggetto-ruolo:
#    dall'AI si confrontavano numeri di due tabelle diverse, e i BA legittimi
#    sparivano senza errore. Nessun test lo vedeva, perche' ciascuno dei due
#    passava un array «di emittenti».
# ⭐ Da quel giorno lo scope lo risolve il SERVICE (`search_lookup(user=...)`),
#    e tool e view passano solo l'utente. Il test non dice «deve chiamare
#    sr_ids»: fa passare TOOL E VIEW dallo stesso resolver mockato (sr e pk con
#    valori diversi) e pretende che al REPOSITORY arrivi lo STESSO scope. Se un
#    giorno uno dei due tornasse a risolverlo da se', il test lo vede.
#
# Indice test:
#   1) tool e view fanno arrivare al repository lo stesso scope emittente
#   2) lo scope e' quello dei soggetto-ruolo, non delle PK
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from django.http import QueryDict

from apps.ai_assistant.tools.billing_account_tools import CercaBillingAccountTool
from apps.anagrafiche.api.views_billing_account import BillingAccountLookupView
from apps.core.services.permissions_resolver import PermissionResolver

_SR_IDS = [501, 502]
_PK_IDS = [7, 8]
_REPO = "apps.anagrafiche.services.billing_account_service.BillingAccountRepository"


class TestBillingAccountToolScope(unittest.TestCase):

    def setUp(self) -> None:
        for nome, valore in (
            ("get_emittenti_sr_ids", _SR_IDS),
            ("get_emittenti_pk_ids", _PK_IDS),
        ):
            patcher = patch.object(PermissionResolver, nome, return_value=valore)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.user = MagicMock(is_authenticated=True, is_superuser=False)

    # Scopo: lo scope che arriva al repository passando da `chiama`.
    def _scope_al_repository(self, chiama) -> list[int] | None:
        with patch(_REPO) as repo_cls:
            repo_cls.return_value.search_lookup.return_value = ([], 0)
            chiama()
        return repo_cls.return_value.search_lookup.call_args.kwargs["emittente_ids"]

    def _scope_del_tool(self) -> list[int] | None:
        request = MagicMock(user=self.user)
        return self._scope_al_repository(
            lambda: CercaBillingAccountTool().execute({"q": "Rossi"}, request)
        )

    def _scope_della_view(self) -> list[int] | None:
        request = MagicMock(user=self.user)
        request.query_params = QueryDict("q=Rossi")
        return self._scope_al_repository(
            lambda: BillingAccountLookupView().get(request)
        )

    # 1) Il punto: le due strade verso lo stesso service non divergono.
    def test_tool_e_view_passano_lo_stesso_scope(self) -> None:
        self.assertEqual(self._scope_del_tool(), self._scope_della_view())

    # 2) E lo scope e' quello che la query sa confrontare.
    def test_lo_scope_e_quello_dei_soggetto_ruolo(self) -> None:
        self.assertEqual(self._scope_del_tool(), _SR_IDS)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
