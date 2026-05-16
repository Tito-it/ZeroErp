# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per LogoutView, SessioniAttiveListView,
#        SessioneRevocaView e SessionAuditRepository.list_sessioni_attive.
#        Mock DB, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LogoutViewTests.test_logout_success
2) LogoutViewTests.test_logout_no_token
3) LogoutViewTests.test_logout_chiude_sessione
4) LogoutViewTests.test_logout_token_invalido_idempotente
5) LogoutViewTests.test_logout_token_scaduto_registra_logout
6) SessioniAttiveListViewTests.test_list_sessioni_success
7) SessioniAttiveListViewTests.test_list_sessioni_empty
8) SessioneRevocaViewTests.test_revoca_success
9) SessioneRevocaViewTests.test_revoca_sessione_corrente
10) SessioneRevocaViewTests.test_revoca_sessione_not_found
11) SessioniRevocaTutteViewTests.test_revoca_tutte_success
12) SessioniRevocaTutteViewTests.test_revoca_tutte_senza_remote
13) SessionAuditRepositoryTests.test_list_sessioni_attive
"""

import json
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError

# --------------- helpers ---------------

_LOGOUT_VIEW = "apps.core.api.logout_view"
_SESSIONI_VIEW = "apps.core.api.sessioni_view"
_REPO_PATH = "apps.core.db.session_audit_repository.connection"


def _mock_request(user_id: int = 1, auth: dict | None = None) -> MagicMock:
    """Crea un mock DRF Request con user e auth."""
    request = MagicMock()
    request.user = MagicMock()
    request.user.id = user_id
    request.user.is_authenticated = True
    request.auth = auth
    request._request = MagicMock()
    request._request.META = {
        "REMOTE_ADDR": "127.0.0.1",
        "HTTP_USER_AGENT": "TestBrowser/1.0",
    }
    return request


# --------------- LogoutView ---------------

class LogoutViewTests(TestCase):

    # Scopo: Verifica che POST con refresh token valido → 204 + blacklist + evento LOGOUT con sid.
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.RefreshToken")
    @patch(f"{_LOGOUT_VIEW}.jwt")
    def test_logout_success(self, mock_jwt, MockRefreshToken, mock_audit):
        from apps.core.api.logout_view import LogoutView

        mock_jwt.decode.return_value = {"sid": "sid-abc-123"}
        mock_token = MagicMock()
        MockRefreshToken.return_value = mock_token

        request = _mock_request()
        request.data = {"refresh": "valid-refresh-token"}

        view = LogoutView()
        response = view.post(request)

        self.assertEqual(response.status_code, 204)
        mock_token.blacklist.assert_called_once()
        mock_audit.record_logout.assert_called_once_with(
            user_id=1,
            request=request._request,
            jti="sid-abc-123",
        )

    # Scopo: Verifica che POST senza refresh token → 400 E_LOGOUT_NO_TOKEN.
    def test_logout_no_token(self):
        from apps.core.api.logout_view import LogoutView

        request = _mock_request()
        request.data = {}

        view = LogoutView()
        with self.assertRaises(ServiceError) as ctx:
            view.post(request)

        self.assertEqual(ctx.exception.code, "E_LOGOUT_NO_TOKEN")

    # Scopo: Verifica che POST con token invalido → 204 idempotente (no 500).
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.RefreshToken")
    @patch(f"{_LOGOUT_VIEW}.jwt")
    def test_logout_token_invalido_idempotente(self, mock_jwt, MockRefreshToken, mock_audit):
        from rest_framework_simplejwt.exceptions import TokenError

        from apps.core.api.logout_view import LogoutView

        # jwt.decode fallisce → sid vuoto → record_logout non chiamato
        mock_jwt.decode.side_effect = Exception("Malformed token")
        MockRefreshToken.side_effect = TokenError("Token is invalid or expired")

        request = _mock_request()
        request.data = {"refresh": "invalid-token-string"}

        view = LogoutView()
        response = view.post(request)

        self.assertEqual(response.status_code, 204)
        mock_audit.record_logout.assert_not_called()

    # Scopo: Verifica che POST con token scaduto ma decodificabile → 204 + record_logout con sid.
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.RefreshToken")
    @patch(f"{_LOGOUT_VIEW}.jwt")
    def test_logout_token_scaduto_registra_logout(self, mock_jwt, MockRefreshToken, mock_audit):
        from rest_framework_simplejwt.exceptions import TokenError

        from apps.core.api.logout_view import LogoutView

        # jwt.decode riesce (senza verifica scadenza) → sid estratto
        mock_jwt.decode.return_value = {"sid": "sid-expired-456"}
        # Ma SimpleJWT rifiuta il token → TokenError
        MockRefreshToken.side_effect = TokenError("Token is expired")

        request = _mock_request()
        request.data = {"refresh": "expired-refresh-token"}

        view = LogoutView()
        response = view.post(request)

        self.assertEqual(response.status_code, 204)
        # record_logout viene chiamato anche con token scaduto
        mock_audit.record_logout.assert_called_once_with(
            user_id=1,
            request=request._request,
            jti="sid-expired-456",
        )

    # Scopo: Verifica che dopo logout, record_logout viene chiamato con sid,
    # garantendo che la CTE escludera' la sessione con ultimo evento LOGOUT.
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.RefreshToken")
    @patch(f"{_LOGOUT_VIEW}.jwt")
    def test_logout_chiude_sessione(self, mock_jwt, MockRefreshToken, mock_audit):
        from apps.core.api.logout_view import LogoutView

        mock_jwt.decode.return_value = {"sid": "sid-session-xyz"}
        mock_token = MagicMock()
        MockRefreshToken.return_value = mock_token

        request = _mock_request(user_id=5)
        request.data = {"refresh": "refresh-token-xyz"}

        view = LogoutView()
        view.post(request)

        # Verifica che record_logout e' stato chiamato con sid
        call_kwargs = mock_audit.record_logout.call_args[1]
        self.assertEqual(call_kwargs["jti"], "sid-session-xyz")
        self.assertEqual(call_kwargs["user_id"], 5)


# --------------- SessioniAttiveListView ---------------

class SessioniAttiveListViewTests(TestCase):

    # Scopo: Verifica GET → 200 con lista sessioni (esclusa corrente tramite sid).
    @patch(f"{_SESSIONI_VIEW}.SessionAuditRepository")
    @patch(f"{_SESSIONI_VIEW}.success_response")
    def test_list_sessioni_success(self, mock_resp, MockRepo):
        from apps.core.api.sessioni_view import SessioniAttiveListView

        mock_repo = MagicMock()
        mock_repo.list_sessioni_attive.return_value = [
            {"jti": "current-sid", "ultimo_evento": "LOGIN", "ip_address": "10.0.0.1",
             "user_agent": "Firefox", "data_inizio": datetime(2026, 3, 9, 8, 0),
             "data_ultimo_evento": datetime(2026, 3, 9, 10, 0)},
            {"jti": "other-sid", "ultimo_evento": "LOGIN", "ip_address": "10.0.0.2",
             "user_agent": "Chrome", "data_inizio": datetime(2026, 3, 9, 7, 0),
             "data_ultimo_evento": datetime(2026, 3, 9, 9, 0)},
        ]
        MockRepo.return_value = mock_repo
        mock_resp.return_value = MagicMock(status_code=200)

        # Il sid e' nel claim "sid" dell'access token
        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioniAttiveListView()
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        call_args = mock_resp.call_args[0][0]
        self.assertEqual(call_args["count"], 1)
        self.assertEqual(len(call_args["sessioni"]), 1)
        self.assertEqual(call_args["sessioni"][0]["jti"], "other-sid")

    # Scopo: Verifica GET con nessuna sessione → 200 con lista vuota.
    @patch(f"{_SESSIONI_VIEW}.SessionAuditRepository")
    @patch(f"{_SESSIONI_VIEW}.success_response")
    def test_list_sessioni_empty(self, mock_resp, MockRepo):
        from apps.core.api.sessioni_view import SessioniAttiveListView

        mock_repo = MagicMock()
        mock_repo.list_sessioni_attive.return_value = []
        MockRepo.return_value = mock_repo
        mock_resp.return_value = MagicMock(status_code=200)

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioniAttiveListView()
        view.get(request)

        call_args = mock_resp.call_args[0][0]
        self.assertEqual(call_args["count"], 0)
        self.assertEqual(call_args["sessioni"], [])


# --------------- SessioneRevocaView ---------------

class SessioneRevocaViewTests(TestCase):

    # Scopo: Verifica POST con sid valido → 204 + blacklist token associati + evento REVOCA.
    @patch(f"{_SESSIONI_VIEW}.session_audit_service")
    @patch(f"{_SESSIONI_VIEW}.BlacklistedToken")
    @patch(f"{_SESSIONI_VIEW}.OutstandingToken")
    @patch(f"{_SESSIONI_VIEW}.jwt")
    def test_revoca_success(self, mock_jwt, MockOutstanding, MockBlacklisted, mock_audit):
        from apps.core.api.sessioni_view import SessioneRevocaView

        # Simula un OutstandingToken con sid corrispondente
        mock_ot = MagicMock()
        mock_ot.token = "encoded-jwt-token"
        MockOutstanding.objects.filter.return_value = [mock_ot]
        mock_jwt.decode.return_value = {"sid": "other-sid"}

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioneRevocaView()
        response = view.post(request, jti="other-sid")

        self.assertEqual(response.status_code, 204)
        MockOutstanding.objects.filter.assert_called_once_with(user_id=1)
        MockBlacklisted.objects.get_or_create.assert_called_once_with(token=mock_ot)
        mock_audit.record_revoca.assert_called_once_with(
            user_id=1,
            request=request._request,
            jti="other-sid",
        )

    # Scopo: Verifica POST con sid corrente → 400 E_SESSIONE_REVOCA_CORRENTE.
    def test_revoca_sessione_corrente(self):
        from apps.core.api.sessioni_view import SessioneRevocaView

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioneRevocaView()
        with self.assertRaises(ServiceError) as ctx:
            view.post(request, jti="current-sid")

        self.assertEqual(ctx.exception.code, "E_SESSIONE_REVOCA_CORRENTE")

    # Scopo: Verifica POST con sid inesistente → 404 E_SESSIONE_NOT_FOUND.
    @patch(f"{_SESSIONI_VIEW}.OutstandingToken")
    @patch(f"{_SESSIONI_VIEW}.jwt")
    def test_revoca_sessione_not_found(self, mock_jwt, MockOutstanding):
        from apps.core.api.sessioni_view import SessioneRevocaView

        # Nessun token con sid corrispondente
        MockOutstanding.objects.filter.return_value = []

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioneRevocaView()
        with self.assertRaises(ServiceError) as ctx:
            view.post(request, jti="nonexistent-sid")

        self.assertEqual(ctx.exception.code, "E_SESSIONE_NOT_FOUND")


# --------------- SessioniRevocaTutteView ---------------

class SessioniRevocaTutteViewTests(TestCase):

    # Scopo: Verifica POST bulk → blacklista solo sid remoti distinti e registra REVOCA.
    @patch(f"{_SESSIONI_VIEW}.session_audit_service")
    @patch(f"{_SESSIONI_VIEW}.BlacklistedToken")
    @patch(f"{_SESSIONI_VIEW}.OutstandingToken")
    @patch(f"{_SESSIONI_VIEW}.jwt")
    def test_revoca_tutte_success(self, mock_jwt, MockOutstanding, MockBlacklisted, mock_audit):
        from apps.core.api.sessioni_view import SessioniRevocaTutteView

        current = MagicMock(token="jwt-current")
        other_1 = MagicMock(token="jwt-other-1")
        other_2 = MagicMock(token="jwt-other-2")
        other_2_refresh = MagicMock(token="jwt-other-2-refresh")
        MockOutstanding.objects.filter.return_value = [
            current, other_1, other_2, other_2_refresh,
        ]
        mock_jwt.decode.side_effect = [
            {"sid": "current-sid"},
            {"sid": "other-sid-1"},
            {"sid": "other-sid-2"},
            {"sid": "other-sid-2"},
        ]

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioniRevocaTutteView()
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["data"]["revoked"], 2)
        MockOutstanding.objects.filter.assert_called_once_with(user_id=1)
        self.assertEqual(MockBlacklisted.objects.get_or_create.call_count, 3)
        self.assertEqual(mock_audit.record_revoca.call_count, 2)
        revoked_sids = {
            call.kwargs["jti"]
            for call in mock_audit.record_revoca.call_args_list
        }
        self.assertEqual(revoked_sids, {"other-sid-1", "other-sid-2"})

    # Scopo: Verifica POST bulk senza sessioni remote → 200 con revoked=0.
    @patch(f"{_SESSIONI_VIEW}.session_audit_service")
    @patch(f"{_SESSIONI_VIEW}.BlacklistedToken")
    @patch(f"{_SESSIONI_VIEW}.OutstandingToken")
    @patch(f"{_SESSIONI_VIEW}.jwt")
    def test_revoca_tutte_senza_remote(self, mock_jwt, MockOutstanding, MockBlacklisted, mock_audit):
        from apps.core.api.sessioni_view import SessioniRevocaTutteView

        current = MagicMock(token="jwt-current")
        MockOutstanding.objects.filter.return_value = [current]
        mock_jwt.decode.return_value = {"sid": "current-sid"}

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioniRevocaTutteView()
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["data"]["revoked"], 0)
        MockBlacklisted.objects.get_or_create.assert_not_called()
        mock_audit.record_revoca.assert_not_called()


# --------------- SessionAuditRepository ---------------

class SessionAuditRepositoryTests(TestCase):

    # Scopo: Verifica che list_sessioni_attive restituisce lista di dict dalla query CTE.
    @patch(_REPO_PATH)
    def test_list_sessioni_attive(self, mock_conn):
        from apps.core.db.session_audit_repository import SessionAuditRepository

        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("jti",), ("ultimo_evento",), ("ip_address",),
            ("user_agent",), ("data_inizio",), ("data_ultimo_evento",),
        ]
        mock_cursor.fetchall.return_value = [
            ("sid-1", "LOGIN", "10.0.0.1", "Firefox/100",
             datetime(2026, 3, 9, 8, 0), datetime(2026, 3, 9, 8, 0)),
            ("sid-2", "REFRESH", "10.0.0.2", "Chrome/120",
             datetime(2026, 3, 9, 7, 0), datetime(2026, 3, 9, 9, 0)),
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        repo = SessionAuditRepository()
        result = repo.list_sessioni_attive(auth_user_id=1)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["jti"], "sid-1")
        self.assertEqual(result[0]["ultimo_evento"], "LOGIN")
        self.assertEqual(result[0]["ip_address"], "10.0.0.1")
        self.assertEqual(result[1]["jti"], "sid-2")
        self.assertEqual(result[1]["ultimo_evento"], "REFRESH")
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        self.assertEqual(call_args[1], [1, 1])
