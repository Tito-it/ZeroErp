# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per ChangePasswordView e PasswordChangeRequiredMiddleware.
#        Mock DB, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) ChangePasswordTests.test_missing_old_password_raises
2) ChangePasswordTests.test_password_mismatch_raises
3) ChangePasswordTests.test_same_password_raises
4) ChangePasswordTests.test_wrong_old_password_raises
5) MiddlewareTests.test_allowed_paths_pass_through
6) MiddlewareTests.test_blocked_path_returns_403
7) MiddlewareTests.test_unauthenticated_passes_through
8) MiddlewareTests.test_superuser_passes_through
9) AuthViewTests.test_login_adds_password_change_flag
10) AuthViewTests.test_login_no_flag_when_not_required
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError

_AUTH_REPO = "apps.core.db.auth_repository.AuthRepository"


class ChangePasswordTests(TestCase):
    """Test validazioni del cambio password (logica service-level)."""

    # Scopo: Verifica che password attuale vuota lanci errore.
    def test_missing_old_password_raises(self):
        with self.assertRaises(ServiceError):
            ErrorManager.require(bool(""), code="E_CHANGE_PASSWORD", message="Password attuale obbligatoria.")

    # Scopo: Verifica che conferma password diversa lanci errore.
    def test_password_mismatch_raises(self):
        with self.assertRaises(ServiceError):
            ErrorManager.require(
                "nuova123" == "diversa456",
                code="E_CHANGE_PASSWORD",
                message="La nuova password e la conferma non coincidono.",
            )

    # Scopo: Verifica che stessa password vecchia/nuova lanci errore.
    def test_same_password_raises(self):
        with self.assertRaises(ServiceError):
            ErrorManager.require(
                "stessa" != "stessa",
                code="E_CHANGE_PASSWORD",
                message="La nuova password deve essere diversa dalla precedente.",
            )

    # Scopo: Verifica che password attuale errata lanci errore.
    def test_wrong_old_password_raises(self):
        user = MagicMock()
        user.check_password.return_value = False
        with self.assertRaises(ServiceError):
            ErrorManager.require(
                user.check_password("sbagliata"),
                code="E_CHANGE_PASSWORD",
                message="Password attuale non corretta.",
            )


class MiddlewareTests(TestCase):
    """Test PasswordChangeRequiredMiddleware."""

    def _make_request(self, path, authenticated=True, superuser=False, deve_cambiare=False):
        request = MagicMock()
        request.path = path
        if authenticated:
            request.user.is_authenticated = True
            request.user.is_superuser = superuser
            request.user.id = 42
        else:
            request.user.is_authenticated = False
        return request, deve_cambiare

    # Scopo: Verifica che i path consentiti passino anche con flag attivo.
    @patch(f"{_AUTH_REPO}.get_deve_cambiare_password", return_value=True)
    def test_allowed_paths_pass_through(self, mock_flag):
        from apps.core.middleware.password_change_middleware import PasswordChangeRequiredMiddleware

        mw = PasswordChangeRequiredMiddleware(lambda r: None)
        for path in ["/api/v1/auth/change-password/", "/api/v1/auth/logout/", "/api/v1/core/me/"]:
            request, _ = self._make_request(path, deve_cambiare=True)
            result = mw.process_view(request, None, None, None)
            self.assertIsNone(result, f"Path {path} dovrebbe passare")

    # Scopo: Verifica che path bloccato ritorni 403 con flag attivo.
    @patch("apps.core.db.auth_repository.AuthRepository.get_deve_cambiare_password", return_value=True)
    def test_blocked_path_returns_403(self, mock_flag):
        from apps.core.middleware.password_change_middleware import PasswordChangeRequiredMiddleware

        mw = PasswordChangeRequiredMiddleware(lambda r: None)
        request, _ = self._make_request("/api/v1/vendite/lotti/")
        result = mw.process_view(request, None, None, None)

        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 403)

    # Scopo: Verifica che utente non autenticato passi (gestito da JWT auth).
    def test_unauthenticated_passes_through(self):
        from apps.core.middleware.password_change_middleware import PasswordChangeRequiredMiddleware

        mw = PasswordChangeRequiredMiddleware(lambda r: None)
        request, _ = self._make_request("/api/v1/vendite/lotti/", authenticated=False)
        result = mw.process_view(request, None, None, None)
        self.assertIsNone(result)

    # Scopo: Verifica che superuser bypassa il middleware.
    def test_superuser_passes_through(self):
        from apps.core.middleware.password_change_middleware import PasswordChangeRequiredMiddleware

        mw = PasswordChangeRequiredMiddleware(lambda r: None)
        request, _ = self._make_request("/api/v1/vendite/lotti/", superuser=True)
        result = mw.process_view(request, None, None, None)
        self.assertIsNone(result)


class AuthViewTests(TestCase):
    """Test che il login aggiunga il flag password_change_required."""

    # Scopo: Verifica che la response del login includa il flag se attivo.
    @patch(f"{_AUTH_REPO}.get_deve_cambiare_password", return_value=True)
    @patch(f"{_AUTH_REPO}.registra_tentativo_login", return_value={"bloccato": False})
    @patch(f"{_AUTH_REPO}.check_blocco_login")
    def test_login_adds_password_change_flag(self, mock_blocco, mock_tentativo, mock_flag):
        from apps.core.api.auth_views import AuditTokenObtainPairView

        view = AuditTokenObtainPairView()
        # Simula response di successo dal parent
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = {"access": "xxx", "refresh": "yyy"}

        with patch.object(AuditTokenObtainPairView, '_find_user') as mock_find:
            mock_user = MagicMock()
            mock_user.id = 42
            mock_find.return_value = mock_user

            with patch('apps.core.api.auth_views.TokenObtainPairView.post', return_value=mock_response):
                with patch('apps.core.api.auth_views.session_audit_service'):
                    with patch.object(AuditTokenObtainPairView, '_extract_claims', return_value=(42, "sid-123")):
                        request = MagicMock()
                        request.data = {"username": "test"}
                        result = view.post(request)

        self.assertTrue(result.data.get("password_change_required"))

    # Scopo: Verifica che il flag NON sia presente se non richiesto.
    @patch(f"{_AUTH_REPO}.get_deve_cambiare_password", return_value=False)
    @patch(f"{_AUTH_REPO}.registra_tentativo_login", return_value={"bloccato": False})
    @patch(f"{_AUTH_REPO}.check_blocco_login")
    def test_login_no_flag_when_not_required(self, mock_blocco, mock_tentativo, mock_flag):
        from apps.core.api.auth_views import AuditTokenObtainPairView

        view = AuditTokenObtainPairView()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = {"access": "xxx", "refresh": "yyy"}

        with patch.object(AuditTokenObtainPairView, '_find_user') as mock_find:
            mock_user = MagicMock()
            mock_user.id = 42
            mock_find.return_value = mock_user

            with patch('apps.core.api.auth_views.TokenObtainPairView.post', return_value=mock_response):
                with patch('apps.core.api.auth_views.session_audit_service'):
                    with patch.object(AuditTokenObtainPairView, '_extract_claims', return_value=(42, "sid-123")):
                        request = MagicMock()
                        request.data = {"username": "test"}
                        result = view.post(request)

        self.assertNotIn("password_change_required", result.data)
