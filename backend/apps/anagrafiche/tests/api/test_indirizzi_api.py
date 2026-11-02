# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per IndirizziRepository (lista, dettaglio,
#        creazione, modifica indirizzi dettaglio, comuni, CAP).
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_indirizzi_dettaglio — lista con risultati e total_count
 2) test_list_indirizzi_dettaglio_empty — nessun risultato
 3) test_list_indirizzi_with_search — filtro ILIKE attivo
 4) test_get_indirizzo_dettaglio — dettaglio singolo
 5) test_get_indirizzo_dettaglio_not_found — id non esistente
 6) (ritirato il 2026-10-18 con `create_indirizzo_dettaglio`: la via la risolve la madre `fn_create_indirizzo`)
 7) test_update_indirizzo_dettaglio — UPDATE dinamico
 8) test_update_indirizzo_no_fields — nessun campo → nessun update
 9) test_list_comuni — lista con provincia e regione
10) test_list_comuni_empty — nessun risultato
11) test_list_codici_postali — CAP per comune
12) (ritirato il 2026-10-18 con `get_or_create_stradario`, copia non atomica di `fn_create_indirizzo`)
13) test_codici_postali_leggono_la_vista_col_filtro_comune — vista di lista + filtro
14) test_regioni_leggono_la_vista_col_filtro_stato — vista di lista + filtro
15) test_stati_ordinano_per_iso3 — la freccia ISO3 entra in whitelist
16) test_pagina_oltre_l_ultima_conta_di_nuovo — ripiego di `fetch_paged_with_total`
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.tests.ricerca_catalogo_fakes import catalogo_ricerca_finto


def _mock_cursor(rows=None, cols=None, rowcount=0, fetchone_value=None):
    """Helper: crea mock cursor configurabile."""
    mock_cur = MagicMock()
    if cols:
        mock_cur.description = [MagicMock(name=c) for c in cols]
        for i, c in enumerate(cols):
            mock_cur.description[i].name = c
    mock_cur.fetchall.return_value = rows or []
    mock_cur.fetchone.return_value = fetchone_value
    mock_cur.rowcount = rowcount
    return mock_cur


def _setup_conn(mock_conn, mock_cur):
    """Helper: configura mock connection."""
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)


class TestListIndirizziDettaglio(TestCase):
    """Test IndirizziRepository.list_indirizzi_dettaglio().

    ⚠️ Dal 2026-09-28 la pagina passa da `fetch_paged_with_total`: si
    sostituisce la `connection` del BB, non quella del repository.
    """

    @patch("apps.core.db._helpers.connection")
    def test_list_indirizzi_dettaglio(self, mock_conn):
        """Lista con risultati e total_count dalla window function."""
        cols = [
            "indirizzo_dettaglio_id", "stradario_id", "indirizzo_normalizzato",
            "civico", "estensione_civico", "descrizione_comune", "cap",
            "provincia", "attivo", "data_insert", "total_count",
        ]
        rows = [
            (1, 10, "Via Roma 1", 1, None, "Milano", "20121", "MI", True, "2026-01-01", 2),
            (2, 10, "Via Roma 3/A", 3, "A", "Milano", "20121", "MI", True, "2026-01-02", 2),
        ]
        mc = _mock_cursor(rows=rows, cols=cols)
        _setup_conn(mock_conn, mc)

        from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository

        repo = IndirizziRepository()
        results, total = repo.list_indirizzi_dettaglio(limit=25, offset=0)

        self.assertEqual(total, 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["indirizzo_normalizzato"], "Via Roma 1")
        self.assertNotIn("total_count", results[0])

    @patch("apps.core.db._helpers.connection")
    def test_list_indirizzi_dettaglio_empty(self, mock_conn):
        """Nessun risultato."""
        mc = _mock_cursor()
        _setup_conn(mock_conn, mc)

        from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository

        results, total = IndirizziRepository().list_indirizzi_dettaglio()
        self.assertEqual(results, [])
        self.assertEqual(total, 0)

    @patch("apps.core.db._helpers.connection")
    def test_list_indirizzi_with_search(self, mock_conn):
        """Verifica che il parametro search sia passato come ILIKE pattern."""
        cols = [
            "indirizzo_dettaglio_id", "stradario_id", "indirizzo_normalizzato",
            "civico", "estensione_civico", "descrizione_comune", "cap",
            "provincia", "attivo", "data_insert", "total_count",
        ]
        rows = [(1, 10, "Via Roma 1", 1, None, "Milano", "20121", "MI", True, "2026-01-01", 1)]
        mc = _mock_cursor(rows=rows, cols=cols)
        _setup_conn(mock_conn, mc)

        from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository

        # La lettura del catalogo e' del BB (`add_ricerca_full_condition`): qui
        # si fissa cosa accende, e si guarda che il pattern arrivi alla SQL.
        with catalogo_ricerca_finto(["indirizzo_normalizzato", "descrizione_comune"]):
            IndirizziRepository().list_indirizzi_dettaglio(search="Roma")
        sql, params = mc.execute.call_args[0]
        self.assertIn("(vid.indirizzo_normalizzato)::text ILIKE %s", sql)
        self.assertIn("(vid.descrizione_comune)::text ILIKE %s", sql)
        self.assertEqual(params.count("%Roma%"), 2)


class TestGetIndirizzoDettaglio(TestCase):
    """Test IndirizziRepository.get_indirizzo_dettaglio()."""

    @patch("apps.anagrafiche.db.indirizzi_repository.connection")
    def test_get_indirizzo_dettaglio(self, mock_conn):
        """Dettaglio singolo trovato."""
        cols = [
            "indirizzo_dettaglio_id", "stradario_id", "indirizzo_normalizzato",
            "civico", "estensione_civico", "descrizione_comune", "cap",
            "provincia", "attivo", "palazzina", "scala", "piano", "interno",
        ]
        row = (1, 10, "Via Roma 1", 1, None, "Milano", "20121", "MI", True, None, "B", "2", "3")
        mc = _mock_cursor(cols=cols, fetchone_value=row)
        _setup_conn(mock_conn, mc)

        from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository

        result = IndirizziRepository().get_indirizzo_dettaglio(1)
        self.assertIsNotNone(result)
        self.assertEqual(result["scala"], "B")
        self.assertEqual(result["piano"], "2")

    @patch("apps.anagrafiche.db.indirizzi_repository.connection")
    def test_get_indirizzo_dettaglio_not_found(self, mock_conn):
        """ID non esistente — None."""
        mc = _mock_cursor(fetchone_value=None)
        _setup_conn(mock_conn, mc)

        from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository

        result = IndirizziRepository().get_indirizzo_dettaglio(999)
        self.assertIsNone(result)


class TestUpdateIndirizzoDettaglio(TestCase):
    """Test IndirizziRepository.update_indirizzo_dettaglio()."""

    @patch("apps.core.db.sql_write_helpers.connection")
    def test_update_indirizzo_dettaglio(self, mock_conn):
        """UPDATE dinamico con campi forniti."""
        mc = _mock_cursor(rowcount=1)
        _setup_conn(mock_conn, mc)

        from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository

        updated = IndirizziRepository().update_indirizzo_dettaglio(
            1, {"civico": 20, "scala": "C", "palazzina": None},
        )
        self.assertTrue(updated)
        sql = mc.execute.call_args[0][0]
        self.assertIn("civico = %s", sql)
        self.assertIn("scala = %s", sql)
        # ⛔ Un `None` SVUOTA il campo (2026-10-20): fino a quel giorno valeva
        #    «non toccare», e svuotare la palazzina dal drawer non scriveva.
        self.assertIn("palazzina = %s", sql)

    def test_update_indirizzo_no_fields(self):
        """Nessun campo fornito — nessun UPDATE, ritorna False (il 400 lo da' il service)."""
        from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository

        updated = IndirizziRepository().update_indirizzo_dettaglio(1, {})
        self.assertFalse(updated)


class TestListComuni(TestCase):
    """Test GeoRepository.list_comuni().

    ⚠️ La connessione si finge sul BB (`_helpers`): dal 2026-09-27 la lista
    legge `config.vw_comuni_lista` con `fetch_paged_with_total`.
    """

    @patch("apps.core.db._helpers.connection")
    def test_list_comuni(self, mock_conn):
        """Lista comuni con provincia e regione."""
        cols = ["id", "descrizione", "provincia_sigla", "provincia_descrizione",
                "regione_descrizione", "total_count"]
        rows = [
            (1, "Milano", "MI", "Milano", "Lombardia", 2),
            (2, "Roma", "RM", "Roma", "Lazio", 2),
        ]
        mc = _mock_cursor(rows=rows, cols=cols)
        _setup_conn(mock_conn, mc)

        from apps.anagrafiche.db.geo_repository import GeoRepository

        results, total = GeoRepository().list_comuni(limit=25, offset=0)
        self.assertEqual(total, 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["provincia_sigla"], "MI")
        self.assertNotIn("total_count", results[0])

    @patch("apps.core.db._helpers.connection")
    def test_list_comuni_empty(self, mock_conn):
        """Nessun comune trovato."""
        mc = _mock_cursor()
        _setup_conn(mock_conn, mc)

        from apps.anagrafiche.db.geo_repository import GeoRepository

        with catalogo_ricerca_finto(["descrizione"]):
            results, total = GeoRepository().list_comuni(search="ZZZZZ")
        self.assertEqual(results, [])
        self.assertEqual(total, 0)
        sql, params = mc.execute.call_args[0]
        self.assertIn("FROM config.vw_comuni_lista v", sql)
        self.assertIn("(v.descrizione)::text ILIKE %s", sql)
        self.assertIn("%ZZZZZ%", params)


class TestListeGeoSuVista(TestCase):
    """Le liste geografiche leggono la vista di lista a catalogo (2026-09-27).

    ⭐ Brief liste-datatable-grezze §4.1 riga 9 / §6.3: la relazione letta e'
    la stessa contro cui il trigger del catalogo valida i `campo_sorgente` —
    una vista accanto alla query non proverebbe niente.
    """

    @patch("apps.core.db._helpers.connection")
    def test_codici_postali_leggono_la_vista_col_filtro_comune(self, mock_conn):
        mc = _mock_cursor()
        _setup_conn(mock_conn, mc)
        from apps.anagrafiche.db.geo_repository import GeoRepository

        with catalogo_ricerca_finto(["codice", "comune_descrizione"]):
            GeoRepository().list_codici_postali(search="201", comune_id=7)
        sql, params = mc.execute.call_args[0]
        self.assertIn("FROM config.vw_codici_postali_lista v", sql)
        self.assertNotIn("JOIN", sql)
        self.assertIn("v.comune_id = %s", sql)
        self.assertIn("(v.codice)::text ILIKE %s OR (v.comune_descrizione)::text ILIKE %s", sql)
        self.assertEqual(params[0], 7)

    @patch("apps.core.db._helpers.connection")
    def test_regioni_leggono_la_vista_col_filtro_stato(self, mock_conn):
        mc = _mock_cursor()
        _setup_conn(mock_conn, mc)
        from apps.anagrafiche.db.geo_repository import GeoRepository

        GeoRepository().list_regioni(stato_id=3, order_by="stato_descrizione", order_dir="desc")
        sql, params = mc.execute.call_args[0]
        self.assertIn("FROM config.vw_regioni_lista v", sql)
        self.assertIn("v.stato_id = %s", sql)
        self.assertIn("ORDER BY stato_descrizione DESC", sql)
        self.assertEqual(params, [3, 25, 0])

    @patch("apps.core.db._helpers.connection")
    def test_stati_ordinano_per_iso3(self, mock_conn):
        mc = _mock_cursor()
        _setup_conn(mock_conn, mc)
        from apps.anagrafiche.db.geo_repository import GeoRepository

        GeoRepository().list_stati(order_by="codice_iso3", order_dir="asc")
        sql = mc.execute.call_args[0][0]
        self.assertIn("ORDER BY codice_iso3 ASC", sql)

    @patch("apps.core.db._helpers.connection")
    def test_pagina_oltre_l_ultima_conta_di_nuovo(self, mock_conn):
        mc = _mock_cursor()
        mc.fetchone.return_value = (12,)
        _setup_conn(mock_conn, mc)
        from apps.anagrafiche.db.geo_repository import GeoRepository

        results, total = GeoRepository().list_province_paginated(regione_id=2, offset=50)
        self.assertEqual((results, total), ([], 12))
        conteggio, params = mc.execute.call_args[0]
        self.assertIn("SELECT COUNT(*) FROM config.vw_province_lista v WHERE v.regione_id = %s", conteggio)
        self.assertEqual(params, [2])


class TestCodiciPostali(TestCase):
    """Test IndirizziRepository.list_codici_postali_by_comune()."""

    @patch("apps.anagrafiche.db.indirizzi_repository.connection")
    def test_list_codici_postali(self, mock_conn):
        """CAP per comune."""
        cols = ["id", "codice"]
        rows = [(1, "20121"), (2, "20122")]
        mc = _mock_cursor(rows=rows, cols=cols)
        _setup_conn(mock_conn, mc)

        from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository

        results = IndirizziRepository().list_codici_postali_by_comune(1)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["codice"], "20121")
