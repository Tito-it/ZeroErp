# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per AuditTokenObtainPairView e AuditTokenRefreshView.
#        Mock service e SimpleJWT, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) AuditAuthViewsTests.test_login_success_calls_record_login
2) AuditAuthViewsTests.test_login_failure_no_record
3) AuditAuthViewsTests.test_refresh_success_calls_record_refresh
4) AuditAuthViewsTests.test_refresh_failure_no_record
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from rest_framework.response import Response

from apps.core.api.auth_views import AuditTokenObtainPairView, AuditTokenRefreshView

_SERVICE = "apps.core.api.auth_views.session_audit_service"


class AuditAuthViewsTests(TestCase):

    # Scopo: Verifica che login con successo chiami record_login con user_id e jti.
    @patch(f"{_SERVICE}.record_login")
    @patch.object(AuditTokenObtainPairView, "_extract_claims", return_value=(42, "jti-abc"))
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_login_success_calls_record_login(
        self, mock_super_post, mock_extract, mock_record
    ):
        mock_super_post.return_value = Response(
            {"access": "tok.en.jwt", "refresh": "ref.tok.en"},
            status=200,
        )
        request = MagicMock()
        request._request = MagicMock()

        view = AuditTokenObtainPairView()
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once_with(
            user_id=42,
            request=request._request,
            jti="jti-abc",
        )

    # Scopo: Verifica che login fallito non chiami record_login.
    @patch(f"{_SERVICE}.record_login")
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_login_failure_no_record(self, mock_super_post, mock_record):
        mock_super_post.return_value = Response(
            {"detail": "Invalid credentials"},
            status=401,
        )
        request = MagicMock()

        view = AuditTokenObtainPairView()
        response = view.post(request)

        self.assertEqual(response.status_code, 401)
        mock_record.assert_not_called()

    # Scopo: Verifica che refresh con successo chiami record_refresh con user_id e jti.
    @patch(f"{_SERVICE}.record_refresh")
    @patch.object(AuditTokenRefreshView, "_extract_claims", return_value=(42, "jti-xyz"))
    @patch("rest_framework_simplejwt.views.TokenRefreshView.post")
    def test_refresh_success_calls_record_refresh(
        self, mock_super_post, mock_extract, mock_record
    ):
        mock_super_post.return_value = Response(
            {"access": "new.tok.en"},
            status=200,
        )
        request = MagicMock()
        request._request = MagicMock()

        view = AuditTokenRefreshView()
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once_with(
            user_id=42,
            request=request._request,
            jti="jti-xyz",
        )

    # Scopo: Verifica che refresh fallito non chiami record_refresh.
    @patch(f"{_SERVICE}.record_refresh")
    @patch("rest_framework_simplejwt.views.TokenRefreshView.post")
    def test_refresh_failure_no_record(self, mock_super_post, mock_record):
        mock_super_post.return_value = Response(
            {"detail": "Token is invalid"},
            status=401,
        )
        request = MagicMock()

        view = AuditTokenRefreshView()
        response = view.post(request)

        self.assertEqual(response.status_code, 401)
        mock_record.assert_not_called()
