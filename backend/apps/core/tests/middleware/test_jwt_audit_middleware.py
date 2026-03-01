# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari JwtAuditMiddleware — GUC PG e rifiuto DISABILITATO.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_set_local_jwt_user_and_current_user_id
2) test_disabilitato_returns_403_on_api
3) test_disabilitato_no_reject_on_non_api
4) test_anonymous_user_no_guc_set
5) test_operativo_passes_through
6) test_middleware_seeds_perms_cache
"""

from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

from apps.core.middleware.jwt_audit_middleware import JwtAuditMiddleware

_RESOLVER = "apps.core.middleware.jwt_audit_middleware.PermissionResolver"


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

    # Scopo: Verifica che SET LOCAL imposti sia jwt_user che current_user_id.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="OPERATIVO")
    def test_set_local_jwt_user_and_current_user_id(self, _mock_ruolo, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        result = self.middleware.process_view(request, None, (), {})

        self.assertIsNone(result)
        # Deve chiamare execute 2 volte: SET LOCAL e set_config
        self.assertEqual(mock_cursor.execute.call_count, 2)
        calls = mock_cursor.execute.call_args_list
        self.assertIn("app.jwt_user", calls[0][0][0])
        self.assertIn("app.current_user_id", calls[1][0][0])

    # Scopo: Utente DISABILITATO su path /api/ deve ricevere 403.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="DISABILITATO")
    def test_disabilitato_returns_403_on_api(self, _mock_ruolo, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request(path="/api/v1/vendite/lotti/")
        result = self.middleware.process_view(request, None, (), {})

        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 403)
        body = result.json() if hasattr(result, 'json') else {}
        if body:
            self.assertEqual(body["error"]["code"], "E_USER_DISABILITATO")

    # Scopo: Utente DISABILITATO su path non-API non viene rifiutato.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="DISABILITATO")
    def test_disabilitato_no_reject_on_non_api(self, _mock_ruolo, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request(path="/admin/")
        result = self.middleware.process_view(request, None, (), {})
        self.assertIsNone(result)

    # Scopo: Utente anonimo non causa nessun SET LOCAL.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    def test_anonymous_user_no_guc_set(self, mock_conn):
        request = _mock_request(authenticated=False)
        request.user.is_authenticated = False
        result = self.middleware.process_view(request, None, (), {})
        self.assertIsNone(result)
        mock_conn.cursor.assert_not_called()

    # Scopo: Utente OPERATIVO passa senza blocco.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="OPERATIVO")
    def test_operativo_passes_through(self, _mock_ruolo, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        result = self.middleware.process_view(request, None, (), {})
        self.assertIsNone(result)

    # Scopo: Il middleware inizializza _zeroerp_perms_cache sulla request.
    @patch("apps.core.middleware.jwt_audit_middleware.connection")
    @patch(f"{_RESOLVER}.get_ruolo_sistema", return_value="OPERATIVO")
    def test_middleware_seeds_perms_cache(self, _mock_ruolo, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        self.middleware.process_view(request, None, (), {})
        # La cache per-request deve essere stata creata dal middleware
        self.assertTrue(hasattr(request, "_zeroerp_perms_cache"))
        self.assertIsInstance(request._zeroerp_perms_cache, dict)
