# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari JwtAuditMiddleware — pre-load cache permessi,
#        rifiuto DISABILITATO, reset GUC simmetrico.
#        Le GUC di scrittura sono testate in
#        test_jwt_audit_authentication.py (la auth class le setta).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_disabilitato_returns_403_on_api
2) test_disabilitato_no_reject_on_non_api
3) test_anonymous_user_skipped
4) test_operativo_passes_through
5) test_middleware_seeds_perms_cache
6) test_middleware_seeds_perms_cache_from_redis
7) test_process_view_does_not_touch_db
8) test_process_response_resets_gucs_when_flag_set
9) test_process_response_no_flag_no_reset
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.middleware.jwt_audit_middleware import JwtAuditMiddleware

_RESOLVER = "apps.core.middleware.jwt_audit_middleware.PermissionResolver"
_LOAD_CACHE = "apps.core.middleware.jwt_audit_middleware.load_user_cache"


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
        self.middleware = JwtAuditMiddleware(get_response=MagicMock())

    # Scopo: Utente DISABILITATO su path /api/ deve ricevere 403.
    @patch(_LOAD_CACHE, return_value=None)
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="DISABILITATO")
    def test_disabilitato_returns_403_on_api(self, _mock_ruolo, _mock_load):
        request = _mock_request(path="/api/v1/vendite/lotti/")
        result = self.middleware.process_view(request, None, (), {})

        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 403)
        body = result.json() if hasattr(result, 'json') else {}
        if body:
            self.assertEqual(body["error"]["code"], "E_USER_DISABILITATO")

    # Scopo: Utente DISABILITATO su path non-API non viene rifiutato.
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="DISABILITATO")
    def test_disabilitato_no_reject_on_non_api(self, _mock_ruolo):
        request = _mock_request(path="/admin/")
        result = self.middleware.process_view(request, None, (), {})
        self.assertIsNone(result)

    # Scopo: Utente anonimo su /api/* non triggera ne' cache ne' check.
    @patch(_LOAD_CACHE)
    def test_anonymous_user_skipped(self, mock_load):
        request = _mock_request(authenticated=False)
        request.user.is_authenticated = False
        result = self.middleware.process_view(request, None, (), {})
        self.assertIsNone(result)
        mock_load.assert_not_called()

    # Scopo: Utente OPERATIVO passa senza blocco.
    @patch(_LOAD_CACHE, return_value=None)
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="OPERATIVO")
    def test_operativo_passes_through(self, _mock_ruolo, _mock_load):
        request = _mock_request()
        result = self.middleware.process_view(request, None, (), {})
        self.assertIsNone(result)

    # Scopo: Il middleware inizializza _zeroerp_perms_cache sulla request (Redis miss).
    @patch(_LOAD_CACHE, return_value=None)
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="OPERATIVO")
    def test_middleware_seeds_perms_cache(self, _mock_ruolo, _mock_load):
        request = _mock_request()
        self.middleware.process_view(request, None, (), {})
        self.assertTrue(hasattr(request, "_zeroerp_perms_cache"))
        self.assertIsInstance(request._zeroerp_perms_cache, dict)
        self.assertFalse(request._zeroerp_perms_cache_loaded_from_redis)

    # Scopo: Il middleware carica cache L2 da Redis quando disponibile.
    @patch(_LOAD_CACHE, return_value={"ruolo_sistema": "OPERATIVO"})
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="OPERATIVO")
    def test_middleware_seeds_perms_cache_from_redis(self, _mock_ruolo, _mock_load):
        request = _mock_request()
        self.middleware.process_view(request, None, (), {})
        self.assertEqual(request._zeroerp_perms_cache, {"ruolo_sistema": "OPERATIVO"})
        self.assertTrue(request._zeroerp_perms_cache_loaded_from_redis)

    # Scopo: process_view non tocca PIU' il DB (le GUC sono settate
    # da JwtAuditAuthentication, non qui). Verifica regressione.
    @patch(_LOAD_CACHE, return_value=None)
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="OPERATIVO")
    def test_process_view_does_not_touch_db(self, _mock_ruolo, mock_conn, _mock_load):
        request = _mock_request()
        self.middleware.process_view(request, None, (), {})
        mock_conn.cursor.assert_not_called()

    # Scopo: process_response resetta le GUC in 1 sola execute SE
    # JwtAuditAuthentication ha settato il flag _zeroerp_jwt_guc_set.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    def test_process_response_resets_gucs_when_flag_set(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        request._zeroerp_jwt_guc_set = True  # simula auth class eseguita
        response_in = MagicMock()
        response_out = self.middleware.process_response(request, response_in)

        self.assertIs(response_out, response_in)
        self.assertEqual(mock_cursor.execute.call_count, 1)
        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("set_config", sql)
        self.assertIn("app.jwt_user", sql)
        self.assertIn("app.current_user_id", sql)
        self.assertIn("''", sql)
        self.assertIn("false", sql)

    # Scopo: process_response NON tocca il DB se il flag non e' settato
    # (request anonima oppure auth fallita). Critico per
    # SimpleTestCase API: senza questa condizione tutti i test API
    # andrebbero in DatabaseOperationForbidden.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    def test_process_response_no_flag_no_reset(self, mock_conn):
        request = _mock_request()
        # nessun _zeroerp_jwt_guc_set sulla request
        response_in = MagicMock()
        response_out = self.middleware.process_response(request, response_in)
        self.assertIs(response_out, response_in)
        mock_conn.cursor.assert_not_called()
