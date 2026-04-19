# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari JwtAuditAuthentication — propagazione GUC
#        sulla connessione PG dopo authenticate() del parent JWT.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_authenticate_returns_none_passthrough — auth fallita → None, niente GUC
2) test_authenticate_success_sets_gucs — auth ok → 1 execute combinata + flag
3) test_set_gucs_uses_session_scope_not_local — set_config con is_local=false
4) test_set_gucs_passes_str_user_and_user_id — params corretti
5) test_set_gucs_database_error_swallowed — DB down → log warning, no raise
6) test_user_without_id_skipped — difensivo: nessun .id → no GUC
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError

from apps.core.api.jwt_audit_authentication import JwtAuditAuthentication

_PARENT_AUTH = (
    "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
)
_CONN = "apps.core.api.jwt_audit_authentication.connection"


def _mock_user(user_id: int = 42, username: str = "mctit") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.__str__ = MagicMock(return_value=username)
    return user


def _mock_request() -> MagicMock:
    return MagicMock(spec=[])


class JwtAuditAuthenticationTests(TestCase):
    """Test per JwtAuditAuthentication."""

    def setUp(self) -> None:
        self.auth = JwtAuditAuthentication()

    # Scopo: Auth fallita (super ritorna None) → ritorna None senza
    # toccare le GUC.
    @patch(_CONN)
    @patch(_PARENT_AUTH, return_value=None)
    def test_authenticate_returns_none_passthrough(self, _parent, mock_conn):
        request = _mock_request()
        result = self.auth.authenticate(request)
        self.assertIsNone(result)
        mock_conn.cursor.assert_not_called()
        self.assertFalse(getattr(request, "_zeroerp_jwt_guc_set", False))

    # Scopo: Auth ok → setta GUC con 1 sola execute + flag su request.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_authenticate_success_sets_gucs(self, mock_parent, mock_conn):
        user = _mock_user(user_id=42, username="mctit")
        token = MagicMock()
        mock_parent.return_value = (user, token)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        result = self.auth.authenticate(request)

        self.assertEqual(result, (user, token))
        self.assertEqual(mock_cursor.execute.call_count, 1)
        self.assertTrue(request._zeroerp_jwt_guc_set)

    # Scopo: La query usa set_config con is_local=false (session-scoped).
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_set_gucs_uses_session_scope_not_local(self, mock_parent, mock_conn):
        mock_parent.return_value = (_mock_user(), MagicMock())
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        self.auth.authenticate(_mock_request())

        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("set_config", sql)
        self.assertIn("app.jwt_user", sql)
        self.assertIn("app.current_user_id", sql)
        self.assertIn("false", sql)
        # No SET LOCAL: persi al COMMIT autocommit
        self.assertNotIn("SET LOCAL", sql)

    # Scopo: Params nell'ordine corretto. Post multi-face: 3 params
    # (user_id per CTE identita, jwt_user, user_id per app.current_user_id).
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_set_gucs_passes_str_user_and_user_id(self, mock_parent, mock_conn):
        mock_parent.return_value = (_mock_user(user_id=99, username="alice"), MagicMock())
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        self.auth.authenticate(_mock_request())

        params = mock_cursor.execute.call_args[0][1]
        self.assertEqual(params, ["99", "alice", "99"])

    # Scopo: DatabaseError dal cursor.execute non deve propagare —
    # cleanup best-effort + log warning. Il flag NON viene settato
    # cosi' il middleware non prova un reset su connessione bacata.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_set_gucs_database_error_swallowed(self, mock_parent, mock_conn):
        user = _mock_user()
        mock_parent.return_value = (user, MagicMock())
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = DatabaseError("DB down")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        # Non deve sollevare
        result = self.auth.authenticate(request)
        self.assertEqual(result, (user, mock_parent.return_value[1]))
        self.assertFalse(getattr(request, "_zeroerp_jwt_guc_set", False))

    # Scopo: User senza .id (caso difensivo) → no GUC, no flag,
    # ritorna comunque il risultato del parent.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_user_without_id_skipped(self, mock_parent, mock_conn):
        user = MagicMock(spec=["__str__"])
        # MagicMock(spec=[...]) non ha .id
        mock_parent.return_value = (user, MagicMock())

        request = _mock_request()
        result = self.auth.authenticate(request)

        self.assertEqual(result, mock_parent.return_value)
        mock_conn.cursor.assert_not_called()
        self.assertFalse(getattr(request, "_zeroerp_jwt_guc_set", False))
