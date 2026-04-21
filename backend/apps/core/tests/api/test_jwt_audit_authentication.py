# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari JwtAuditAuthentication — propagazione GUC
#        sulla connessione PG dopo authenticate() del parent JWT.
#        Post §8.3.4: l'autenticazione valida il claim `identita_id`
#        e popola 3 GUC di identita in singola query CTE.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_authenticate_returns_none_passthrough — auth fallita → None, niente GUC
 2) test_authenticate_success_sets_gucs — auth ok → 1 execute + flag su request
 3) test_set_gucs_uses_session_scope_not_local — set_config con is_local=false
 4) test_set_gucs_passes_identita_user_and_username — params nel giusto ordine
 5) test_set_gucs_database_error_swallowed — DB down → no raise, no flag
 6) test_user_without_id_skipped — difensivo: nessun .id → no GUC
 7) test_jwt_senza_identita_claim_raise_401 — token senza claim → E_JWT_SENZA_IDENTITA
 8) test_identita_non_attiva_raise_401 — CTE count 0 → E_IDENTITA_NON_ATTIVA
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError

from apps.core.api.jwt_audit_authentication import (
    IdentitaNonAttivaError,
    JwtAuditAuthentication,
    JwtSenzaIdentitaError,
)

_PARENT_AUTH = (
    "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
)
_CONN = "apps.core.api.jwt_audit_authentication.connection"


def _mock_user(user_id: int = 42, username: str = "mctit") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.__str__ = MagicMock(return_value=username)
    return user


def _mock_token_with_identita(identita_id: int | None = 7) -> MagicMock:
    """Token validato SimpleJWT: espone `.get(claim)`. Se identita_id
    e' None simula un token pre-§8.3.2 (senza claim)."""
    token = MagicMock()
    def _get(key, default=None):
        if key == "identita_id":
            return identita_id
        return default
    token.get = MagicMock(side_effect=_get)
    return token


def _mock_request() -> MagicMock:
    return MagicMock(spec=[])


def _mock_cursor_row(mock_conn, *, identita_count: int = 1) -> MagicMock:
    """Configura connection.cursor() come context manager e
    fa ritornare 6 colonne da fetchone(), layout della query CTE di
    `set_jwt_gucs`:
      idx 0..4 → risultati set_config (stringhe settate: jwt_user,
                  current_user_id, current_identita_id, ruolo_applicativo,
                  soggetto_ruolo_id). Valori simulati '' perche' il test
                  non li legge — importa solo il numero di colonne.
      idx 5   → COUNT(*) da id_row, usato dal codice per decidere
                  `identita_trovata`.
    Se modifichi la query CTE (aggiungi/rimuovi GUC), aggiorna qui di
    conseguenza oppure il test diventa silenziosamente permissivo."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("", "", "", "", "", identita_count)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_cursor


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

    # Scopo: Auth ok + claim identita_id presente + CTE trova identita
    # attiva → 1 execute + flag su request.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_authenticate_success_sets_gucs(self, mock_parent, mock_conn):
        user = _mock_user(user_id=42, username="mctit")
        token = _mock_token_with_identita(identita_id=7)
        mock_parent.return_value = (user, token)
        mock_cursor = _mock_cursor_row(mock_conn, identita_count=1)

        request = _mock_request()
        result = self.auth.authenticate(request)

        self.assertEqual(result, (user, token))
        self.assertEqual(mock_cursor.execute.call_count, 1)
        self.assertTrue(request._zeroerp_jwt_guc_set)

    # Scopo: La query usa set_config con is_local=false (session-scoped).
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_set_gucs_uses_session_scope_not_local(self, mock_parent, mock_conn):
        mock_parent.return_value = (_mock_user(), _mock_token_with_identita())
        mock_cursor = _mock_cursor_row(mock_conn)

        self.auth.authenticate(_mock_request())

        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("set_config", sql)
        self.assertIn("app.jwt_user", sql)
        self.assertIn("app.current_user_id", sql)
        self.assertIn("app.current_identita_id", sql)
        self.assertIn("false", sql)
        self.assertNotIn("SET LOCAL", sql)

    # Scopo: Params nell'ordine del nuovo set_jwt_gucs con identita_id:
    # [identita_id, user_id (CTE), username, user_id (GUC)]
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_set_gucs_passes_identita_user_and_username(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(user_id=99, username="alice"),
            _mock_token_with_identita(identita_id=501),
        )
        mock_cursor = _mock_cursor_row(mock_conn)

        self.auth.authenticate(_mock_request())

        params = mock_cursor.execute.call_args[0][1]
        self.assertEqual(params, ["501", "99", "alice", "99"])

    # Scopo: DatabaseError dal cursor.execute non deve propagare —
    # cleanup best-effort + log warning. Ma set_jwt_gucs ritorna False
    # → authenticate solleva IdentitaNonAttivaError.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_set_gucs_database_error_swallowed(self, mock_parent, mock_conn):
        user = _mock_user()
        token = _mock_token_with_identita()
        mock_parent.return_value = (user, token)
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = DatabaseError("DB down")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        # DB down → CTE fallisce → identita non trovata → 401.
        with self.assertRaises(IdentitaNonAttivaError):
            self.auth.authenticate(request)
        self.assertFalse(getattr(request, "_zeroerp_jwt_guc_set", False))

    # Scopo: User senza .id (caso difensivo) → no GUC, no flag,
    # ritorna comunque il risultato del parent.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_user_without_id_skipped(self, mock_parent, mock_conn):
        user = MagicMock(spec=["__str__"])
        # MagicMock(spec=[...]) non ha .id
        mock_parent.return_value = (user, _mock_token_with_identita())

        request = _mock_request()
        result = self.auth.authenticate(request)

        self.assertEqual(result, mock_parent.return_value)
        mock_conn.cursor.assert_not_called()
        self.assertFalse(getattr(request, "_zeroerp_jwt_guc_set", False))

    # Scopo: Token senza claim identita_id (vecchio stile pre-§8.3.2)
    # → JwtSenzaIdentitaError (401 E_JWT_SENZA_IDENTITA).
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_jwt_senza_identita_claim_raise_401(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(),
            _mock_token_with_identita(identita_id=None),
        )
        with self.assertRaises(JwtSenzaIdentitaError) as ctx:
            self.auth.authenticate(_mock_request())
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.default_code, "E_JWT_SENZA_IDENTITA")
        # La CTE non deve essere stata eseguita (fail prima).
        mock_conn.cursor.assert_not_called()

    # Scopo: Claim presente ma la coppia (user, identita) non e' attiva
    # (CTE count = 0) → IdentitaNonAttivaError (401).
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_identita_non_attiva_raise_401(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(),
            _mock_token_with_identita(identita_id=999),
        )
        _mock_cursor_row(mock_conn, identita_count=0)

        with self.assertRaises(IdentitaNonAttivaError) as ctx:
            self.auth.authenticate(_mock_request())
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.default_code, "E_IDENTITA_NON_ATTIVA")
