# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il flag del cambio password nella risposta del login.
#        Mock DB, compatibile CI senza database reale. Il blocco della
#        navigazione con la password da cambiare e' il cancello degli
#        obblighi: test_cancello_obblighi.py.
# Note: Le validazioni del cambio password stanno in
#       test_change_password_token_veste.py, sulla view vera. Fino al
#       2026-10-03 qui c'erano quattro test che chiamavano `ErrorManager.require`
#       a mano, senza la view: verdi anche con la verifica tolta. Ritirati.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) AuthViewTests.test_login_adds_password_change_flag
2) AuthViewTests.test_login_no_flag_when_not_required
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch


_AUTH_REPO = "apps.core.db.auth_repository.AuthRepository"


class AuthViewTests(TestCase):
    """Test che il login aggiunga il flag password_change_required."""

    # Il login chiede la provenienza (IP fidato): qui si fissa, la request e'
    # un MagicMock. La regola dell'IP e' provata in test_request_context.
    def setUp(self):
        patcher = patch("apps.core.services.request_context.get_client_ip", return_value="203.0.113.7")
        patcher.start()
        self.addCleanup(patcher.stop)
        # Il login legge il device del secondo fattore dopo la password:
        # nessun device. ⛔ `unittest.TestCase`: senza, andrebbe al DB vero.
        device = patch("apps.core.api.auth_views._secondo_fattore_repo")
        device.start().get_device.return_value = {"stato": "ASSENTE"}
        self.addCleanup(device.stop)

    # Scopo: Verifica che la response del login includa il flag se attivo.
    @patch(f"{_AUTH_REPO}.get_deve_cambiare_password", return_value=True)
    @patch(f"{_AUTH_REPO}.registra_tentativo_login", return_value={"bloccato": False})
    @patch(f"{_AUTH_REPO}.check_blocco_login")
    def test_login_adds_password_change_flag(self, mock_blocco, mock_tentativo, mock_flag):
        from apps.core.api.auth_views import AdminTokenView

        view = AdminTokenView()
        # Simula response di successo dal parent
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = {"access": "xxx", "refresh": "yyy"}

        with patch.object(AdminTokenView, '_find_user') as mock_find:
            mock_user = MagicMock()
            mock_user.id = 42
            mock_find.return_value = mock_user

            with patch('apps.core.api.auth_views.TokenObtainPairView.post', return_value=mock_response):
                with patch('apps.core.api.auth_views.session_audit_service'):
                    with patch.object(AdminTokenView, '_extract_claims', return_value=(42, "sid-123")):
                        request = MagicMock()
                        request.data = {"username": "test"}
                        result = view.post(request)

        self.assertTrue(result.data.get("password_change_required"))

    # Scopo: Verifica che il flag NON sia presente se non richiesto.
    @patch(f"{_AUTH_REPO}.get_deve_cambiare_password", return_value=False)
    @patch(f"{_AUTH_REPO}.registra_tentativo_login", return_value={"bloccato": False})
    @patch(f"{_AUTH_REPO}.check_blocco_login")
    def test_login_no_flag_when_not_required(self, mock_blocco, mock_tentativo, mock_flag):
        from apps.core.api.auth_views import AdminTokenView

        view = AdminTokenView()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = {"access": "xxx", "refresh": "yyy"}

        with patch.object(AdminTokenView, '_find_user') as mock_find:
            mock_user = MagicMock()
            mock_user.id = 42
            mock_find.return_value = mock_user

            with patch('apps.core.api.auth_views.TokenObtainPairView.post', return_value=mock_response):
                with patch('apps.core.api.auth_views.session_audit_service'):
                    with patch.object(AdminTokenView, '_extract_claims', return_value=(42, "sid-123")):
                        request = MagicMock()
                        request.data = {"username": "test"}
                        result = view.post(request)

        self.assertNotIn("password_change_required", result.data)
