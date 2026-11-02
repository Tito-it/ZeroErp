# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari PermissionResolver — verifica integrazione
#        con le funzioni SQL script.fn_* e comportamento cache.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_super_admin_true
 2) test_super_admin_false
 3) test_super_admin_no_row_false
 4) test_ruolo_applicativo_da_guc
 5) test_ruolo_applicativo_fallback_query
 5a) test_ruolo_applicativo_no_identita
 6) test_area_tutto
 7) test_area_lettura
 8) test_area_bloccato
 9) test_area_no_row_defaults_bloccato
10) test_area_correct_params
11) test_oggetto_livello
12) test_oggetto_no_row_defaults_bloccato
13) test_oggetto_correct_params
14) test_azione_abilitata
15) test_azione_negata
16) test_azione_no_row_false
17) test_azione_correct_params
18) test_emittenti_null_none
19) test_emittenti_no_row_none
20) test_emittenti_con_righe_lista
21) test_emittenti_correct_params
21a) test_operatore_con_riga_ritorna_pk
21b) test_admin_globale_ritorna_none
21c) test_no_row_ritorna_none
21d) test_emittente_for_user_correct_params
21e) test_emittente_for_user_cache
22) test_override_trovato
23) test_override_non_trovato_fallback
24) test_uo_trovata
25) test_uo_non_trovata
26) test_has_profilo_true
27) test_has_profilo_false
28) test_has_profilo_no_row
29) test_cache_evita_query_duplicate
30) test_cache_chiavi_diverse
31) test_cache_none_non_memorizza
32) test_cached_hit
33) test_cached_miss_stores
34) test_cached_no_dict
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.permissions_resolver import (
    LIVELLO_MAP,
    PermissionResolver,
    _cached,
)

_CONN = "apps.core.services.permissions_resolver.connection"


def _mock_user(user_id: int = 1) -> MagicMock:
    """Scopo: Crea un mock user Django con id impostato."""
    user = MagicMock()
    user.id = user_id
    return user


def _setup_cursor(mock_conn: MagicMock, fetchone_value: tuple | None) -> MagicMock:
    """Scopo: Configura il mock connection.cursor() per restituire fetchone_value."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_value
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_cursor


# ── Super admin ───────────────────────────────────────────


class PermissionResolverIsSuperAdminTests(TestCase):
    """Test per is_super_admin — delegata a script.fn_is_super_admin.

    NB: il contratto cross-veste §8.3.7 (filtro `ruolo_applicativo=OPERATORE`
    che impedisce il bypass SUPER_ADMIN per identita non-operatore) e'
    enforce *lato DB* dentro `script.fn_is_super_admin` e va verificato
    con pgTAP sul branch DB. Qui testiamo solo che il wrapper Python
    propaghi fedelmente il risultato della fn DB senza alterazioni: un
    test Python con mock non puo' dare prova del filtro cross-veste
    (il mock ritorna quello che gli passi, indipendentemente dal
    ruolo_applicativo del user reale)."""

    # Scopo: is_super_admin True quando il binding e' attivo.
    @patch(_CONN)
    def test_super_admin_true(self, mock_conn):
        cursor = _setup_cursor(mock_conn, (True,))
        user = _mock_user()
        result = PermissionResolver.is_super_admin(user)
        self.assertTrue(result)
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_is_super_admin(%s)", [1]
        )

    # Scopo: is_super_admin False quando il binding non e' attivo.
    @patch(_CONN)
    def test_super_admin_false(self, mock_conn):
        _setup_cursor(mock_conn, (False,))
        result = PermissionResolver.is_super_admin(_mock_user())
        self.assertFalse(result)

    # Scopo: Nessuna riga dalla funzione -> False (fail-closed).
    @patch(_CONN)
    def test_super_admin_no_row_false(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.is_super_admin(_mock_user())
        self.assertFalse(result)


# ── Ruolo applicativo ─────────────────────────────────────


class PermissionResolverRuoloApplicativoTests(TestCase):
    """Test per get_ruolo_applicativo — GUC-first con fallback query."""

    # Scopo: GUC popolato ritorna il valore senza query identita.
    @patch(_CONN)
    def test_ruolo_applicativo_da_guc(self, mock_conn):
        cursor = _setup_cursor(mock_conn, ("OPERATORE",))
        result = PermissionResolver.get_ruolo_applicativo(_mock_user())
        self.assertEqual(result, "OPERATORE")
        # Prima esecuzione: SELECT NULLIF(current_setting(...)); ritorna
        # il valore gia' popolato, fallback non eseguito.
        self.assertEqual(cursor.execute.call_count, 1)

    # Scopo: GUC vuoto -> fallback query identita_digitali, sulle sole vesti
    #        utilizzabili (building block DB).
    @patch(_CONN)
    def test_ruolo_applicativo_fallback_query(self, mock_conn):
        cursor = MagicMock()
        # Sequenza: primo fetchone restituisce ('',) GUC vuoto;
        # secondo fetchone la riga identita.
        cursor.fetchone.side_effect = [(None,), ("CLIENTE_PORTALE",)]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        result = PermissionResolver.get_ruolo_applicativo(_mock_user())
        self.assertEqual(result, "CLIENTE_PORTALE")
        self.assertEqual(cursor.execute.call_count, 2)
        # La regola «utilizzabile» la decide il DB, come per la GUC: il
        # fallback non la riscrive con `attivo`.
        sql = cursor.execute.call_args_list[1][0][0]
        self.assertIn("script.fn_veste_utilizzabile(id)", sql)
        self.assertNotIn("attivo = true", sql)
        self.assertIn("ORDER BY id", sql)

    # Scopo: Nessuna identita -> None.
    @patch(_CONN)
    def test_ruolo_applicativo_no_identita(self, mock_conn):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(None,), None]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        result = PermissionResolver.get_ruolo_applicativo(_mock_user())
        self.assertIsNone(result)


# ── Livello area ──────────────────────────────────────────


class PermissionResolverLivelloAreaTests(TestCase):
    """Test per get_livello_area — delegata a script.fn_resolve_livello_area."""

    # Scopo: Livello TUTTO concede tutte le azioni CRUD.
    @patch(_CONN)
    def test_area_tutto(self, mock_conn):
        _setup_cursor(mock_conn, ("TUTTO",))
        livello = PermissionResolver.get_livello_area(_mock_user(), "vendite")
        self.assertEqual(livello, "TUTTO")
        self.assertEqual(
            LIVELLO_MAP[livello], frozenset({"view", "add", "change", "delete"})
        )

    # Scopo: Livello LETTURA concede solo view.
    @patch(_CONN)
    def test_area_lettura(self, mock_conn):
        _setup_cursor(mock_conn, ("LETTURA",))
        livello = PermissionResolver.get_livello_area(_mock_user(), "vendite")
        self.assertEqual(livello, "LETTURA")
        self.assertIn("view", LIVELLO_MAP[livello])
        self.assertNotIn("add", LIVELLO_MAP[livello])

    # Scopo: Livello BLOCCATO nega tutto.
    @patch(_CONN)
    def test_area_bloccato(self, mock_conn):
        _setup_cursor(mock_conn, ("BLOCCATO",))
        livello = PermissionResolver.get_livello_area(_mock_user(), "vendite")
        self.assertEqual(livello, "BLOCCATO")
        self.assertEqual(len(LIVELLO_MAP[livello]), 0)

    # Scopo: Nessuna riga -> default BLOCCATO.
    @patch(_CONN)
    def test_area_no_row_defaults_bloccato(self, mock_conn):
        _setup_cursor(mock_conn, None)
        livello = PermissionResolver.get_livello_area(_mock_user(), "vendite")
        self.assertEqual(livello, "BLOCCATO")

    # Scopo: Verifica parametri SQL corretti.
    @patch(_CONN)
    def test_area_correct_params(self, mock_conn):
        cursor = _setup_cursor(mock_conn, ("TUTTO",))
        PermissionResolver.get_livello_area(_mock_user(42), "contabilita")
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_resolve_livello_area(%s, %s)",
            [42, "contabilita"],
        )


# ── Livello oggetto ──────────────────────────────────────


class PermissionResolverLivelloOggettoTests(TestCase):
    """Test per get_livello_oggetto — delegata a script.fn_resolve_livello_oggetto."""

    # Scopo: Livello oggetto restituito correttamente.
    @patch(_CONN)
    def test_oggetto_livello(self, mock_conn):
        _setup_cursor(mock_conn, ("LETTURA",))
        livello = PermissionResolver.get_livello_oggetto(
            _mock_user(), "anagrafiche", "clienti", "anagrafiche"
        )
        self.assertEqual(livello, "LETTURA")

    # Scopo: Nessuna riga -> default BLOCCATO.
    @patch(_CONN)
    def test_oggetto_no_row_defaults_bloccato(self, mock_conn):
        _setup_cursor(mock_conn, None)
        livello = PermissionResolver.get_livello_oggetto(
            _mock_user(), "anagrafiche", "clienti", "anagrafiche"
        )
        self.assertEqual(livello, "BLOCCATO")

    # Scopo: Verifica parametri SQL corretti.
    @patch(_CONN)
    def test_oggetto_correct_params(self, mock_conn):
        cursor = _setup_cursor(mock_conn, ("TUTTO",))
        PermissionResolver.get_livello_oggetto(
            _mock_user(7), "vendite", "fattura", "vendite"
        )
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_resolve_livello_oggetto(%s, %s, %s, %s)",
            [7, "vendite", "fattura", "vendite"],
        )


# ── Azione processo ──────────────────────────────────────


class PermissionResolverAzioneTests(TestCase):
    """Test per check_azione — delegata a script.fn_check_azione_processo."""

    # Scopo: Azione abilitata restituisce True.
    @patch(_CONN)
    def test_azione_abilitata(self, mock_conn):
        _setup_cursor(mock_conn, (True,))
        result = PermissionResolver.check_azione(_mock_user(), "genera_fatture_lotti")
        self.assertTrue(result)

    # Scopo: Azione negata restituisce False.
    @patch(_CONN)
    def test_azione_negata(self, mock_conn):
        _setup_cursor(mock_conn, (False,))
        result = PermissionResolver.check_azione(_mock_user(), "genera_fatture_lotti")
        self.assertFalse(result)

    # Scopo: Nessuna riga -> False.
    @patch(_CONN)
    def test_azione_no_row_false(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.check_azione(_mock_user(), "genera_fatture_lotti")
        self.assertFalse(result)

    # Scopo: Verifica parametri SQL corretti.
    @patch(_CONN)
    def test_azione_correct_params(self, mock_conn):
        cursor = _setup_cursor(mock_conn, (True,))
        PermissionResolver.check_azione(_mock_user(5), "reset_lotto")
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_check_azione_processo(%s, %s)",
            [5, "reset_lotto"],
        )


# ── Emittenti fiscali ────────────────────────────────────


class PermissionResolverEmittentiTests(TestCase):
    """Test per get_emittenti_pk_ids (wrapper di
    script.fn_get_emittenti_scope_pk_ids, la canonica guarded — fix B5).
    Fino al 2026-09-12 passavano dall'alias `get_emittenti_ids`, tolto
    (analisi-software-per-dati-morti §2.7)."""

    # Scopo: fn ritorna NULL -> None (nessuna restrizione).
    @patch(_CONN)
    def test_emittenti_null_none(self, mock_conn):
        _setup_cursor(mock_conn, (None,))
        result = PermissionResolver.get_emittenti_pk_ids(_mock_user())
        self.assertIsNone(result)

    # Scopo: Nessuna riga -> None.
    @patch(_CONN)
    def test_emittenti_no_row_none(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.get_emittenti_pk_ids(_mock_user())
        self.assertIsNone(result)

    # Scopo: Array PG -> lista Python.
    @patch(_CONN)
    def test_emittenti_con_righe_lista(self, mock_conn):
        _setup_cursor(mock_conn, ([1, 3, 5],))
        result = PermissionResolver.get_emittenti_pk_ids(_mock_user())
        self.assertEqual(result, [1, 3, 5])

    # Scopo: Verifica il binding alla fn guarded (fix B5):
    # get_emittenti_pk_ids interroga fn_get_emittenti_scope_pk_ids.
    @patch(_CONN)
    def test_emittenti_correct_params(self, mock_conn):
        cursor = _setup_cursor(mock_conn, (None,))
        PermissionResolver.get_emittenti_pk_ids(_mock_user(99))
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_get_emittenti_scope_pk_ids(%s)", [99]
        )


# ── Emittente 1-a-1 (refactor operatore-emittenti) ───────


class PermissionResolverEmittenteForUserTests(TestCase):
    """Test per get_emittente_for_user — delegata a
    script.fn_resolve_emittente_for_user."""

    # Scopo: Operatore con riga -> ritorna PK reale emittenti_fiscali.id.
    @patch(_CONN)
    def test_operatore_con_riga_ritorna_pk(self, mock_conn):
        _setup_cursor(mock_conn, (42,))
        result = PermissionResolver.get_emittente_for_user(_mock_user())
        self.assertEqual(result, 42)
        self.assertIsInstance(result, int)

    # Scopo: Admin globale (0 righe) -> NULL dal DB -> None.
    @patch(_CONN)
    def test_admin_globale_ritorna_none(self, mock_conn):
        _setup_cursor(mock_conn, (None,))
        result = PermissionResolver.get_emittente_for_user(_mock_user())
        self.assertIsNone(result)

    # Scopo: Nessuna riga dalla funzione -> None.
    @patch(_CONN)
    def test_no_row_ritorna_none(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.get_emittente_for_user(_mock_user())
        self.assertIsNone(result)

    # Scopo: Verifica parametri SQL corretti.
    @patch(_CONN)
    def test_emittente_for_user_correct_params(self, mock_conn):
        cursor = _setup_cursor(mock_conn, (7,))
        PermissionResolver.get_emittente_for_user(_mock_user(123))
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_resolve_emittente_for_user(%s)", [123]
        )

    # Scopo: La cache evita una seconda query per lo stesso user.
    @patch(_CONN)
    def test_emittente_for_user_cache(self, mock_conn):
        cursor = _setup_cursor(mock_conn, (5,))
        cache: dict = {}
        first = PermissionResolver.get_emittente_for_user(
            _mock_user(), cache=cache
        )
        second = PermissionResolver.get_emittente_for_user(
            _mock_user(), cache=cache
        )
        self.assertEqual(first, 5)
        self.assertEqual(second, 5)
        # Una sola query nonostante 2 chiamate
        self.assertEqual(cursor.execute.call_count, 1)
        self.assertEqual(cache.get("emittente_for_user"), 5)


# ── Area model override ──────────────────────────────────


class PermissionResolverAreaModelOverrideTests(TestCase):
    """Test per get_area_schema_db — delega a script.fn_area_di_oggetto."""

    # Scopo: L'area la dice la funzione del DB (sede unica della regola, la
    # stessa del guard dei verbi): il resolver la chiama, non la riscrive.
    @patch(_CONN)
    def test_override_trovato(self, mock_conn):
        cursor = _setup_cursor(mock_conn, ("config",))
        result = PermissionResolver.get_area_schema_db("anagrafiche", "qualifiche")
        self.assertEqual(result, "config")
        sql, params = cursor.execute.call_args.args
        self.assertIn("script.fn_area_di_oggetto", sql)
        self.assertEqual(params, ["anagrafiche", "qualifiche"])

    # Scopo: Override non trovato -> fallback ad app_label.
    @patch(_CONN)
    def test_override_non_trovato_fallback(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.get_area_schema_db("vendite", "fattura")
        self.assertEqual(result, "vendite")


# ── Unita' organizzativa ─────────────────────────────────


class PermissionResolverUnitaOrganizzativaTests(TestCase):
    """Test per get_unita_organizzativa_id — delegata a script.fn_get_uo_id_for_user."""

    # Scopo: UO trovata restituisce l'id.
    @patch(_CONN)
    def test_uo_trovata(self, mock_conn):
        cursor = _setup_cursor(mock_conn, (10,))
        result = PermissionResolver.get_unita_organizzativa_id(_mock_user())
        self.assertEqual(result, 10)
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_get_uo_id_for_user(%s)", [1]
        )

    # Scopo: UO non trovata (fn ritorna NULL) -> None.
    @patch(_CONN)
    def test_uo_non_trovata(self, mock_conn):
        _setup_cursor(mock_conn, (None,))
        result = PermissionResolver.get_unita_organizzativa_id(_mock_user())
        self.assertIsNone(result)

    # Scopo: Nessuna riga dalla funzione -> None.
    @patch(_CONN)
    def test_uo_no_row(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.get_unita_organizzativa_id(_mock_user())
        self.assertIsNone(result)


# ── Has profilo reparto area ─────────────────────────────


class PermissionResolverHasProfiloTests(TestCase):
    """Test per has_profilo_applicabile_per_area — EXISTS sull'ereditato
    d'area (`fn_get_permessi_ereditati_aree`, veste OPERATORE)."""

    # Scopo: Esiste un profilo applicabile per l'area -> True.
    @patch(_CONN)
    def test_has_profilo_true(self, mock_conn):
        cursor = _setup_cursor(mock_conn, (True,))
        result = PermissionResolver.has_profilo_applicabile_per_area(
            _mock_user(), "vendite"
        )
        self.assertTrue(result)
        # ⛔ La query legge il passo 4 del resolver, non la raccolta
        # dei profili senza veste: con `fn_get_profili_accesso_applicabili`
        # a 1 argomento un operatore multi-veste conterebbe anche il
        # profilo PORTALE della veste cliente (D-1).
        sql = cursor.execute.call_args[0][0]
        self.assertIn("script.fn_get_permessi_ereditati_aree", sql)
        self.assertNotIn("fn_get_profili_accesso_applicabili", sql)

    # Scopo: Nessun profilo applicabile per l'area -> False.
    @patch(_CONN)
    def test_has_profilo_false(self, mock_conn):
        _setup_cursor(mock_conn, (False,))
        result = PermissionResolver.has_profilo_applicabile_per_area(
            _mock_user(), "vendite"
        )
        self.assertFalse(result)

    # Scopo: Nessuna riga dalla funzione -> False (fail-closed).
    @patch(_CONN)
    def test_has_profilo_no_row(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.has_profilo_applicabile_per_area(
            _mock_user(), "vendite"
        )
        self.assertFalse(result)


# ── Cache per-request ────────────────────────────────────


class PermissionResolverCacheTests(TestCase):
    """Test per comportamento cache per-request."""

    # Scopo: La cache evita query duplicate per lo stesso check.
    @patch(_CONN)
    def test_cache_evita_query_duplicate(self, mock_conn):
        cursor = _setup_cursor(mock_conn, (True,))
        user = _mock_user()
        cache: dict = {}

        r1 = PermissionResolver.is_super_admin(user, cache=cache)
        self.assertTrue(r1)
        self.assertEqual(cursor.execute.call_count, 1)

        r2 = PermissionResolver.is_super_admin(user, cache=cache)
        self.assertTrue(r2)
        self.assertEqual(cursor.execute.call_count, 1)  # nessuna query aggiuntiva

    # Scopo: Chiavi cache diverse non interferiscono.
    @patch(_CONN)
    def test_cache_chiavi_diverse(self, mock_conn):
        cursor = _setup_cursor(mock_conn, ("TUTTO",))
        user = _mock_user()
        cache: dict = {}

        PermissionResolver.get_livello_area(user, "vendite", cache=cache)
        PermissionResolver.get_livello_area(user, "contabilita", cache=cache)
        self.assertEqual(cursor.execute.call_count, 2)

    # Scopo: Senza cache dict, ogni chiamata riesegue la query.
    @patch(_CONN)
    def test_cache_none_non_memorizza(self, mock_conn):
        cursor = _setup_cursor(mock_conn, (True,))
        user = _mock_user()

        PermissionResolver.is_super_admin(user, cache=None)
        PermissionResolver.is_super_admin(user, cache=None)
        self.assertEqual(cursor.execute.call_count, 2)


# ── Helper _cached ───────────────────────────────────────


class CachedHelperTests(TestCase):
    """Test per la funzione helper _cached."""

    # Scopo: Cache hit restituisce il valore senza computare.
    def test_cached_hit(self):
        cache = {"key": "value"}
        result = _cached(cache, "key", lambda: "other")
        self.assertEqual(result, "value")

    # Scopo: Cache miss computa e memorizza il valore.
    def test_cached_miss_stores(self):
        cache: dict = {}
        result = _cached(cache, "key", lambda: "computed")
        self.assertEqual(result, "computed")
        self.assertEqual(cache["key"], "computed")

    # Scopo: Senza cache dict, computa e restituisce senza memorizzare.
    def test_cached_no_dict(self):
        result = _cached(None, "key", lambda: "computed")
        self.assertEqual(result, "computed")
