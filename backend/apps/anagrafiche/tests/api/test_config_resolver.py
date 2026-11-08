# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
 3) test_config_resolver_ruolo_senza_matrice — nature libere, lette dall'enum
 4) test_config_resolver_ruolo_non_trovato — codice inesistente → 404
 5) test_config_resolver_chiave_esatta — la chiave arriva al DB com'e', senza maiuscolo
 6) test_config_resolver_default_present — DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO> risolve a id
 7) test_config_resolver_default_codice_orfano — codice non tra dettagli → default_id None
 8) test_config_resolver_default_assente — fn_get_parameter_full ritorna None → default_id None
 9) test_config_resolver_min_search_length_dal_catalogo — la soglia e' quella del
    catalogo della lista `anagrafiche.soggetti` (`soglia_ricerca`), non una costante
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

# La soglia del resolver e' letta dal catalogo della lista soggetti
# (`soglia_ricerca`, brief-db-be-fe-ricerca-soglia-per-lista §6 b): qui, come
# la connessione, e' sostituita per tutto il modulo.
_SOGLIA_PATH = "apps.anagrafiche.db.soggetti_repository.soglia_ricerca"
_soglia = patch(_SOGLIA_PATH, return_value=3)


def setUpModule():
    _soglia.start()


def tearDownModule():
    _soglia.stop()


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
_RUOLO_COLS = ["id", "codice_interno", "descrizione"]

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


def _build_side_effect(mock_cur, ruolo_row, nature_rows, dettaglio_rows, dominio_nature=()):
    """Scopo: side_effect cursor che simula le SQL query del repo soggetti
    (ruolo, nature, dettagli e — solo senza matrice — il dominio delle nature,
    `dominio_nature`, dall'enum). Il default tipo passa via
    ParameterRepository, mockato separatamente nei test che lo richiedono.
    """
    call_count = [0]

    def side_effect(sql, params=None):
        call_count[0] += 1
        if call_count[0] == 1:
            _set_description(mock_cur, _RUOLO_COLS)
            mock_cur.fetchone.return_value = ruolo_row
            mock_cur.fetchall.return_value = [ruolo_row] if ruolo_row else []
        elif call_count[0] == 2:
            _set_description(mock_cur, _NATURE_COLS)
            mock_cur.fetchone.return_value = nature_rows[0] if nature_rows else None
            mock_cur.fetchall.return_value = nature_rows
        elif call_count[0] == 3:
            _set_description(mock_cur, _DETTAGLIO_COLS)
            mock_cur.fetchone.return_value = dettaglio_rows[0] if dettaglio_rows else None
            mock_cur.fetchall.return_value = dettaglio_rows
        elif call_count[0] == 4:
            mock_cur.fetchall.return_value = [(n,) for n in dominio_nature]

    return side_effect


# Path per patchare il default lookup via ParameterRepository.
_GET_PARAM_PATH = "apps.anagrafiche.db.soggetti_repository.ParameterRepository.get_parameter_se_dichiarato"


@patch(_GET_PARAM_PATH, return_value=None, autospec=True)
@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverRisUmana(TestCase):
    """Config resolver per RIS_UMANA — solo PF."""

    # Scopo: Verifica che RIS_UMANA restituisca natura PF e tipo PR.
    def test_config_resolver_ris_umana(self, mock_conn, _mock_get_param):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)
        mock_cur.execute.side_effect = _build_side_effect(
            mock_cur,
            (5, "RIS_UMANA", "Risorsa Umana"),
            [("PF", "Persona Fisica", "PF")],
            [(1, "PR", "Privato", "PF", "PF", True, False, "ALFANUM_16", "NON_APPLICABILE", "NONE")],
        )

        result = SoggettiRepository().get_config_resolver("RIS_UMANA")

        self.assertIsNotNone(result)
        self.assertEqual(result["tipo_ruolo"], "RIS_UMANA")
        self.assertEqual(result["nature_ammesse"], ["PF"])
        self.assertEqual(len(result["tipi_soggetto_dettaglio"]), 1)
        det = result["tipi_soggetto_dettaglio"][0]
        self.assertEqual(det["codice_interno"], "PR")
        self.assertTrue(det["cf_obbligatorio"])
        self.assertFalse(det["piva_obbligatoria"])
        # Default non configurato (mock get_parameter ritorna None)
        self.assertIsNone(result["default_tipo_soggetto_dettaglio_id"])
        self.assertEqual(result["min_search_length"], 3)


@patch(_GET_PARAM_PATH, return_value=None, autospec=True)
@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverCliente(TestCase):
    """Config resolver per CL — PF, PG, ENC."""

    # Scopo: Verifica che CL restituisca 3 nature e piu' tipi dettaglio.
    def test_config_resolver_cliente(self, mock_conn, _mock_get_param):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)
        mock_cur.execute.side_effect = _build_side_effect(
            mock_cur,
            (2, "CL", "Cliente"),
            [
                ("PF", "Persona Fisica", "PF"),
                ("PG", "Persona Giuridica", "PG"),
                ("ENTE", "Ente Non Commerciale", "ENTE"),
            ],
            [
                (1, "PR", "Privato", "PF", "PF", True, False, "ALFANUM_16", "NON_APPLICABILE", "NONE"),
                (2, "DI", "Ditta Individuale", "PF", "PF", True, True, "ALFANUM_16", "NUM_11", "OPTIONAL"),
                (3, "SC", "Societa di Capitali", "PG", "PG", True, True, "ALFANUM_16", "NUM_11", "REQUIRED"),
                (4, "SP", "Societa di Persone", "PG", "PG", True, True, "ALFANUM_16", "NUM_11", "REQUIRED"),
                (5, "ENC", "Ente Non Commerciale", "ENTE", "ENTE", True, True, "ALFANUM_16", "NUM_11", "REQUIRED"),
            ],
        )

        result = SoggettiRepository().get_config_resolver("CL")

        self.assertIsNotNone(result)
        self.assertEqual(result["tipo_ruolo"], "CL")
        self.assertEqual(sorted(result["nature_ammesse"]), ["ENTE", "PF", "PG"])
        self.assertEqual(len(result["tipi_soggetto_dettaglio"]), 5)


@patch(_GET_PARAM_PATH, return_value=None, autospec=True)
@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverSenzaMatrice(TestCase):
    """Config resolver per ruolo senza matrice — nature libere."""

    # Scopo: Ruolo attivo ma senza righe in tipi_ruoli_nature_ammesse → tutte
    #        le nature, LETTE dal dominio (l'enum), non da un elenco nel codice:
    #        una natura che il codice non conosce arriva lo stesso.
    def test_config_resolver_ruolo_senza_matrice(self, mock_conn, _mock_get_param):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)
        mock_cur.execute.side_effect = _build_side_effect(
            mock_cur,
            (99, "NUOVO", "Ruolo Nuovo"),
            [],  # nessuna natura
            [],
            dominio_nature=("PF", "PG", "ENTE", "NUOVA"),
        )

        result = SoggettiRepository().get_config_resolver("NUOVO")

        self.assertIsNotNone(result)
        self.assertEqual(result["nature_ammesse"], ["PF", "PG", "ENTE", "NUOVA"])
        self.assertIn("natura_soggetto_enum", mock_cur.execute.call_args_list[3].args[0])


@patch(_GET_PARAM_PATH, return_value=None, autospec=True)
@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverNonTrovato(TestCase):
    """Config resolver per codice ruolo inesistente."""

    # Scopo: Codice inesistente → None. Esce subito senza chiamare get_parameter.
    def test_config_resolver_ruolo_non_trovato(self, mock_conn, mock_get_param):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)

        def side_effect_execute(sql, params=None):
            _set_description(mock_cur, _RUOLO_COLS)
            mock_cur.fetchone.return_value = None
            mock_cur.fetchall.return_value = []

        mock_cur.execute.side_effect = side_effect_execute

        result = SoggettiRepository().get_config_resolver("INESISTENTE")

        self.assertIsNone(result)
        # Sanity: get_parameter NON deve essere stato chiamato (early return).
        mock_get_param.assert_not_called()


@patch(_GET_PARAM_PATH, return_value=None, autospec=True)
@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverChiaveEsatta(TestCase):
    """La chiave del tipo ruolo e' il `codice_interno`: si confronta esatta.

    Fino al 2026-11-04 la view la metteva in maiuscolo (rotta «case
    insensitive»), unica fra le tre rotte con la chiave nell'URL. Decisione di
    Tid (brief-be-codice-maiuscolo §7.2): tutte esatte.
    """

    # Scopo: la view e il repository passano la chiave invariata: `cl` non e' `CL`.
    def test_config_resolver_chiave_esatta(self, mock_conn, _mock_get_param):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)

        def side_effect_execute(sql, params=None):
            _set_description(mock_cur, _RUOLO_COLS)
            mock_cur.fetchone.return_value = None
            mock_cur.fetchall.return_value = []

        mock_cur.execute.side_effect = side_effect_execute

        SoggettiRepository().get_config_resolver("ris_umana")

        # Verifica che il parametro passato al cursor sia esattamente quello ricevuto
        mock_cur.execute.assert_called_once()
        call_args = mock_cur.execute.call_args
        self.assertEqual(call_args[0][1], ["ris_umana"])


_RUOLO_CL = (2, "CL", "Cliente")
_NATURE_PF_PG = [
    ("PF", "Persona Fisica", "PF"),
    ("PG", "Persona Giuridica", "PG"),
]
_DETTAGLI_CL = [
    (1, "PR", "Privato", "PF", "PF", True, False, "ALFANUM_16", "NON_APPLICABILE", "NONE"),
    (3, "SC", "Societa di Capitali", "PG", "PG", True, True, "ALFANUM_16", "NUM_11", "REQUIRED"),
]


@patch(_GET_PARAM_PATH, autospec=True)
@patch("apps.anagrafiche.db.soggetti_repository.connection")
class TestConfigResolverDefault(TestCase):
    """Config resolver — risoluzione default tipo_soggetto_dettaglio."""

    # Scopo: Default 'PR' configurato in config.parameters → id risolto correttamente.
    def test_config_resolver_default_present(self, mock_conn, mock_get_param):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)
        mock_cur.execute.side_effect = _build_side_effect(
            mock_cur, _RUOLO_CL, _NATURE_PF_PG, _DETTAGLI_CL,
        )
        mock_get_param.return_value = "PR"

        result = SoggettiRepository().get_config_resolver("CL")

        self.assertEqual(result["default_tipo_soggetto_dettaglio_id"], 1)
        self.assertEqual(result["min_search_length"], 3)
        # Verifica che il param_code passato sia derivato da ruolo["codice"]
        # (post-validazione DB), non dall'input raw.
        mock_get_param.assert_called_once()
        # Mock `autospec` di un metodo: `args[0]` e' `self`, il codice e' `args[1]`.
        call_args = mock_get_param.call_args
        self.assertEqual(call_args[0][1], "DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL")

    # Scopo: Default configurato ma codice non presente nei dettagli ammessi
    #        (config inconsistente o cambio nature) → default_id None, no errore.
    def test_config_resolver_default_codice_orfano(self, mock_conn, mock_get_param):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)
        mock_cur.execute.side_effect = _build_side_effect(
            mock_cur, _RUOLO_CL, _NATURE_PF_PG, _DETTAGLI_CL,
        )
        mock_get_param.return_value = "ORFANO"

        result = SoggettiRepository().get_config_resolver("CL")

        self.assertIsNone(result["default_tipo_soggetto_dettaglio_id"])

    # Scopo: parametro non dichiarato → None (get_parameter_se_dichiarato) → default_id None.
    # ⚠️ Col mock il caso «non dichiarato» e' solo un None: che il DB non
    #    sollevi lo prova test_dati_fiscali_societari_db (test 16).
    def test_config_resolver_default_assente(self, mock_conn, mock_get_param):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)
        mock_cur.execute.side_effect = _build_side_effect(
            mock_cur, _RUOLO_CL, _NATURE_PF_PG, _DETTAGLI_CL,
        )
        mock_get_param.return_value = None

        result = SoggettiRepository().get_config_resolver("CL")

        self.assertIsNone(result["default_tipo_soggetto_dettaglio_id"])

    # Scopo: min_search_length e' la soglia del catalogo della lista che il
    #        resolver interroga (`anagrafiche.soggetti`), letta a ogni config:
    #        un valore diverso da quello di progetto arriva cosi' com'e'.
    def test_config_resolver_min_search_length_dal_catalogo(self, mock_conn, mock_get_param):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        mock_cur = _mock_cursor()
        _setup_conn(mock_conn, mock_cur)
        mock_cur.execute.side_effect = _build_side_effect(
            mock_cur, _RUOLO_CL, _NATURE_PF_PG, _DETTAGLI_CL,
        )
        mock_get_param.return_value = None

        with patch(_SOGLIA_PATH, return_value=5) as soglia:
            result = SoggettiRepository().get_config_resolver("CL")

        soglia.assert_called_once_with("anagrafiche.soggetti")
        self.assertEqual(result["min_search_length"], 5)
