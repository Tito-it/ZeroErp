# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari PermissionResolver — verifica integrazione
#        con le funzioni SQL script.fn_* e comportamento cache.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_ruolo_operativo
 2) test_ruolo_admin
 3) test_ruolo_disabilitato
 4) test_ruolo_none_senza_bridge
 5) test_ruolo_none_no_row
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


# ── Ruolo sistema ─────────────────────────────────────────


class PermissionResolverRuoloSistemaTests(TestCase):
    """Test per get_ruolo_sistema — delegata a script.fn_get_ruolo_sistema."""

    # Scopo: Ruolo OPERATIVO restituito correttamente.
    @patch(_CONN)
    def test_ruolo_operativo(self, mock_conn):
        cursor = _setup_cursor(mock_conn, ("OPERATIVO",))
        user = _mock_user()
        result = PermissionResolver.get_ruolo_sistema(user)
        self.assertEqual(result, "OPERATIVO")
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_get_ruolo_sistema(%s)", [1]
        )

    # Scopo: Ruolo ADMIN restituito correttamente.
    @patch(_CONN)
    def test_ruolo_admin(self, mock_conn):
        _setup_cursor(mock_conn, ("ADMIN",))
        result = PermissionResolver.get_ruolo_sistema(_mock_user())
        self.assertEqual(result, "ADMIN")

    # Scopo: Ruolo DISABILITATO restituito correttamente.
    @patch(_CONN)
    def test_ruolo_disabilitato(self, mock_conn):
        _setup_cursor(mock_conn, ("DISABILITATO",))
        result = PermissionResolver.get_ruolo_sistema(_mock_user())
        self.assertEqual(result, "DISABILITATO")

    # Scopo: Utente senza bridge (fn ritorna NULL) -> None.
    @patch(_CONN)
    def test_ruolo_none_senza_bridge(self, mock_conn):
        _setup_cursor(mock_conn, (None,))
        result = PermissionResolver.get_ruolo_sistema(_mock_user())
        self.assertIsNone(result)

    # Scopo: Nessuna riga dalla funzione -> None.
    @patch(_CONN)
    def test_ruolo_none_no_row(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.get_ruolo_sistema(_mock_user())
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
    """Test per get_emittenti_ids — delegata a script.fn_get_emittenti_scope."""

    # Scopo: fn ritorna NULL -> None (nessuna restrizione).
    @patch(_CONN)
    def test_emittenti_null_none(self, mock_conn):
        _setup_cursor(mock_conn, (None,))
        result = PermissionResolver.get_emittenti_ids(_mock_user())
        self.assertIsNone(result)

    # Scopo: Nessuna riga -> None.
    @patch(_CONN)
    def test_emittenti_no_row_none(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.get_emittenti_ids(_mock_user())
        self.assertIsNone(result)

    # Scopo: Array PG -> lista Python.
    @patch(_CONN)
    def test_emittenti_con_righe_lista(self, mock_conn):
        _setup_cursor(mock_conn, ([1, 3, 5],))
        result = PermissionResolver.get_emittenti_ids(_mock_user())
        self.assertEqual(result, [1, 3, 5])

    # Scopo: Verifica parametri SQL corretti.
    @patch(_CONN)
    def test_emittenti_correct_params(self, mock_conn):
        cursor = _setup_cursor(mock_conn, (None,))
        PermissionResolver.get_emittenti_ids(_mock_user(99))
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_get_emittenti_scope(%s)", [99]
        )


# ── Area model override ──────────────────────────────────


class PermissionResolverAreaModelOverrideTests(TestCase):
    """Test per get_area_schema_db — query SQL diretta."""

    # Scopo: Override trovato restituisce lo schema_db dell'area.
    @patch(_CONN)
    def test_override_trovato(self, mock_conn):
        _setup_cursor(mock_conn, ("config",))
        result = PermissionResolver.get_area_schema_db("anagrafiche", "qualifiche")
        self.assertEqual(result, "config")

    # Scopo: Override non trovato -> fallback ad app_label.
    @patch(_CONN)
    def test_override_non_trovato_fallback(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.get_area_schema_db("vendite", "fattura")
        self.assertEqual(result, "vendite")


# ── Unita' organizzativa ─────────────────────────────────


class PermissionResolverUnitaOrganizzativaTests(TestCase):
    """Test per get_unita_organizzativa_id — query SQL diretta."""

    # Scopo: UO trovata restituisce l'id.
    @patch(_CONN)
    def test_uo_trovata(self, mock_conn):
        _setup_cursor(mock_conn, (10,))
        result = PermissionResolver.get_unita_organizzativa_id(_mock_user())
        self.assertEqual(result, 10)

    # Scopo: UO non trovata -> None.
    @patch(_CONN)
    def test_uo_non_trovata(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.get_unita_organizzativa_id(_mock_user())
        self.assertIsNone(result)


# ── Has profilo reparto area ─────────────────────────────


class PermissionResolverHasProfiloTests(TestCase):
    """Test per has_profilo_reparto_area — query SQL EXISTS."""

    # Scopo: Reparto con profilo -> True.
    @patch(_CONN)
    def test_has_profilo_true(self, mock_conn):
        _setup_cursor(mock_conn, (True,))
        result = PermissionResolver.has_profilo_reparto_area(_mock_user(), "vendite")
        self.assertTrue(result)

    # Scopo: Reparto senza profilo -> False.
    @patch(_CONN)
    def test_has_profilo_false(self, mock_conn):
        _setup_cursor(mock_conn, (False,))
        result = PermissionResolver.has_profilo_reparto_area(_mock_user(), "vendite")
        self.assertFalse(result)

    # Scopo: Nessuna riga -> False.
    @patch(_CONN)
    def test_has_profilo_no_row(self, mock_conn):
        _setup_cursor(mock_conn, None)
        result = PermissionResolver.has_profilo_reparto_area(_mock_user(), "vendite")
        self.assertFalse(result)


# ── Cache per-request ────────────────────────────────────


class PermissionResolverCacheTests(TestCase):
    """Test per comportamento cache per-request."""

    # Scopo: La cache evita query duplicate per lo stesso ruolo.
    @patch(_CONN)
    def test_cache_evita_query_duplicate(self, mock_conn):
        cursor = _setup_cursor(mock_conn, ("OPERATIVO",))
        user = _mock_user()
        cache: dict = {}

        r1 = PermissionResolver.get_ruolo_sistema(user, cache=cache)
        self.assertEqual(r1, "OPERATIVO")
        self.assertEqual(cursor.execute.call_count, 1)

        r2 = PermissionResolver.get_ruolo_sistema(user, cache=cache)
        self.assertEqual(r2, "OPERATIVO")
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
        cursor = _setup_cursor(mock_conn, ("ADMIN",))
        user = _mock_user()

        PermissionResolver.get_ruolo_sistema(user, cache=None)
        PermissionResolver.get_ruolo_sistema(user, cache=None)
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
