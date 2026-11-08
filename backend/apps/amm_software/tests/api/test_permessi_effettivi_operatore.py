# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'endpoint dei permessi EFFETTIVI di un operatore su azioni e
#        oggetti, col tetto d'area (brief-db-permessi-tetto-area). Alimenta
#        l'etichetta «limitata dall'area» del pannello permessi.
#
#        PERCHE' ESISTE. Col tetto un override sotto un'area che non lo
#        consente resta scritto e dormiente (D-3): il pannello deve dirlo, o
#        mostra «abilitata» su un'azione che il DB nega. Questi test presidiano
#        che il valore mostrato venga dalla stessa funzione dei resolver.
#
#        ⛔ Nessuna dipendenza da DB reale (vincolo CI di AGENTS.md): la forma
#        della query si prova sull'SQL GENERATO. Che la funzione applichi il
#        tetto lo prova il pgTAP `test-permessi-tetto-area-v1`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_permessi_effettivi — GET ritorna azioni e oggetti con valore e tetto
 2) test_operatore_inesistente_solleva — l'esistenza si verifica PRIMA della lettura
 3) test_query_usa_le_funzioni_della_catena — azioni e oggetti dalle funzioni dei resolver
 4) test_query_non_riscrive_il_tetto — nessuna seconda copia del confronto fra livelli
 5) test_solo_azioni_attive — il catalogo del pannello, non le azioni spente
 6) test_chiavi_della_risposta — azioni e oggetti, niente aree
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import PermessiEffettiviOperatoreView
from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.core.services.service_errors import ServiceError


SAMPLE_EFFETTIVI = {
    "azioni": [
        {"azione_id": 3, "permission_codename": "genera_fatture_lotti",
         "area_id": 2, "abilitata_specifica": True, "livello_area": "BLOCCATO",
         "livello_minimo_area": "TUTTO", "abilitata": False,
         "limitata_da_area": True},
    ],
    "oggetti": [
        {"app_label": "anagrafiche", "model_name": "conto_bancario",
         "area_schema_db": "anagrafiche", "livello_override": "TUTTO",
         "livello_area": "LETTURA", "livello_specifico": "TUTTO",
         "livello": "LETTURA", "limitato_da_area": True},
    ],
}


def _make_request() -> MagicMock:
    request = MagicMock()
    request.method = "GET"
    request.user = MagicMock(is_authenticated=True, is_superuser=True, id=1)
    request.data = {}
    return request


class TestPermessiEffettiviOperatoreView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_get_permessi_effettivi(self, mock_repo_cls):
        """GET ritorna, per azione e oggetto, il valore applicato e il tetto.

        ⭐ `limitata_da_area` e' la ragione dell'endpoint: un override che
        abilita, sotto un'area BLOCCATA, vale «negata» — e va detto perche'.
        """
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 7}
        mock_repo.get_permessi_effettivi.return_value = SAMPLE_EFFETTIVI
        mock_repo_cls.return_value = mock_repo

        response = PermessiEffettiviOperatoreView().get(_make_request(), auth_user_id=7)

        data = json.loads(response.content)["data"]
        self.assertFalse(data["azioni"][0]["abilitata"])
        self.assertTrue(data["azioni"][0]["limitata_da_area"])
        self.assertEqual(data["oggetti"][0]["livello"], "LETTURA")
        self.assertTrue(data["oggetti"][0]["limitato_da_area"])
        mock_repo.get_permessi_effettivi.assert_called_once_with(7)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_operatore_inesistente_solleva(self, mock_repo_cls):
        """⛔ L'esistenza si verifica PRIMA della lettura.

        Su un id inesistente il DB risponderebbe «tutto negato / BLOCCATO»
        (nessuna identita' OPERATORE attiva): plausibile, e sbagliato al posto
        di un errore.
        """
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = None
        mock_repo_cls.return_value = mock_repo

        with self.assertRaises(ServiceError):
            PermessiEffettiviOperatoreView().get(_make_request(), auth_user_id=999)

        mock_repo.get_permessi_effettivi.assert_not_called()


class TestFormaDellaQueryEffettivi(TestCase):
    """Il pannello legge la stessa catena dei resolver.

    `fn_get_permessi_effettivi_azioni` / `..._oggetti` sono la sede unica
    della catena col tetto: le leggono `fn_check_azione_processo`,
    `fn_resolve_livello_oggetto` e le mappe di `/me/`. Qui resta da provare
    che il backend chiami quelle funzioni e non scriva una seconda copia del
    tetto.
    """

    def _esegui(self) -> tuple[list[str], dict]:
        with patch(
            "apps.amm_software.db.amm_software_repository.connection"
        ) as mock_conn:
            cursor = mock_conn.cursor.return_value.__enter__.return_value
            cursor.description = []
            cursor.fetchall.return_value = []
            risultato = AmmSoftwareRepository().get_permessi_effettivi(7)
            return [c.args[0] for c in cursor.execute.call_args_list], risultato

    def test_query_usa_le_funzioni_della_catena(self):
        """⛔ La sorgente sono le funzioni della catena, non le tabelle di override."""
        (sql_azioni, sql_oggetti), _ = self._esegui()
        self.assertIn("script.fn_get_permessi_effettivi_azioni", sql_azioni)
        self.assertIn("script.fn_get_permessi_effettivi_oggetti", sql_oggetti)
        for sql in (sql_azioni, sql_oggetti):
            self.assertNotIn("user_override_", sql)

    def test_query_non_riscrive_il_tetto(self):
        """Il backend non confronta livelli e non applica il tetto.

        `GREATEST` o le due regole pure richiamate qui sarebbero una seconda
        sede del tetto: la copia che il pgTAP non vede. ⚠️ E l'enum e'
        ordinato TUTTO < LETTURA < BLOCCATO, quindi una copia scritta «a
        intuito» sbaglierebbe anche il verso.
        """
        sql_eseguite, _ = self._esegui()
        for sql in sql_eseguite:
            self.assertNotIn("GREATEST", sql)
            self.assertNotIn("fn_area_consente_azione", sql)
            self.assertNotIn("fn_livello_con_tetto_area", sql)

    def test_solo_azioni_attive(self):
        """Le azioni spente non entrano: il catalogo del pannello e' delle attive."""
        (sql_azioni, _), _ = self._esegui()
        self.assertIn("WHERE e.attivo", sql_azioni)

    def test_chiavi_della_risposta(self):
        """ℹ️ Niente chiave `aree`.

        Il livello effettivo di un'area e' l'override o l'ereditato, che il
        pannello ha gia': restituirlo anche qui sarebbe una seconda risposta
        alla stessa domanda.
        """
        _, risultato = self._esegui()
        self.assertEqual(sorted(risultato.keys()), ["azioni", "oggetti"])
