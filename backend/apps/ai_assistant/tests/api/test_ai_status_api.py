# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `GET /ai-assistant/status/` dice se l'assistente e' UTILIZZABILE da
#        chi chiede, oltre che acceso: il frontend mostra la chat solo in
#        quel caso, invece di farla vedere a chi prenderebbe un 403 alla
#        prima domanda (Tid, 2026-09-25).
#        ⭐ `utilizzabile` viene dalla stessa regola dell'ingresso di
#        `/query/` (`valuta_accesso_endpoint` su `AIQueryView`), e il test
#        lo prova passando dal resolver, non da una copia.
# Note: `PermissionResolver` mockato: si prova cio' che la catena DECIDE.
# ------------------------------------------------------------

# Indice test:
# 1. test_lettura_sull_assistente_e_utilizzabile
# 2. test_bloccato_sull_assistente_non_e_utilizzabile
# 3. test_ai_spenta_non_e_utilizzabile_e_non_chiede_permessi

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from apps.ai_assistant.api.views import AIStatusView
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova


# ⚠️ La richiesta NON e' un MagicMock: la view usa la cache permessi della
#    richiesta (`cache_permessi_richiesta`), che ne legge e scrive gli
#    attributi — su un MagicMock ogni attributo esisterebbe gia', e la cache
#    sarebbe un mock invece di un dizionario.
def _richiesta() -> SimpleNamespace:
    user = operatore_di_prova(user_id=5)
    return SimpleNamespace(user=user)


class TestAIStatusAPI(unittest.TestCase):

    def setUp(self) -> None:
        self.resolver = patch("apps.core.api.permissions.PermissionResolver").start()
        self.addCleanup(patch.stopall)
        self.resolver.get_ruolo_applicativo.return_value = RUOLO_APPLICATIVO_OPERATORE
        self.resolver.is_super_admin.return_value = False
        patch(
            "apps.ai_assistant.services.tool_registry.get_all_tools", return_value=[],
        ).start()

    def _stato(self, *, enabled: bool) -> dict:
        with patch("apps.ai_assistant.api.views.settings") as settings:
            settings.AI_ENABLED = enabled
            settings.AI_PROVIDER = "mock"
            risposta = AIStatusView().get(_richiesta())
        return json.loads(risposta.content)["data"]

    def test_lettura_sull_assistente_e_utilizzabile(self) -> None:
        self.resolver.get_livello_area.return_value = "LETTURA"
        dati = self._stato(enabled=True)
        self.assertIs(dati["enabled"], True)
        self.assertIs(dati["utilizzabile"], True)
        self.resolver.get_livello_area.assert_called_once()
        self.assertEqual(self.resolver.get_livello_area.call_args.args[1], "ai_assistant")

    def test_bloccato_sull_assistente_non_e_utilizzabile(self) -> None:
        self.resolver.get_livello_area.return_value = "BLOCCATO"
        dati = self._stato(enabled=True)
        self.assertIs(dati["enabled"], True)
        self.assertIs(dati["utilizzabile"], False)

    def test_ai_spenta_non_e_utilizzabile_e_non_chiede_permessi(self) -> None:
        self.resolver.get_livello_area.return_value = "TUTTO"
        dati = self._stato(enabled=False)
        self.assertIs(dati["utilizzabile"], False)
        self.resolver.get_livello_area.assert_not_called()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
