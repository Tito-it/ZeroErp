# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari JwtAuditMiddleware — reset GUC di inizio richiesta e
#        guard BYPASSRLS. Il rifiuto DISABILITATO non e' piu' qui (S-2).
#        Le GUC di scrittura sono testate in
#        test_jwt_audit_authentication.py (la auth class le setta).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_il_middleware_non_ha_process_view (S-2)
2) test_process_request_resets_gucs_on_reused_connection
3) test_process_request_skips_when_no_connection
4) test_process_request_skips_non_api
5) test_process_request_fail_closed_on_db_error
6) test_process_request_rejects_bypassrls_connection (guard RLS Path A, fail-closed)
7) test_process_request_passes_non_bypassrls_connection (guard ok, verifica una-volta)
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError

import apps.core.middleware.jwt_audit_middleware as jwt_mw
from apps.core.middleware.jwt_audit_middleware import JwtAuditMiddleware

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

    # Scopo: ⛔ Il middleware NON ha `process_view` (ritirato il 2026-09-28,
    # analisi difetti doc API core S-2). Rifiutava i DISABILITATO, ma a quel
    # punto `request.user` e' l'utente di SESSIONE: per un client Bearer e'
    # anonimo (l'auth DRF gira dopo), e il ramo non scattava mai — i test che
    # lo provavano mettevano a mano un utente autenticato. Il rifiuto vero e'
    # nella catena di `ZeroERPPermission` (test_permissions). Questo test
    # impedisce che una seconda sede inerte torni a sembrare una difesa.
    def test_il_middleware_non_ha_process_view(self):
        self.assertFalse(hasattr(JwtAuditMiddleware, "process_view"))

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
