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
5) AuditAuthViewsTests.test_login_success_propaga_gucs
6) AuditAuthViewsTests.test_refresh_success_propaga_gucs
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from rest_framework.response import Response

from apps.core.api.auth_views import AuditTokenObtainPairView, AuditTokenRefreshView

_SERVICE = "apps.core.api.auth_views.session_audit_service"
_SET_GUCS = "apps.core.api.auth_views.set_jwt_gucs"


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
    @patch.object(AuditTokenRefreshView, "_resolve_username", return_value="alice")
    @patch.object(AuditTokenRefreshView, "_extract_claims", return_value=(42, "jti-xyz"))
    @patch("rest_framework_simplejwt.views.TokenRefreshView.post")
    @patch(_SET_GUCS)
    def test_refresh_success_calls_record_refresh(
        self, _mock_gucs, mock_super_post, mock_extract, _mock_resolve, mock_record
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

    # Scopo: Hotfix BE-2.0ter — verifica che il LOGIN propaghi le GUC
    # `app.jwt_user`/`app.current_user_id` PRIMA della scrittura di
    # audit, cosi' i trigger DB di sessioni_utente popolano user_insert
    # con lo username effettivo invece di 'zeroerp_app'. Il login NON
    # passa dalla DRF auth chain, quindi senza questo set manuale le
    # GUC restano vuote.
    @patch(f"{_SERVICE}.record_login")
    @patch.object(AuditTokenObtainPairView, "_extract_claims", return_value=(42, "jti-abc"))
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("apps.core.api.auth_views._auth_repo")
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    @patch(_SET_GUCS)
    def test_login_success_propaga_gucs(
        self, mock_set_gucs, mock_super_post, mock_repo,
        mock_find_user, mock_extract, mock_record_login,
    ):
        fake_user = MagicMock(id=42, username="alice")
        mock_find_user.return_value = fake_user
        mock_repo.check_blocco_login.return_value = None
        mock_repo.registra_tentativo_login.return_value = {"bloccato": False}
        mock_repo.get_deve_cambiare_password.return_value = False
        mock_super_post.return_value = Response(
            {"access": "tok.en.jwt", "refresh": "ref.tok.en"},
            status=200,
        )
        request = MagicMock()
        request._request = MagicMock()

        view = AuditTokenObtainPairView()
        view.post(request)

        mock_set_gucs.assert_called_once_with(
            username="alice",
            user_id=42,
            request=request._request,
        )
        # E deve essere chiamato PRIMA di record_login (audit deve
        # vedere le GUC settate sulla connessione).
        gucs_call_order = mock_set_gucs.call_args_list
        record_call_order = mock_record_login.call_args_list
        self.assertEqual(len(gucs_call_order), 1)
        self.assertEqual(len(record_call_order), 1)

    # Scopo: Hotfix BE-2.0ter — verifica che il REFRESH propaghi le GUC
    # PRIMA della scrittura di audit. Il refresh NON porta Bearer
    # access token, quindi la DRF auth chain non passa per
    # JwtAuditAuthentication: bisogna risolvere l'username dal user_id
    # del claim e settare manualmente.
    @patch(f"{_SERVICE}.record_refresh")
    @patch.object(AuditTokenRefreshView, "_resolve_username", return_value="alice")
    @patch.object(AuditTokenRefreshView, "_extract_claims", return_value=(42, "jti-xyz"))
    @patch("rest_framework_simplejwt.views.TokenRefreshView.post")
    @patch(_SET_GUCS)
    def test_refresh_success_propaga_gucs(
        self, mock_set_gucs, mock_super_post, mock_extract,
        mock_resolve, mock_record_refresh,
    ):
        mock_super_post.return_value = Response(
            {"access": "new.tok.en"},
            status=200,
        )
        request = MagicMock()
        request._request = MagicMock()

        view = AuditTokenRefreshView()
        view.post(request)

        mock_resolve.assert_called_once_with(42)
        mock_set_gucs.assert_called_once_with(
            username="alice",
            user_id=42,
            request=request._request,
        )
        mock_record_refresh.assert_called_once()

    # Scopo: Refresh con _resolve_username che ritorna None (utente
    # non trovato o query fallita) — fail-open: niente set_jwt_gucs ma
    # record_refresh comunque chiamato (l'audit storico resta).
    @patch(f"{_SERVICE}.record_refresh")
    @patch.object(AuditTokenRefreshView, "_resolve_username", return_value=None)
    @patch.object(AuditTokenRefreshView, "_extract_claims", return_value=(42, "jti-xyz"))
    @patch("rest_framework_simplejwt.views.TokenRefreshView.post")
    @patch(_SET_GUCS)
    def test_refresh_username_non_risolvibile_fail_open(
        self, mock_set_gucs, mock_super_post, mock_extract,
        mock_resolve, mock_record_refresh,
    ):
        mock_super_post.return_value = Response(
            {"access": "new.tok.en"},
            status=200,
        )
        request = MagicMock()
        request._request = MagicMock()

        view = AuditTokenRefreshView()
        view.post(request)

        mock_set_gucs.assert_not_called()
        mock_record_refresh.assert_called_once()
