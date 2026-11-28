# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per LookupRepository (tipi soggetto dettaglio,
#        picker dei tipi di indirizzo, autocomplete comuni, search stradario).
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_tipi_soggetto_dettaglio — verifica SQL e mappatura risultati
 2) test_list_tipi_soggetto_dettaglio_empty — nessun risultato
 3) test_picker_chiama_la_funzione_del_contesto — una funzione per contesto, parametri in ordine
 4) test_picker_contesto_sconosciuto — fuori whitelist: KeyError, nessuna query
 4b) test_picker_tipo_ruolo_codice_sconosciuto — codice ignoto: elenco vuoto, la funzione non si chiama
   (il binding vero sul DB: apps/anagrafiche/tests/db/test_tipi_indirizzo_proponibili_db.py)
 5) test_search_comuni_with_search — ricerca ILIKE con risultati
 6) test_search_comuni_no_search — nessun filtro, ritorna primi N
 7) test_search_comuni_empty — nessun risultato
 8) test_search_comuni_pagination — verifica limit e offset passati
 9) test_search_stradario_with_results — ricerca vie con risultati
10) test_search_stradario_empty — nessun risultato
11) test_search_stradario_params — verifica parametri passati alla funzione DB
12) test_list_utilities_per_ba_delegates_to_fn — wrapper su anagrafiche.fn_lookup_utilities_per_ba, params corretti
13) test_list_utilities_per_ba_maps_columns — mappatura colonne is_personalizzata_per_ef e parametri override
14) test_list_utilities_per_ba_empty — risultato vuoto se BA senza utility
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch


def _mock_cursor_with_description(rows, col_names):
    """Helper: crea un mock cursor con description e fetchall/fetchone."""
    mock_cursor = MagicMock()
    mock_cursor.description = [MagicMock(name=c) for c in col_names]
    # Workaround: MagicMock(name=...) non imposta .name come attributo leggibile
    for i, c in enumerate(col_names):
        mock_cursor.description[i].name = c
    mock_cursor.fetchall.return_value = rows
    return mock_cursor


def _mock_connection(mock_conn, mock_cursor):
    """Helper: configura mock connection con context manager."""
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)


class TestListTipiSoggettoDettaglio(TestCase):
    """Test LookupRepository.list_tipi_soggetto_dettaglio()."""

    @patch("apps.core.db.lookup_repository.connection")
    def test_list_tipi_soggetto_dettaglio(self, mock_conn):
        """Verifica SQL eseguito e mappatura colonne risultato."""
        cols = ["id", "codice_interno", "descrizione", "natura_soggetto",
                "cf_obbligatorio", "piva_obbligatoria", "dati_societari_policy"]
        rows = [
            (1, "PR", "Privato", "PF", True, False, "NONE"),
            (3, "SC", "Societa' di capitali", "PG", True, True, "REQUIRED"),
        ]
        mock_cursor = _mock_cursor_with_description(rows, cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results = repo.list_tipi_soggetto_dettaglio()

        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("tipi_soggetto_dettaglio", sql)
        self.assertIn("tipi_soggetto", sql)
        self.assertIn("tipi_soggetto ts", sql)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["codice_interno"], "PR")
        self.assertEqual(results[0]["natura_soggetto"], "PF")
        self.assertEqual(results[1]["dati_societari_policy"], "REQUIRED")

    @patch("apps.core.db.lookup_repository.connection")
    def test_list_tipi_soggetto_dettaglio_empty(self, mock_conn):
        """Nessun tipo soggetto attivo — lista vuota."""
        cols = ["id", "codice_interno", "descrizione", "natura_soggetto",
                "cf_obbligatorio", "piva_obbligatoria", "dati_societari_policy"]
        mock_cursor = _mock_cursor_with_description([], cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results = repo.list_tipi_soggetto_dettaglio()
        self.assertEqual(results, [])


class TestTipiIndirizzoProponibili(TestCase):
    """Test LookupRepository.list_tipi_indirizzo_proponibili() (R-2)."""

    _COLS = ["tipo_indirizzo_id", "codice", "codice_interno", "descrizione",
             "obbligatorio", "ammesso", "motivo_codice", "reason", "reason_key",
             "reason_valori", "motivi"]

    @patch("apps.core.db.lookup_repository.connection")
    def test_picker_chiama_la_funzione_del_contesto(self, mock_conn):
        from apps.core.db.lookup_repository import LookupRepository

        casi = {
            "soggetto": ("fn_tipi_indirizzo_proponibili_soggetto", ("019d-uuid",)),
            "natura": ("fn_tipi_indirizzo_proponibili_natura", (3,)),
            "ruolo": ("fn_tipi_indirizzo_proponibili_ruolo", (50, None)),
            "tipo_ruolo": ("fn_tipi_indirizzo_proponibili_tipo_ruolo", (2, None)),
        }
        for contesto, (funzione, args) in casi.items():
            with self.subTest(contesto=contesto):
                mock_cursor = _mock_cursor_with_description([], self._COLS)
                _mock_connection(mock_conn, mock_cursor)
                LookupRepository().list_tipi_indirizzo_proponibili(contesto, *args)
                sql, params = mock_cursor.execute.call_args[0]
                self.assertIn(f"anagrafiche.{funzione}(", sql)
                self.assertIn("WITH ORDINALITY", sql)
                self.assertEqual(params, list(args))

    @patch("apps.core.db.lookup_repository.connection")
    def test_picker_contesto_sconosciuto(self, mock_conn):
        from apps.core.db.lookup_repository import LookupRepository

        with self.assertRaises(KeyError):
            LookupRepository().list_tipi_indirizzo_proponibili("matrice", 1)
        mock_conn.cursor.assert_not_called()

    @patch("apps.core.db.lookup_repository.connection")
    def test_picker_tipo_ruolo_codice_sconosciuto(self, mock_conn):
        from apps.core.db.lookup_repository import LookupRepository

        mock_cursor = _mock_cursor_with_description([], ["id"])
        mock_cursor.fetchone.return_value = None
        _mock_connection(mock_conn, mock_cursor)
        self.assertEqual(LookupRepository().list_tipi_indirizzo_proponibili_tipo_ruolo("XX"), [])
        mock_cursor.execute.assert_called_once()


class TestSearchComuni(TestCase):
    """Test LookupRepository.search_comuni().

    ⚠️ Dal 2026-09-28 la pagina passa da `fetch_paged_with_total`: si
    sostituisce la `connection` del BB, non quella del repository.
    """

    @patch("apps.core.db._helpers.connection")
    def test_search_comuni_with_search(self, mock_conn):
        """Ricerca ILIKE su denominazione comune con risultati."""
        cols = ["id", "descrizione", "provincia_sigla", "total_count"]
        rows = [
            (4517, "ROMA", "RM", 1),
            (4518, "ROMA CAPITALE", "RM", 1),
        ]
        mock_cursor = _mock_cursor_with_description(rows, cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results, count = repo.search_comuni(search="ROM", limit=20)

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("comuni", sql)
        self.assertEqual(params[0], "%ROM%")
        self.assertEqual(count, 1)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], 4517)
        self.assertEqual(results[0]["descrizione"], "ROMA")
        self.assertEqual(results[0]["provincia_sigla"], "RM")

    @patch("apps.core.db._helpers.connection")
    def test_search_comuni_no_search(self, mock_conn):
        """Nessun filtro — ritorna primi N comuni."""
        cols = ["id", "descrizione", "provincia_sigla", "total_count"]
        rows = [
            (1, "ABANO TERME", "PD", 50),
        ]
        mock_cursor = _mock_cursor_with_description(rows, cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results, count = repo.search_comuni(limit=20)

        sql, params = mock_cursor.execute.call_args[0]
        self.assertIsNone(params[0])
        self.assertEqual(count, 50)

    @patch("apps.core.db._helpers.connection")
    def test_search_comuni_empty(self, mock_conn):
        """Nessun risultato — tupla ([], 0)."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results, count = repo.search_comuni(search="ZZZZZ")

        self.assertEqual(results, [])
        self.assertEqual(count, 0)

    @patch("apps.core.db._helpers.connection")
    def test_search_comuni_pagination(self, mock_conn):
        """Verifica che limit e offset vengano passati al SQL."""
        cols = ["id", "descrizione", "provincia_sigla", "total_count"]
        rows = [(100, "NAPOLI", "NA", 200)]
        mock_cursor = _mock_cursor_with_description(rows, cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        repo.search_comuni(search="NAP", limit=10, offset=5)

        _, params = mock_cursor.execute.call_args[0]
        # params: [search_pattern, search_pattern, limit, offset]
        self.assertEqual(params[2], 10)
        self.assertEqual(params[3], 5)


class TestSearchStradario(TestCase):
    """Test LookupRepository.search_stradario()."""

    @patch("apps.core.db.lookup_repository.connection")
    def test_search_stradario_with_results(self, mock_conn):
        """Ricerca vie con risultati — verifica SQL e mappatura colonne."""
        cols = ["stradario_id", "toponimo", "denominazione", "indirizzo_normalizzato",
                "comune_id", "comune_descrizione", "provincia_sigla",
                "codice_postale_id", "cap"]
        rows = [
            (101, "Via", "Roma", "VIA ROMA", 4517, "ROMA", "RM", 50, "00100"),
            (102, "Piazza", "Venezia", "PIAZZA VENEZIA", 4517, "ROMA", "RM", 51, "00187"),
        ]
        mock_cursor = _mock_cursor_with_description(rows, cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results = repo.search_stradario(comune_id=4517, search="rom", limit=30)

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("fn_search_stradario", sql)
        self.assertEqual(params, [4517, "rom", 30])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["stradario_id"], 101)
        self.assertEqual(results[0]["indirizzo_normalizzato"], "VIA ROMA")
        self.assertEqual(results[1]["toponimo"], "Piazza")
        self.assertEqual(results[1]["cap"], "00187")

    @patch("apps.core.db.lookup_repository.connection")
    def test_search_stradario_empty(self, mock_conn):
        """Nessun risultato — lista vuota."""
        cols = ["stradario_id", "toponimo", "denominazione", "indirizzo_normalizzato",
                "comune_id", "comune_descrizione", "provincia_sigla",
                "codice_postale_id", "cap"]
        mock_cursor = _mock_cursor_with_description([], cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results = repo.search_stradario(comune_id=9999, search="ZZZZZ")

        self.assertEqual(results, [])

    @patch("apps.core.db.lookup_repository.connection")
    def test_search_stradario_params(self, mock_conn):
        """Verifica che comune_id, search e limit vengano passati correttamente."""
        cols = ["stradario_id", "toponimo", "denominazione", "indirizzo_normalizzato",
                "comune_id", "comune_descrizione", "provincia_sigla",
                "codice_postale_id", "cap"]
        rows = [(200, "Corso", "Italia", "CORSO ITALIA", 100, "FIRENZE", "FI", 10, "50123")]
        mock_cursor = _mock_cursor_with_description(rows, cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        repo.search_stradario(comune_id=100, search="ital", limit=15)

        _, params = mock_cursor.execute.call_args[0]
        self.assertEqual(params[0], 100)
        self.assertEqual(params[1], "ital")
        self.assertEqual(params[2], 15)


class TestListUtilitiesPerBillingAccount(TestCase):
    """Test LookupRepository.list_utilities_per_billing_account() —
    wrapper su anagrafiche.fn_lookup_utilities_per_ba (refactor
    operatore-emittenti, sez. 3 del WIP)."""

    _COLS = [
        "utility_id", "codice", "descrizione", "is_personalizzata_per_ef",
        "minimo_soglia_min", "minimo_soglia_max",
        "arrotondamento_importi_dec", "metodo_arrotondamento_importi",
    ]

    @patch("apps.core.db.lookup_repository.connection")
    def test_list_utilities_per_ba_delegates_to_fn(self, mock_conn):
        """Verifica che il metodo chiami la funzione SQL corretta con
        billing_account_id e ruolo_codice_soggetto come parametri."""
        mock_cursor = _mock_cursor_with_description([], self._COLS)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        LookupRepository().list_utilities_per_billing_account(
            billing_account_id=200, ruolo_codice_soggetto="CL"
        )

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("anagrafiche.fn_lookup_utilities_per_ba", sql)
        self.assertEqual(params, [200, "CL"])

    @patch("apps.core.db.lookup_repository.connection")
    def test_list_utilities_per_ba_maps_columns(self, mock_conn):
        """Verifica mappatura colonne: is_personalizzata_per_ef e
        parametri override (soglie, arrotondamento)."""
        rows = [
            # Utility con override per EF (parametri custom)
            (1, "EE", "Energia Elettrica", True, 0.5, 1000.0, 2, "HALF_UP"),
            # Utility ammessa ma senza personalizzazione (parametri default)
            (2, "GAS", "Gas Naturale", False, None, None, None, None),
        ]
        mock_cursor = _mock_cursor_with_description(rows, self._COLS)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        results = LookupRepository().list_utilities_per_billing_account(
            billing_account_id=200, ruolo_codice_soggetto="CL"
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["is_personalizzata_per_ef"])
        self.assertEqual(results[0]["minimo_soglia_min"], 0.5)
        self.assertEqual(results[0]["metodo_arrotondamento_importi"], "HALF_UP")
        self.assertFalse(results[1]["is_personalizzata_per_ef"])
        self.assertIsNone(results[1]["minimo_soglia_min"])

    @patch("apps.core.db.lookup_repository.connection")
    def test_list_utilities_per_ba_empty(self, mock_conn):
        """Lista vuota: BA senza utility ammesse → ritorna []."""
        mock_cursor = _mock_cursor_with_description([], self._COLS)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        results = LookupRepository().list_utilities_per_billing_account(
            billing_account_id=999, ruolo_codice_soggetto="FO"
        )
        self.assertEqual(results, [])
