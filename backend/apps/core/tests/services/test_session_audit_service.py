# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per session_audit_service — mock DB,
#        compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) SessionAuditServiceTests.test_record_login_calls_repository
2) SessionAuditServiceTests.test_record_refresh_calls_repository
3) SessionAuditServiceTests.test_record_login_with_jti
4) SessionAuditServiceTests.test_get_client_ip_from_xff
5) SessionAuditServiceTests.test_get_client_ip_from_remote_addr
6) SessionAuditServiceTests.test_get_user_agent_truncated
7) SessionAuditServiceTests.test_record_login_db_error_silent
8) SessionAuditServiceTests.test_record_logout_calls_repository
9) SessionAuditServiceTests.test_record_revoca_calls_repository
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services import session_audit_service
from apps.core.services.request_context import get_client_ip, get_user_agent

_REPO = "apps.core.services.session_audit_service.SessionAuditRepository"
_GET_REQ_ID = "apps.core.services.session_audit_service.get_request_id"


def _mock_request(
    ip: str = "192.168.1.1",
    user_agent: str = "TestBrowser/1.0",
    xff: str | None = None,
) -> MagicMock:
    """Scopo: Crea un mock HttpRequest con META."""
    request = MagicMock()
    meta = {
        "REMOTE_ADDR": ip,
        "HTTP_USER_AGENT": user_agent,
    }
    if xff:
        meta["HTTP_X_FORWARDED_FOR"] = xff
    request.META = meta
    return request


class SessionAuditServiceTests(TestCase):

    # Scopo: Verifica che record_login chiami il repository con i parametri corretti.
    @patch(_GET_REQ_ID, return_value="abc-123")
    @patch(_REPO)
    def test_record_login_calls_repository(self, MockRepo, _mock_req_id):
        repo = MockRepo.return_value
        request = _mock_request()

        session_audit_service.record_login(user_id=1, request=request)

        repo.log_session_event.assert_called_once_with(
            auth_user_id=1,
            evento="LOGIN",
            jti=None,
            ip_address="192.168.1.1",
            user_agent="TestBrowser/1.0",
            request_id="abc-123",
            dettaglio=None,
        )

    # Scopo: Verifica che record_refresh chiami il repository con evento REFRESH.
    @patch(_GET_REQ_ID, return_value=None)
    @patch(_REPO)
    def test_record_refresh_calls_repository(self, MockRepo, _mock_req_id):
        repo = MockRepo.return_value
        request = _mock_request()

        session_audit_service.record_refresh(user_id=2, request=request)

        repo.log_session_event.assert_called_once_with(
            auth_user_id=2,
            evento="REFRESH",
            jti=None,
            ip_address="192.168.1.1",
            user_agent="TestBrowser/1.0",
            request_id=None,
            dettaglio=None,
        )

    # Scopo: Verifica che record_login passi jti al repository.
    @patch(_GET_REQ_ID, return_value=None)
    @patch(_REPO)
    def test_record_login_with_jti(self, MockRepo, _mock_req_id):
        repo = MockRepo.return_value
        request = _mock_request()

        session_audit_service.record_login(
            user_id=1, request=request, jti="token-jti-123",
        )

        call_kwargs = repo.log_session_event.call_args[1]
        self.assertEqual(call_kwargs["jti"], "token-jti-123")

    # Scopo: Verifica che l'IP venga estratto da X-Forwarded-For.
    def test_get_client_ip_from_xff(self):
        request = _mock_request(xff="10.0.0.1, 10.0.0.2")
        ip = get_client_ip(request)
        self.assertEqual(ip, "10.0.0.1")

    # Scopo: Verifica fallback su REMOTE_ADDR.
    def test_get_client_ip_from_remote_addr(self):
        request = _mock_request(ip="172.16.0.1")
        ip = get_client_ip(request)
        self.assertEqual(ip, "172.16.0.1")

    # Scopo: Verifica troncamento User-Agent a 500 caratteri.
    def test_get_user_agent_truncated(self):
        long_ua = "A" * 600
        request = _mock_request(user_agent=long_ua)
        ua = get_user_agent(request)
        self.assertEqual(len(ua), 500)

    # Scopo: Verifica che errori DB vengano gestiti silenziosamente (no eccezione).
    @patch(_GET_REQ_ID, return_value=None)
    @patch(_REPO)
    def test_record_login_db_error_silent(self, MockRepo, _mock_req_id):
        repo = MockRepo.return_value
        repo.log_session_event.side_effect = RuntimeError("DB down")
        request = _mock_request()

        # Non deve sollevare eccezioni
        session_audit_service.record_login(user_id=1, request=request)

    # Scopo: Verifica che record_logout chiami il repository con evento LOGOUT.
    @patch(_GET_REQ_ID, return_value=None)
    @patch(_REPO)
    def test_record_logout_calls_repository(self, MockRepo, _mock_req_id):
        repo = MockRepo.return_value
        request = _mock_request()

        session_audit_service.record_logout(user_id=3, request=request, jti="jti-logout")

        repo.log_session_event.assert_called_once_with(
            auth_user_id=3,
            evento="LOGOUT",
            jti="jti-logout",
            ip_address="192.168.1.1",
            user_agent="TestBrowser/1.0",
            request_id=None,
            dettaglio=None,
        )

    # Scopo: Verifica che record_revoca chiami il repository con evento REVOCA.
    @patch(_GET_REQ_ID, return_value=None)
    @patch(_REPO)
    def test_record_revoca_calls_repository(self, MockRepo, _mock_req_id):
        repo = MockRepo.return_value
        request = _mock_request()

        session_audit_service.record_revoca(user_id=4, request=request, jti="jti-revoca")

        repo.log_session_event.assert_called_once_with(
            auth_user_id=4,
            evento="REVOCA",
            jti="jti-revoca",
            ip_address="192.168.1.1",
            user_agent="TestBrowser/1.0",
            request_id=None,
            dettaglio=None,
        )
