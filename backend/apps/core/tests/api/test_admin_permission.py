# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari IsAdminZeroERP — permission class per endpoint admin.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_admin_user_allowed — ruolo ADMIN -> accesso consentito
 2) test_operativo_denied — ruolo OPERATIVO -> 403
 3) test_disabilitato_denied — ruolo DISABILITATO -> 403
 4) test_no_bridge_denied — utente senza bridge (ruolo None) -> 403
 5) test_superuser_bypass — superuser Django -> accesso consentito senza check ruolo
 6) test_anonymous_denied — utente non autenticato -> 403
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.api.permissions import IsAdminZeroERP


def _mock_request(
    user_id: int = 1,
    authenticated: bool = True,
    is_superuser: bool = False,
) -> MagicMock:
    """Scopo: Crea un mock DRF request per i test IsAdminZeroERP."""
    request = MagicMock()
    request.method = "GET"
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = authenticated
    user.is_superuser = is_superuser
    request.user = user
    # Simula assenza cache per-request
    del request._zeroerp_perms_cache
    del request._zeroerp_perms_cache_loaded_from_redis
    return request


def _mock_view() -> MagicMock:
    """Scopo: Crea un mock view minimale."""
    return MagicMock()


class TestIsAdminZeroERP(TestCase):

    def setUp(self) -> None:
        self.perm = IsAdminZeroERP()

    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.api.permissions.PermissionResolver.get_ruolo_sistema", return_value="ADMIN")
    def test_admin_user_allowed(self, mock_ruolo: MagicMock, _mock_load: MagicMock, _mock_save: MagicMock) -> None:
        """Scopo: Un utente con ruolo ADMIN deve avere accesso."""
        request = _mock_request()
        result = self.perm.has_permission(request, _mock_view())
        self.assertTrue(result)
        mock_ruolo.assert_called_once()

    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.api.permissions.PermissionResolver.get_ruolo_sistema", return_value="OPERATIVO")
    def test_operativo_denied(self, mock_ruolo: MagicMock, _mock_load: MagicMock, _mock_save: MagicMock) -> None:
        """Scopo: Un utente OPERATIVO non deve avere accesso agli endpoint admin."""
        request = _mock_request()
        result = self.perm.has_permission(request, _mock_view())
        self.assertFalse(result)
        self.assertIn("amministratori", self.perm.message)

    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.api.permissions.PermissionResolver.get_ruolo_sistema", return_value="DISABILITATO")
    def test_disabilitato_denied(self, mock_ruolo: MagicMock, _mock_load: MagicMock, _mock_save: MagicMock) -> None:
        """Scopo: Un utente DISABILITATO non deve avere accesso."""
        request = _mock_request()
        result = self.perm.has_permission(request, _mock_view())
        self.assertFalse(result)

    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.api.permissions.PermissionResolver.get_ruolo_sistema", return_value=None)
    def test_no_bridge_denied(self, mock_ruolo: MagicMock, _mock_load: MagicMock, _mock_save: MagicMock) -> None:
        """Scopo: Un utente senza bridge risorse_umane_auth_user (ruolo None) non ha accesso."""
        request = _mock_request()
        result = self.perm.has_permission(request, _mock_view())
        self.assertFalse(result)

    def test_superuser_bypass(self) -> None:
        """Scopo: Un superuser Django bypassa il check ruolo_sistema."""
        request = _mock_request(is_superuser=True)
        result = self.perm.has_permission(request, _mock_view())
        self.assertTrue(result)

    def test_anonymous_denied(self) -> None:
        """Scopo: Un utente non autenticato non ha accesso."""
        request = _mock_request(authenticated=False)
        request.user.is_authenticated = False
        result = self.perm.has_permission(request, _mock_view())
        self.assertFalse(result)
