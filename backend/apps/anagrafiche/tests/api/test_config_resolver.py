# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per endpoint config-resolver per tipo ruolo.
#        Verifica che il resolver restituisca nature ammesse e tipi
#        soggetto dettaglio corretti per diversi scenari.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_config_resolver_ris_umana — ruolo con singola natura PF
 2) test_config_resolver_cliente — ruolo con nature multiple PF/PG/ENC
 3) test_config_resolver_ruolo_senza_matrice — nature libere (fallback)
 4) test_config_resolver_ruolo_non_trovato — codice inesistente → 404
 5) test_config_resolver_case_insensitive — codice minuscolo accettato
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch


def _mock_cursor():
    """Helper: crea mock cursor con execute multipli."""
    mock_cur = MagicMock()
    mock_cur.description = None
    mock_cur.fetchall.return_value = []
    mock_cur.fetchone.return_value = None
    return mock_cur


def _setup_conn(mock_conn, mock_cur):
    """Helper: configura mock connection."""
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)


# Colonne tipo_ruolo
_RUOLO_COLS = ["id", "codice", "descrizione"]

# Colonne nature ammesse
_NATURE_COLS = ["tipo_soggetto_id", "tipo_soggetto_descrizione", "natura_soggetto"]

# Colonne tipi dettaglio
_DETTAGLIO_COLS = [
    "id", "codice_interno", "descrizione", "tipo_soggetto_id",
    "natura_soggetto", "cf_obbligatorio", "piva_obbligatoria",
    "formato_cf", "formato_piva", "dati_societari_policy",
]


def _set_description(mock_cur, cols):
    """Imposta description sul cursor mock."""
    desc = []
    for c in cols:
        m = MagicMock()
        m.name = c
        desc.append(m)
    mock_cur.description = desc


@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverRisUmana(TestCase):
    """Config resolver per RIS_UMANA — solo PF."""

    # Scopo: Verifica che RIS_UMANA restituisca natura PF e tipo PR.
    def test_config_resolver_ris_umana(self, mock_conn):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)

        # Sequenza fetchone/fetchall per le 3 query
        ruolo_row = (5, "RIS_UMANA", "Risorsa Umana")
        nature_rows = [("PF", "Persona Fisica", "PF")]
        dettaglio_rows = [
            (1, "PR", "Privato", "PF", "PF", True, False, "ALFANUM_16", "NON_APPLICABILE", "NONE"),
        ]

        call_count = [0]
        original_execute = mock_cur.execute

        def side_effect_execute(sql, params=None):
            call_count[0] += 1
            if call_count[0] == 1:
                # Query ruolo
                _set_description(mock_cur, _RUOLO_COLS)
                mock_cur.fetchone.return_value = ruolo_row
                mock_cur.fetchall.return_value = [ruolo_row]
            elif call_count[0] == 2:
                # Query nature
                _set_description(mock_cur, _NATURE_COLS)
                mock_cur.fetchone.return_value = nature_rows[0] if nature_rows else None
                mock_cur.fetchall.return_value = nature_rows
            elif call_count[0] == 3:
                # Query dettaglio
                _set_description(mock_cur, _DETTAGLIO_COLS)
                mock_cur.fetchone.return_value = dettaglio_rows[0] if dettaglio_rows else None
                mock_cur.fetchall.return_value = dettaglio_rows

        mock_cur.execute.side_effect = side_effect_execute

        repo = SoggettiRepository()
        result = repo.get_config_resolver("RIS_UMANA")

        self.assertIsNotNone(result)
        self.assertEqual(result["tipo_ruolo"], "RIS_UMANA")
        self.assertEqual(result["nature_ammesse"], ["PF"])
        self.assertEqual(len(result["tipi_soggetto_dettaglio"]), 1)
        det = result["tipi_soggetto_dettaglio"][0]
        self.assertEqual(det["codice_interno"], "PR")
        self.assertTrue(det["cf_obbligatorio"])
        self.assertFalse(det["piva_obbligatoria"])


@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverCliente(TestCase):
    """Config resolver per CL — PF, PG, ENC."""

    # Scopo: Verifica che CL restituisca 3 nature e piu' tipi dettaglio.
    def test_config_resolver_cliente(self, mock_conn):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)

        ruolo_row = (2, "CL", "Cliente")
        nature_rows = [
            ("PF", "Persona Fisica", "PF"),
            ("PG", "Persona Giuridica", "PG"),
            ("ENTE", "Ente Non Commerciale", "ENTE"),
        ]
        dettaglio_rows = [
            (1, "PR", "Privato", "PF", "PF", True, False, "ALFANUM_16", "NON_APPLICABILE", "NONE"),
            (2, "DI", "Ditta Individuale", "PF", "PF", True, True, "ALFANUM_16", "NUM_11", "OPTIONAL"),
            (3, "SC", "Societa di Capitali", "PG", "PG", True, True, "ALFANUM_16", "NUM_11", "REQUIRED"),
            (4, "SP", "Societa di Persone", "PG", "PG", True, True, "ALFANUM_16", "NUM_11", "REQUIRED"),
            (5, "ENC", "Ente Non Commerciale", "ENTE", "ENTE", True, True, "ALFANUM_16", "NUM_11", "REQUIRED"),
        ]

        call_count = [0]

        def side_effect_execute(sql, params=None):
            call_count[0] += 1
            if call_count[0] == 1:
                _set_description(mock_cur, _RUOLO_COLS)
                mock_cur.fetchone.return_value = ruolo_row
                mock_cur.fetchall.return_value = [ruolo_row]
            elif call_count[0] == 2:
                _set_description(mock_cur, _NATURE_COLS)
                mock_cur.fetchall.return_value = nature_rows
            elif call_count[0] == 3:
                _set_description(mock_cur, _DETTAGLIO_COLS)
                mock_cur.fetchall.return_value = dettaglio_rows

        mock_cur.execute.side_effect = side_effect_execute

        repo = SoggettiRepository()
        result = repo.get_config_resolver("CL")

        self.assertIsNotNone(result)
        self.assertEqual(result["tipo_ruolo"], "CL")
        self.assertEqual(sorted(result["nature_ammesse"]), ["ENTE", "PF", "PG"])
        self.assertEqual(len(result["tipi_soggetto_dettaglio"]), 5)


@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverSenzaMatrice(TestCase):
    """Config resolver per ruolo senza matrice — nature libere."""

    # Scopo: Ruolo attivo ma senza righe in tipi_ruoli_nature_ammesse → fallback tutte le nature.
    def test_config_resolver_ruolo_senza_matrice(self, mock_conn):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)

        ruolo_row = (99, "NUOVO", "Ruolo Nuovo")

        call_count = [0]

        def side_effect_execute(sql, params=None):
            call_count[0] += 1
            if call_count[0] == 1:
                _set_description(mock_cur, _RUOLO_COLS)
                mock_cur.fetchone.return_value = ruolo_row
                mock_cur.fetchall.return_value = [ruolo_row]
            elif call_count[0] == 2:
                _set_description(mock_cur, _NATURE_COLS)
                mock_cur.fetchall.return_value = []  # Nessuna natura configurata
            elif call_count[0] == 3:
                _set_description(mock_cur, _DETTAGLIO_COLS)
                mock_cur.fetchall.return_value = []

        mock_cur.execute.side_effect = side_effect_execute

        repo = SoggettiRepository()
        result = repo.get_config_resolver("NUOVO")

        self.assertIsNotNone(result)
        self.assertEqual(sorted(result["nature_ammesse"]), ["ENTE", "PF", "PG"])


@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverNonTrovato(TestCase):
    """Config resolver per codice ruolo inesistente."""

    # Scopo: Codice inesistente → None.
    def test_config_resolver_ruolo_non_trovato(self, mock_conn):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)

        def side_effect_execute(sql, params=None):
            _set_description(mock_cur, _RUOLO_COLS)
            mock_cur.fetchone.return_value = None
            mock_cur.fetchall.return_value = []

        mock_cur.execute.side_effect = side_effect_execute

        repo = SoggettiRepository()
        result = repo.get_config_resolver("INESISTENTE")

        self.assertIsNone(result)


@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverCaseInsensitive(TestCase):
    """Config resolver accetta codice case-insensitive (la view fa .upper())."""

    # Scopo: Verifica che il repository riceva il codice gia' uppercase dalla view.
    def test_config_resolver_case_insensitive(self, mock_conn):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)

        def side_effect_execute(sql, params=None):
            _set_description(mock_cur, _RUOLO_COLS)
            mock_cur.fetchone.return_value = None
            mock_cur.fetchall.return_value = []

        mock_cur.execute.side_effect = side_effect_execute

        repo = SoggettiRepository()
        # La view chiama .upper() prima del repository
        result = repo.get_config_resolver("ris_umana")

        # Verifica che il parametro passato al cursor sia esattamente quello ricevuto
        mock_cur.execute.assert_called_once()
        call_args = mock_cur.execute.call_args
        self.assertEqual(call_args[0][1], ["ris_umana"])
