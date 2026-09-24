# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari JwtAuditMiddleware — rifiuto DISABILITATO, reset GUC
#        simmetrico (la cache permessi non si precarica piu' qui).
#        Le GUC di scrittura sono testate in
#        test_jwt_audit_authentication.py (la auth class le setta).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_disabilitato_returns_403_on_api
2) test_disabilitato_no_reject_on_non_api
3) test_anonymous_user_skipped
4) test_operativo_passes_through
5) test_middleware_non_precarica_la_cache_permessi
6) test_process_view_does_not_touch_db
7) test_process_request_resets_gucs_on_reused_connection
8) test_process_request_skips_when_no_connection
9) test_process_request_skips_non_api
10) test_process_request_fail_closed_on_db_error
11) test_process_request_rejects_bypassrls_connection (guard RLS Path A, fail-closed)
12) test_process_request_passes_non_bypassrls_connection (guard ok, verifica una-volta)
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError

import apps.core.middleware.jwt_audit_middleware as jwt_mw
from apps.core.middleware.jwt_audit_middleware import JwtAuditMiddleware

_RESOLVER = "apps.core.middleware.jwt_audit_middleware.PermissionResolver"
_BYPASSRLS = "apps.core.middleware.jwt_audit_middleware.connection_role_bypasses_rls"


def _mock_request(
    path: str = "/api/v1/test/", user_id: int = 1, authenticated: bool = True
) -> MagicMock:
    """Scopo: Crea un mock HttpRequest senza _zeroerp_perms_cache pre-esistente."""
    request = MagicMock(spec=[])
    request.path = path
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = authenticated
    user.__str__ = MagicMock(return_value="testuser")
    request.user = user
    return request


class JwtAuditMiddlewareTests(TestCase):
    """Test per JwtAuditMiddleware."""

    def setUp(self) -> None:
        # Reset del flag di processo del guard BYPASSRLS (evita contaminazione
        # cross-test: è una global verificata-una-volta-per-processo).
        jwt_mw._WEB_CONN_ROLE_VERIFIED = False
        self.middleware = JwtAuditMiddleware(get_response=MagicMock())

    # Scopo: Utente DISABILITATO su path /api/ deve ricevere 403.
    @patch(f"{_RESOLVER}.get_ruolo_applicativo", return_value="DISABILITATO")
    def test_disabilitato_returns_403_on_api(self, _mock_ruolo):
        request = _mock_request(path="/api/v1/vendite/lotti/")
        result = self.middleware.process_view(request, None, (), {})

        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 403)
        body = result.json() if hasattr(result, 'json') else {}
        if body:
            self.assertEqual(body["error"]["code"], "E_USER_DISABILITATO")

    # Scopo: Utente DISABILITATO su path non-API non viene rifiutato.
    @patch(f"{_RESOLVER}.get_ruolo_applicativo", return_value="DISABILITATO")
    def test_disabilitato_no_reject_on_non_api(self, _mock_ruolo):
        request = _mock_request(path="/admin/")
        result = self.middleware.process_view(request, None, (), {})
        self.assertIsNone(result)

    # Scopo: Utente anonimo su /api/* non triggera il check DISABILITATO.
    @patch(f"{_RESOLVER}.get_ruolo_applicativo")
    def test_anonymous_user_skipped(self, mock_ruolo):
        request = _mock_request(authenticated=False)
        request.user.is_authenticated = False
        result = self.middleware.process_view(request, None, (), {})
        self.assertIsNone(result)
        mock_ruolo.assert_not_called()

    # Scopo: Utente OPERATIVO passa senza blocco.
    @patch(f"{_RESOLVER}.get_ruolo_applicativo", return_value="OPERATORE")
    def test_operativo_passes_through(self, _mock_ruolo):
        request = _mock_request()
        result = self.middleware.process_view(request, None, (), {})
        self.assertIsNone(result)

    # Scopo: il middleware NON precarica piu' la cache permessi: la sua chiave
    # e' il contesto di sessione, che nasce dopo (in set_jwt_gucs). M-1.
    @patch(f"{_RESOLVER}.get_ruolo_applicativo", return_value="OPERATORE")
    def test_middleware_non_precarica_la_cache_permessi(self, _mock_ruolo):
        request = _mock_request()
        self.middleware.process_view(request, None, (), {})
        self.assertFalse(hasattr(request, "_zeroerp_perms_cache"))

    # Scopo: process_view non tocca PIU' il DB (le GUC sono settate
    # da JwtAuditAuthentication, non qui). Verifica regressione.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    @patch(f"{_RESOLVER}.get_ruolo_applicativo", return_value="OPERATORE")
    def test_process_view_does_not_touch_db(self, _mock_ruolo, mock_conn):
        request = _mock_request()
        self.middleware.process_view(request, None, (), {})
        mock_conn.cursor.assert_not_called()

    # Scopo: process_request azzera i 5 GUC in 1 sola execute quando
    # esiste gia' una connessione (potenzialmente sporca di una request
    # precedente con CONN_MAX_AGE>0). Incondizionato rispetto all'auth.
    @patch(_BYPASSRLS, return_value=False)
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    def test_process_request_resets_gucs_on_reused_connection(self, mock_conn, _mock_bypass):
        mock_conn.connection = object()  # connessione gia' stabilita (riusata)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()  # nessun marker auth: deve resettare comunque
        result = self.middleware.process_request(request)

        self.assertIsNone(result)
        self.assertEqual(mock_cursor.execute.call_count, 1)
        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("set_config", sql)
        # Reset dei 5 GUC settati da JwtAuditAuthentication.
        self.assertIn("app.jwt_user", sql)
        self.assertIn("app.current_user_id", sql)
        self.assertIn("app.current_identita_id", sql)
        self.assertIn("app.ruolo_applicativo", sql)
        self.assertIn("app.soggetto_ruolo_id", sql)
        self.assertIn("''", sql)
        self.assertIn("false", sql)

    # Scopo: connessione NON ancora aperta (fresca → GUC gia' puliti) →
    # nessun accesso DB. Critico per SimpleTestCase API: senza questo
    # gate i test API senza DB andrebbero in DatabaseOperationForbidden.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    def test_process_request_skips_when_no_connection(self, mock_conn):
        mock_conn.connection = None  # nessuna connessione stabilita
        request = _mock_request()
        result = self.middleware.process_request(request)
        self.assertIsNone(result)
        mock_conn.cursor.assert_not_called()

    # Scopo: path non-/api/ → nessun reset (e nessun accesso DB).
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    def test_process_request_skips_non_api(self, mock_conn):
        mock_conn.connection = object()
        request = _mock_request(path="/admin/")
        result = self.middleware.process_request(request)
        self.assertIsNone(result)
        mock_conn.cursor.assert_not_called()

    # Scopo: FAIL-CLOSED — se il reset GUC fallisce, la request NON viene
    # servita (500), per non procedere con uno scope ereditato.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    def test_process_request_fail_closed_on_db_error(self, mock_conn):
        mock_conn.connection = object()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = DatabaseError("boom")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        result = self.middleware.process_request(request)

        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 500)
        body = result.json() if hasattr(result, "json") else {}
        if body:
            self.assertEqual(body["error"]["code"], "E_GUC_RESET_FAILED")

    # Scopo: guard RLS Path A — se la connessione del percorso richiesta è su un
    # ruolo BYPASSRLS (DB_USER misconfigurato sul ruolo batch o misuse del gateway
    # di sistema nel web) la richiesta è rifiutata (500, fail-closed).
    @patch(_BYPASSRLS, return_value=True)
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    def test_process_request_rejects_bypassrls_connection(self, mock_conn, _mock_bypass):
        mock_conn.connection = object()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        result = self.middleware.process_request(request)

        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 500)
        body = result.json() if hasattr(result, "json") else {}
        if body:
            self.assertEqual(body["error"]["code"], "E_DB_ROLE_UNSAFE")
        # Flag NON deve essere stato impostato: ogni richiesta resta rifiutata.
        self.assertFalse(jwt_mw._WEB_CONN_ROLE_VERIFIED)

    # Scopo: guard RLS Path A — connessione web su ruolo NON-BYPASSRLS passa, e la
    # verifica avviene UNA sola volta per processo (flag memorizzato).
    @patch(_BYPASSRLS, return_value=False)
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    def test_process_request_passes_non_bypassrls_connection(self, mock_conn, mock_bypass):
        mock_conn.connection = object()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        self.assertIsNone(self.middleware.process_request(_mock_request()))
        self.assertTrue(jwt_mw._WEB_CONN_ROLE_VERIFIED)
        # Seconda richiesta: il guard non interroga più il DB (verificato-una-volta).
        self.assertIsNone(self.middleware.process_request(_mock_request()))
        self.assertEqual(mock_bypass.call_count, 1)
