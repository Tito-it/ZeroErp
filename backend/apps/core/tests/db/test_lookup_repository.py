# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per LookupRepository (tipi soggetto dettaglio,
#        matrice indirizzi, autocomplete comuni, search stradario).
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_tipi_soggetto_dettaglio — verifica SQL e mappatura risultati
 2) test_list_tipi_soggetto_dettaglio_empty — nessun risultato
 3) test_list_matrice_indirizzi — verifica SQL con parametro e mappatura
 4) test_list_matrice_indirizzi_empty — nessun risultato
 5) test_search_comuni_with_search — ricerca ILIKE con risultati
 6) test_search_comuni_no_search — nessun filtro, ritorna primi N
 7) test_search_comuni_empty — nessun risultato
 8) test_search_comuni_pagination — verifica limit e offset passati
 9) test_search_stradario_with_results — ricerca vie con risultati
10) test_search_stradario_empty — nessun risultato
11) test_search_stradario_params — verifica parametri passati alla funzione DB
12) test_list_entity_utility_matrix_ef — LEFT JOIN matrice ammesse + override per emittente
13) test_list_entity_utility_matrix_unconfigured — riga ammessa ma senza override (record_id NULL)
14) test_list_entity_utility_matrix_invalid_table — whitelist nega tabella non ammessa
15) test_list_entity_utility_matrix_tipo_ruolo_parametrized — tipo_ruolo_codice e' parametro %s, no SQL injection
16) test_list_utilities_per_ba_delegates_to_fn — wrapper su anagrafiche.fn_lookup_utilities_per_ba, params corretti
17) test_list_utilities_per_ba_maps_columns — mappatura colonne is_personalizzata_per_ef e parametri override
18) test_list_utilities_per_ba_empty — risultato vuoto se BA senza utility
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


class TestListMatriceIndirizzi(TestCase):
    """Test LookupRepository.list_matrice_indirizzi()."""

    @patch("apps.core.db.lookup_repository.connection")
    def test_list_matrice_indirizzi(self, mock_conn):
        """Verifica SQL con parametro tipo_soggetto_dettaglio_id e mappatura."""
        cols = ["tipo_indirizzo_id", "codice", "descrizione",
                "obbligatorio", "fallback_tipo_indirizzo_id", "fallback_codice"]
        rows = [
            (1, "RESID", "Residenza", True, None, None),
            (2, "DOMFISC", "Domicilio Fiscale", True, None, None),
            (5, "FATT", "Fatturazione", False, 2, "DOMFISC"),
        ]
        mock_cursor = _mock_cursor_with_description(rows, cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results = repo.list_matrice_indirizzi(1)

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("tipi_soggetto_dettaglio_tipi_indirizzo", sql)
        self.assertEqual(params, [1])
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0]["obbligatorio"])
        self.assertEqual(results[2]["fallback_codice"], "DOMFISC")

    @patch("apps.core.db.lookup_repository.connection")
    def test_list_matrice_indirizzi_empty(self, mock_conn):
        """Nessun indirizzo configurato per il tipo — lista vuota."""
        cols = ["tipo_indirizzo_id", "codice", "descrizione",
                "obbligatorio", "fallback_tipo_indirizzo_id", "fallback_codice"]
        mock_cursor = _mock_cursor_with_description([], cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results = repo.list_matrice_indirizzi(999)
        self.assertEqual(results, [])


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


class TestListEntityUtilityMatrix(TestCase):
    """Test LookupRepository.list_entity_utility_matrix() — pattern slot/override."""

    @patch("apps.core.db.lookup_repository.connection")
    def test_list_entity_utility_matrix_ef(self, mock_conn):
        """LEFT JOIN: matrice utility ammesse + override per emittente fiscale."""
        cols = [
            "utility_id", "utility_codice", "utility_descrizione",
            "record_id",
            "minimo_soglia_min", "minimo_soglia_max",
            "arrotondamento_importi_dec", "metodo_arrotondamento_importi",
            "record_attivo", "record_data_insert", "record_data_update",
        ]
        rows = [
            # Riga configurata
            (1, "EE", "Energia Elettrica", 100, 0.5, None, 2, "HALF_UP", True, None, None),
            # Riga ammessa ma non configurata (record_id = NULL)
            (2, "GAS", "Gas Naturale", None, None, None, None, None, None, None, None),
        ]
        mock_cursor = _mock_cursor_with_description(rows, cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results = repo.list_entity_utility_matrix(
            entity_soggetto_ruolo_id=50,
            tipo_ruolo_codice="EF",
            overrides_table="anagrafiche.emittenti_fiscali_utilities",
            overrides_fk_column="emittente_soggetto_ruolo_id",
        )

        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("config.utilities_tipi_ruolo", sql)
        self.assertIn("LEFT JOIN anagrafiche.emittenti_fiscali_utilities", sql)
        self.assertIn("o.emittente_soggetto_ruolo_id = %s", sql)
        # Filtro attivo solo su utilities_tipi_ruolo (matrice).
        # NOTA: config.utilities NON ha colonna attivo, quindi non e' filtrabile lato u.
        self.assertIn("utr.attivo = true", sql)
        self.assertEqual(params, [50, "EF"])
        self.assertEqual(len(results), 2)
        # Riga configurata: record_id valorizzato
        self.assertEqual(results[0]["record_id"], 100)
        self.assertEqual(results[0]["metodo_arrotondamento_importi"], "HALF_UP")
        # Riga non configurata: record_id NULL
        self.assertIsNone(results[1]["record_id"])
        self.assertIsNone(results[1]["metodo_arrotondamento_importi"])

    @patch("apps.core.db.lookup_repository.connection")
    def test_list_entity_utility_matrix_unconfigured(self, mock_conn):
        """Tutte le utility ammesse ma nessun override per l'entita'."""
        cols = [
            "utility_id", "utility_codice", "utility_descrizione",
            "record_id",
            "minimo_soglia_min", "minimo_soglia_max",
            "arrotondamento_importi_dec", "metodo_arrotondamento_importi",
            "record_attivo", "record_data_insert", "record_data_update",
        ]
        rows = [
            (1, "EE", "Energia Elettrica", None, None, None, None, None, None, None, None),
            (2, "GAS", "Gas Naturale", None, None, None, None, None, None, None, None),
        ]
        mock_cursor = _mock_cursor_with_description(rows, cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        results = repo.list_entity_utility_matrix(
            entity_soggetto_ruolo_id=99,
            tipo_ruolo_codice="EF",
            overrides_table="anagrafiche.emittenti_fiscali_utilities",
            overrides_fk_column="emittente_soggetto_ruolo_id",
        )
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["record_id"] is None for r in results))

    def test_list_entity_utility_matrix_invalid_table(self):
        """Whitelist: tabella non ammessa solleva ValueError (no SQL injection)."""
        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        with self.assertRaises(ValueError) as ctx:
            repo.list_entity_utility_matrix(
                entity_soggetto_ruolo_id=1,
                tipo_ruolo_codice="EF",
                overrides_table="public.evil_table; DROP TABLE users;--",
                overrides_fk_column="emittente_soggetto_ruolo_id",
            )
        self.assertIn("non ammessa", str(ctx.exception))

    @patch("apps.core.db.lookup_repository.connection")
    def test_list_entity_utility_matrix_tipo_ruolo_parametrized(self, mock_conn):
        """SECURITY: tipo_ruolo_codice DEVE essere parametro %s, non interpolato.

        Verifica che un payload con caratteri SQL non venga interpolato direttamente
        nello SQL string ma venga passato come parametro al cursor (sicuro).
        """
        cols = [
            "utility_id", "utility_codice", "utility_descrizione",
            "record_id",
            "minimo_soglia_min", "minimo_soglia_max",
            "arrotondamento_importi_dec", "metodo_arrotondamento_importi",
            "record_attivo", "record_data_insert", "record_data_update",
        ]
        mock_cursor = _mock_cursor_with_description([], cols)
        _mock_connection(mock_conn, mock_cursor)

        from apps.core.db.lookup_repository import LookupRepository

        repo = LookupRepository()
        attack = "EF'; DROP TABLE config.tipi_ruoli; --"
        repo.list_entity_utility_matrix(
            entity_soggetto_ruolo_id=1,
            tipo_ruolo_codice=attack,
            overrides_table="anagrafiche.emittenti_fiscali_utilities",
            overrides_fk_column="emittente_soggetto_ruolo_id",
        )

        sql, params = mock_cursor.execute.call_args[0]
        # Lo SQL non deve contenere il payload di attacco interpolato
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn(attack, sql)
        # Il payload deve essere stato passato come parametro %s al cursor
        self.assertIn(attack, params)


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
