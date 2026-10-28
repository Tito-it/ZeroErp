# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Cosa significano i tre livelli dell'area `ai_assistant`, e che vale
#        sempre il piu' stretto fra quello e il livello sul dominio del tool
#        (brief-db-area-funzionale-assistente-ai §5.3, presidio 3 del §5.4).
#
# ⭐ Gli operatori sono FABBRICATI qui, non presi dai dati: un livello per area,
#    scritto nel test. I tool sono quelli VERI del registro (`cerca_pratiche`,
#    `crea_pratica`) con i loro gemelli veri: se un giorno il gemello cambia
#    area o metodo, questo test lo vede.
# Note: `PermissionResolver` mockato — si prova cio' che la catena DECIDE dato
#       un livello, non come il livello si risolve (quello e' del DB).
#
# Indice test:
#   1) LETTURA sull'assistente + TUTTO su pratiche: consulta, NON crea
#   2) TUTTO sull'assistente + LETTURA su pratiche: consulta, NON crea
#   3) TUTTO + TUTTO: crea, e solo previa conferma
#   4) BLOCCATO sull'assistente: nessun tool, anche con TUTTO sul dominio
#   5) l'ingresso chiede `view`: con LETTURA si entra, con BLOCCATO no
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import patch

from apps.ai_assistant.api.views import AIQueryView
from apps.ai_assistant.services import tool_registry
from apps.core.api.permissions import valuta_accesso_endpoint
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova


class TestLivelliAssistente(unittest.TestCase):

    def setUp(self) -> None:
        tool_registry.clear_registry()
        tool_registry.populate_registry()
        self.addCleanup(tool_registry.clear_registry)

        for nome, valore in (
            ("get_ruolo_applicativo", RUOLO_APPLICATIVO_OPERATORE),
            ("is_super_admin", False),
            ("check_azione", False),
        ):
            patcher = patch.object(PermissionResolver, nome, return_value=valore)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(tool_registry, "_get_disabled_tools", return_value=set())
        patcher.start()
        self.addCleanup(patcher.stop)

        self.livelli: dict[str, str] = {}

        def _area(user: Any, area: str, *, cache: Any = None) -> str:
            return self.livelli.get(area, "BLOCCATO")

        # Un gemello con `model_permission` passa dal livello d'oggetto, che
        # senza override ricade su quello d'area: qui e' lo stesso livello.
        def _oggetto(user: Any, app: str, model: str, area: str, *, cache: Any = None) -> str:
            return self.livelli.get(area, "BLOCCATO")

        for nome, effetto in (("get_livello_area", _area), ("get_livello_oggetto", _oggetto)):
            patcher = patch.object(PermissionResolver, nome, side_effect=effetto)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.cerca = tool_registry.get_tool_by_name("cerca_pratiche")
        self.crea = tool_registry.get_tool_by_name("crea_pratica")
        assert self.cerca is not None and self.crea is not None
        # Il test ha senso solo se i due tool sono una lettura e una scrittura.
        self.assertFalse(self.cerca.scrive)
        self.assertTrue(self.crea.scrive)

    def _puo(self, tool: Any) -> bool:
        return tool_registry.is_tool_allowed_for_user(operatore_di_prova(user_id=11), tool)

    # 1) Crea pratiche dalla UI, non tramite l'assistente.
    def test_lettura_sull_assistente_consulta_ma_non_crea(self) -> None:
        self.livelli = {"ai_assistant": "LETTURA", "pratiche": "TUTTO"}
        self.assertTrue(self._puo(self.cerca))
        self.assertFalse(self._puo(self.crea))

    # 2) Non crea da nessuna parte: l'assistente non allarga il dominio.
    def test_lettura_sul_dominio_non_crea_neanche_con_tutto_sull_assistente(self) -> None:
        self.livelli = {"ai_assistant": "TUTTO", "pratiche": "LETTURA"}
        self.assertTrue(self._puo(self.cerca))
        self.assertFalse(self._puo(self.crea))

    # 3) Crea, e la conferma resta: il tool scrive, quindi la chiede.
    def test_tutto_e_tutto_crea_previa_conferma(self) -> None:
        self.livelli = {"ai_assistant": "TUTTO", "pratiche": "TUTTO"}
        self.assertTrue(self._puo(self.cerca))
        self.assertTrue(self._puo(self.crea))
        self.assertTrue(self.crea.requires_confirmation)

    # 4) Nessun tool, qualunque livello sul dominio.
    def test_bloccato_sull_assistente_nessun_tool(self) -> None:
        self.livelli = {"ai_assistant": "BLOCCATO", "pratiche": "TUTTO"}
        self.assertEqual(tool_registry.get_tools_for_user(operatore_di_prova(user_id=11)), [])

    # 5) La domanda e' una lettura: `post_accesso = "view"` su `AIQueryView`.
    #    Senza, la POST chiederebbe `add` e LETTURA non entrerebbe.
    def test_l_ingresso_chiede_view(self) -> None:
        for livello, atteso in (("LETTURA", True), ("TUTTO", True), ("BLOCCATO", False)):
            with self.subTest(livello=livello):
                self.livelli = {"ai_assistant": livello}
                esito = valuta_accesso_endpoint(
                    operatore_di_prova(user_id=11), AIQueryView, method="POST", cache={},
                )
                self.assertIs(esito.consentito, atteso)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
