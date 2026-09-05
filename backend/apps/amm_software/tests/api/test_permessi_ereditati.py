# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'endpoint dei livelli EREDITATI dal profilo — cosa un operatore
#        avrebbe senza nessun override individuale. Alimenta la colonna
#        «ereditato» del pannello permessi.
#
#        PERCHE' ESISTE, oltre al giro di andata e ritorno. Un override che
#        RIPETE il profilo non e' rumore innocuo: congela la riga, perche' da
#        quel momento non segue piu' il reparto quando il reparto cambia. La
#        colonna serve a non scriverlo, e questi test presidiano che il valore
#        mostrato sia quello che i resolver applicherebbero davvero.
#
#        ⛔ Nessuna dipendenza da DB reale (vincolo CI di AGENTS.md): i test
#        sulla forma della query leggono l'SQL GENERATO, che e' l'idioma di
#        questo repo per provare un criterio senza un database di turno.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_permessi_ereditati — GET ritorna aree e azioni col profilo che le fornisce
 2) test_get_permessi_ereditati_senza_profili — nessun profilo -> due liste vuote
 3) test_operatore_inesistente_solleva — l'esistenza si verifica PRIMA della lettura
 4) test_query_usa_la_funzione_dei_resolver — non una lettura per uo_id
 5) test_query_sceglie_per_priorita — lo spareggio e' quello dei resolver
 6) test_nessuna_chiave_oggetti — l'ereditato di un model e' il livello dell'area
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import PermessiEreditatiView
from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.core.services.service_errors import ServiceError


SAMPLE_EREDITATI = {
    "aree": [
        {"area_id": 2, "area_codice": "vendite", "area_descrizione": "Vendite",
         "livello": "LETTURA", "profilo_nome": "Back-office",
         "profilo_tipo": "REPARTO"},
    ],
    "azioni": [
        {"azione_id": 3, "permission_codename": "genera_fatture_lotti",
         "azione_descrizione": "Genera fatture lotti", "area_codice": "vendite",
         "abilitata": True, "profilo_nome": "Back-office",
         "profilo_tipo": "REPARTO"},
    ],
}


def _make_request() -> MagicMock:
    request = MagicMock()
    request.method = "GET"
    request.user = MagicMock(is_authenticated=True, is_superuser=True, id=1)
    request.data = {}
    return request


class TestPermessiEreditatiView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_get_permessi_ereditati(self, mock_repo_cls):
        """GET ritorna aree e azioni, ognuna col profilo che le fornisce.

        ⭐ `profilo_nome` non e' decorazione: e' cio' che distingue «lo da' il
        reparto» da «lo da' un profilo ad hoc», e sono due situazioni con
        rimedi opposti per chi amministra.
        """
        mock_repo = MagicMock()
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 7}
        mock_repo.get_permessi_ereditati.return_value = SAMPLE_EREDITATI
        mock_repo_cls.return_value = mock_repo

        response = PermessiEreditatiView().get(_make_request(), auth_user_id=7)

        data = json.loads(response.content)["data"]
        self.assertEqual(data["aree"][0]["livello"], "LETTURA")
        self.assertEqual(data["aree"][0]["profilo_nome"], "Back-office")
        self.assertTrue(data["azioni"][0]["abilitata"])
        mock_repo.get_permessi_ereditati.assert_called_once_with(7)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_get_permessi_ereditati_senza_profili(self, mock_repo_cls):
        """Nessun profilo applicabile -> due liste VUOTE.

        ⚠️ La lista vuota e' un DATO, non un buco: significa «nessun profilo
        copre questa voce», quindi vale il default (BLOCCATO / azione negata).
        E' il frontend a renderlo come «default», e per farlo deve poter
        distinguere l'assenza dallo zero.
        """
        mock_repo = MagicMock()
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 7}
        mock_repo.get_permessi_ereditati.return_value = {"aree": [], "azioni": []}
        mock_repo_cls.return_value = mock_repo

        response = PermessiEreditatiView().get(_make_request(), auth_user_id=7)

        data = json.loads(response.content)["data"]
        self.assertEqual(data["aree"], [])
        self.assertEqual(data["azioni"], [])

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_operatore_inesistente_solleva(self, mock_repo_cls):
        """⛔ L'esistenza si verifica PRIMA della lettura, e non e' cerimonia.

        Su un id inesistente le due query tornerebbero due liste vuote, che a
        video sono indistinguibili da «questo utente non eredita niente»: la
        risposta sbagliata al posto di un errore.
        """
        mock_repo = MagicMock()
        mock_repo.get_operatore_detail.return_value = None
        mock_repo_cls.return_value = mock_repo

        with self.assertRaises(ServiceError):
            PermessiEreditatiView().get(_make_request(), auth_user_id=999)

        mock_repo.get_permessi_ereditati.assert_not_called()


class TestFormaDellaQueryEreditati(TestCase):
    """La query dice la stessa cosa dei resolver, o la colonna mente.

    Si legge l'SQL generato invece di interrogare un database: sul catalogo di
    oggi — dove NON esiste nessun binding AD_HOC — la lettura giusta e quella
    sbagliata darebbero lo stesso risultato, quindi un test sui dati sarebbe
    verde per la ragione sbagliata.
    """

    def _sql_eseguite(self) -> list[str]:
        with patch(
            "apps.amm_software.db.amm_software_repository.connection"
        ) as mock_conn:
            cursor = mock_conn.cursor.return_value.__enter__.return_value
            cursor.description = []
            cursor.fetchall.return_value = []
            AmmSoftwareRepository().get_permessi_ereditati(7)
            return [c.args[0] for c in cursor.execute.call_args_list]

    def test_query_usa_la_funzione_dei_resolver(self):
        """⛔ La sorgente e' `fn_get_profili_accesso_applicabili`, non l'UO.

        `get_profilo_reparto` legge il solo binding REPARTO per
        `unita_organizzativa_id`. I bindings sono TRE (AD_HOC prio 1, PORTALE e
        REPARTO prio 2): per un utente con un binding AD_HOC quella lettura
        darebbe un valore plausibile e sbagliato, su una schermata di sicurezza.
        """
        for sql in self._sql_eseguite():
            self.assertIn("script.fn_get_profili_accesso_applicabili", sql)
            self.assertNotIn("unita_organizzativa_id", sql)

    def test_query_sceglie_per_priorita(self):
        """Lo spareggio e' quello dei resolver: il profilo a priorita' minore.

        I resolver fanno `ORDER BY h.priorita LIMIT 1` su una voce sola; qui la
        forma d'insieme e' `DISTINCT ON (<voce>) ... ORDER BY <voce>, h.priorita`,
        che e' lo stesso criterio applicato a tutte le voci in una volta.
        ⚠️ E' l'unico pezzo di catena riscritto: se un giorno i due divergono,
        e' da qui che si comincia a guardare.
        """
        sql_aree, sql_azioni = self._sql_eseguite()
        self.assertIn("DISTINCT ON (paa.area_id)", sql_aree)
        self.assertIn("ORDER BY paa.area_id, h.priorita", sql_aree)
        self.assertIn("DISTINCT ON (paz.azione_id)", sql_azioni)
        self.assertIn("ORDER BY paz.azione_id, h.priorita", sql_azioni)

    def test_nessuna_chiave_oggetti(self):
        """ℹ️ `config.profili_accesso_oggetti` non esiste.

        Per un model l'ereditato e' il livello della sua AREA, che il chiamante
        ha gia' dalla chiave `aree`. Restituirlo anche qui sarebbe una seconda
        risposta alla stessa domanda, con due posti in cui sbagliarla.
        """
        with patch(
            "apps.amm_software.db.amm_software_repository.connection"
        ) as mock_conn:
            cursor = mock_conn.cursor.return_value.__enter__.return_value
            cursor.description = []
            cursor.fetchall.return_value = []
            risultato = AmmSoftwareRepository().get_permessi_ereditati(7)

        self.assertEqual(sorted(risultato.keys()), ["aree", "azioni"])
