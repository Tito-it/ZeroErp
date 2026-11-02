# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il riepilogo permessi PER AREA degli operatori di una pagina della
#        lista, e la colonna «Override» della lista operatori
#        (brief-db-riepilogo-permessi-lista-operatori, 2026-10-06).
#
#        PERCHE' ESISTE. Il riepilogo era una matrice operatori × aree con una
#        subquery per area costruita da un f-string, su TUTTI gli operatori.
#        Ora livello, override e voci limitate vengono da una sede sola a DB
#        (`fn_get_permessi_riepilogo_aree`, che legge `vw_override_operatore_area`
#        e le funzioni del tetto), e il conteggio della lista dalla stessa vista.
#        Due conteggi scritti qui sarebbero due numeri diversi per lo stesso
#        operatore.
#
#        ⛔ Nessuna dipendenza da DB reale (vincolo CI di AGENTS.md): la forma
#        della query si prova sull'SQL GENERATO. Che la funzione conti giusto lo
#        prova il pgTAP `test-permessi-riepilogo-aree-v1`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_riepilogo_per_gli_id_dati — la view passa gli id, senza duplicati
 2) test_id_non_valido_e_un_400 — un pezzo non intero non si ignora
 3) test_senza_id_nessuna_riga — nessun id, nessuna lettura (repository)
 3b) test_senza_id_e_un_400 — il parametro e' obbligatorio (view)
 4) test_tetto_al_numero_di_id — oltre MAX_LIMIT si rifiuta
 5) test_query_legge_la_funzione_del_riepilogo — sorgente e perimetro operatore
 6) test_query_non_ricalcola — niente resolver, override o tetto riscritti qui
 7) test_lista_proietta_override_count_dalla_vista — la colonna della lista
 8) test_override_count_ordinabile — la colonna e' nella whitelist
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import PermessiRiepilogoView
from apps.amm_software.db.amm_software_repository import (
    ALLOWED_ORDER_COLUMNS,
    AmmSoftwareRepository,
)
from apps.core.api.constants import MAX_LIMIT
from apps.core.services.service_errors import ServiceError


SAMPLE_RIGA = {
    "auth_user_id": 7, "area_id": 2, "area_codice": "anagrafiche",
    "area_descrizione": "Anagrafiche", "livello": "TUTTO",
    "override_count": 3, "voci_limitate": 0,
}


def _make_request(ids: str | None) -> MagicMock:
    request = MagicMock()
    request.method = "GET"
    request.user = MagicMock(is_authenticated=True, is_superuser=True, id=1)
    request.query_params = {} if ids is None else {"auth_user_ids": ids}
    return request


class TestPermessiRiepilogoView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_get_riepilogo_per_gli_id_dati(self, mock_repo_cls):
        """Gli id della pagina arrivano al repository interi, una volta sola, nell'ordine dato."""
        mock_repo = MagicMock()
        mock_repo.get_permessi_riepilogo.return_value = [SAMPLE_RIGA]
        mock_repo_cls.return_value = mock_repo

        response = PermessiRiepilogoView().get(_make_request("7, 3,7"))

        data = json.loads(response.content)["data"]
        self.assertEqual(data["results"], [SAMPLE_RIGA])
        mock_repo.get_permessi_riepilogo.assert_called_once_with([7, 3])

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_id_non_valido_e_un_400(self, mock_repo_cls):
        """⛔ Un pezzo che non e' un id non si scarta in silenzio.

        La pagina chiede righe precise: un id ignorato sarebbe un operatore
        senza chip, e nessuno saprebbe perche'.
        """
        mock_repo_cls.return_value = MagicMock()
        # «²» passa `str.isdigit()` ma non `int()`; il numero lungo passa `int()`
        # ma non il cast a `integer` del DB: entrambi sarebbero un 500.
        for grezzo in ("7,abc", "0", "-3", "7;8", "7,\u00b2", "2147483648"):
            with self.subTest(grezzo=grezzo), self.assertRaises(ServiceError):
                PermessiRiepilogoView().get(_make_request(grezzo))
        mock_repo_cls.return_value.get_permessi_riepilogo.assert_not_called()

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_senza_id_e_un_400(self, mock_repo_cls):
        """Parametro assente, vuoto o di sole virgole: un 400, non una lista vuota."""
        mock_repo_cls.return_value = MagicMock()
        for grezzo in (None, "", " , ,"):
            with self.subTest(grezzo=grezzo), self.assertRaises(ServiceError):
                PermessiRiepilogoView().get(_make_request(grezzo))
        mock_repo_cls.return_value.get_permessi_riepilogo.assert_not_called()

    def test_senza_id_nessuna_riga(self):
        """Nessun id ⇒ nessuna lettura (non «tutti gli operatori», come prima)."""
        with patch("apps.amm_software.db.amm_software_repository.connection") as mock_conn:
            self.assertEqual(AmmSoftwareRepository().get_permessi_riepilogo([]), [])
            mock_conn.cursor.assert_not_called()

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_tetto_al_numero_di_id(self, mock_repo_cls):
        """La funzione fa tre letture per operatore: piu' di una pagina si rifiuta."""
        mock_repo_cls.return_value = MagicMock()
        troppi = ",".join(str(i) for i in range(1, MAX_LIMIT + 2))
        with self.assertRaises(ServiceError):
            PermessiRiepilogoView().get(_make_request(troppi))
        mock_repo_cls.return_value.get_permessi_riepilogo.assert_not_called()


class TestFormaDellaQueryRiepilogo(TestCase):
    """Il riepilogo legge la sede unica, e resta perimetrato come la lista."""

    def _sql_riepilogo(self) -> tuple[str, list]:
        with patch("apps.amm_software.db.amm_software_repository.connection") as mock_conn:
            cursor = mock_conn.cursor.return_value.__enter__.return_value
            cursor.description = []
            cursor.fetchall.return_value = []
            AmmSoftwareRepository().get_permessi_riepilogo([7, 3])
            return cursor.execute.call_args.args[0], cursor.execute.call_args.args[1]

    def test_query_legge_la_funzione_del_riepilogo(self):
        """Sorgente: la funzione DB. Perimetro: i soli operatori fra gli id dati.

        ⚠️ Un id che non e' un operatore (un utente tecnico, una credenziale
        solo shop) riceverebbe dalla funzione righe `BLOCCATO`: si scarta prima.
        """
        sql, params = self._sql_riepilogo()
        self.assertIn("script.fn_get_permessi_riepilogo_aree(", sql)
        self.assertIn("script.fn_categoria_accesso(x.id)", sql)
        self.assertEqual(params, [[7, 3]])

    def test_query_non_ricalcola(self):
        """⛔ Nessuna seconda sede: niente resolver, tabelle di override o tetto qui."""
        sql, _ = self._sql_riepilogo()
        for vietato in ("fn_resolve_livello_area", "user_override_",
                        "fn_get_permessi_effettivi", "GREATEST"):
            self.assertNotIn(vietato, sql)


class TestColonnaOverrideDellaLista(TestCase):
    """La colonna «Override» della lista operatori conta dalla stessa vista."""

    def test_lista_proietta_override_count_dalla_vista(self):
        with patch("apps.amm_software.db.amm_software_repository.fetch_paged_with_total") as mock_fetch:
            mock_fetch.return_value = ([], 0)
            AmmSoftwareRepository().list_operatori()
            sql = mock_fetch.call_args.args[0]
        self.assertIn("script.vw_override_operatore_area", sql)
        self.assertIn("AS override_count", sql)
        # ⛔ Mai ricontare le tre tabelle: la vista E' il conteggio.
        self.assertNotIn("config.user_override_", sql)

    def test_override_count_ordinabile(self):
        self.assertEqual(ALLOWED_ORDER_COLUMNS["override_count"], "override_count")
