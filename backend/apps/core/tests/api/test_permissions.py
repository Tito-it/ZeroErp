# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari ZeroERPPermission — permission class DRF.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_anonymous_user_denied
 2) test_superuser_allowed
 3) test_disabilitato_denied
 4) test_admin_ruolo_allowed
 5) test_operativo_area_tutto_get_allowed
 6) test_operativo_area_lettura_post_denied
 7) test_operativo_area_lettura_get_allowed
 8) test_operativo_area_bloccato_denied
 9) test_action_permission_checked
10) test_post_permission_on_apiview
11) test_no_area_without_skip_denied (fail-closed)
12) test_no_area_with_skip_allowed (skip_area_check=True)
13) test_no_area_denied_logs_warning
14) test_disabilitato_message
15) test_bloccato_senza_profilo_message
16) test_bloccato_con_profilo_message
17) test_azione_negata_message
18) test_log_warning_disabilitato
19) test_log_warning_azione_negata
20) test_log_warning_livello_insufficiente
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.api.permissions import ZeroERPPermission


def _mock_request(method: str = "GET", user_id: int = 1, authenticated: bool = True, is_superuser: bool = False) -> MagicMock:
    """Scopo: Crea un mock DRF request."""
    request = MagicMock()
    request.method = method
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = authenticated
    user.is_superuser = is_superuser
    request.user = user
    return request


def _mock_view(action: str | None = None, area: str | None = None, queryset: object | None = None) -> MagicMock:
    """Scopo: Crea un mock DRF view."""
    view = MagicMock()
    view.action = action
    view.area_funzionale = area
    view.queryset = queryset
    # Rimuovi gli attributi *_permission per default
    del view.list_permission
    del view.retrieve_permission
    del view.create_permission
    del view.get_permission
    del view.post_permission
    del view.put_permission
    del view.patch_permission
    del view.delete_permission
    return view


class ZeroERPPermissionTests(TestCase):
    """Test per la permission class DRF."""

    def setUp(self) -> None:
        self.perm = ZeroERPPermission()

    # Scopo: Utente anonimo deve essere negato.
    def test_anonymous_user_denied(self):
        request = _mock_request(authenticated=False)
        request.user.is_authenticated = False
        view = _mock_view(area="vendite")
        self.assertFalse(self.perm.has_permission(request, view))

    # Scopo: Django superuser deve essere sempre ammesso.
    def test_superuser_allowed(self):
        request = _mock_request(is_superuser=True)
        view = _mock_view(area="vendite")
        self.assertTrue(self.perm.has_permission(request, view))

    # Scopo: Utente DISABILITATO deve essere negato.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_disabilitato_denied(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "DISABILITATO"
        request = _mock_request()
        view = _mock_view(area="vendite")
        self.assertFalse(self.perm.has_permission(request, view))

    # Scopo: Utente con ruolo_sistema ADMIN deve essere ammesso.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_admin_ruolo_allowed(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "ADMIN"
        request = _mock_request()
        view = _mock_view(area="vendite")
        self.assertTrue(self.perm.has_permission(request, view))

    # Scopo: OPERATIVO con TUTTO su area puo' fare GET.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_operativo_area_tutto_get_allowed(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.get_livello_area.return_value = "TUTTO"
        mock_resolver.get_area_schema_db.return_value = "vendite"

        request = _mock_request(method="GET")
        view = _mock_view(area="vendite")
        self.assertTrue(self.perm.has_permission(request, view))

    # Scopo: OPERATIVO con LETTURA su area non puo' fare POST.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_operativo_area_lettura_post_denied(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.get_livello_area.return_value = "LETTURA"
        mock_resolver.get_area_schema_db.return_value = "vendite"

        request = _mock_request(method="POST")
        view = _mock_view(area="vendite")
        self.assertFalse(self.perm.has_permission(request, view))

    # Scopo: OPERATIVO con LETTURA su area puo' fare GET.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_operativo_area_lettura_get_allowed(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.get_livello_area.return_value = "LETTURA"
        mock_resolver.get_area_schema_db.return_value = "vendite"

        request = _mock_request(method="GET")
        view = _mock_view(area="vendite")
        self.assertTrue(self.perm.has_permission(request, view))

    # Scopo: OPERATIVO con BLOCCATO su area viene negato sempre.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_operativo_area_bloccato_denied(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.get_livello_area.return_value = "BLOCCATO"
        mock_resolver.get_area_schema_db.return_value = "vendite"

        request = _mock_request(method="GET")
        view = _mock_view(area="vendite")
        self.assertFalse(self.perm.has_permission(request, view))

    # Scopo: ViewSet con action e *_permission usa check_azione.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_action_permission_checked(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.check_azione.return_value = True

        request = _mock_request(method="POST")
        view = _mock_view(action="run_pipeline", area="vendite")
        view.run_pipeline_permission = "genera_fatture_lotti"
        self.assertTrue(self.perm.has_permission(request, view))
        mock_resolver.check_azione.assert_called_once()

    # Scopo: APIView con post_permission usa check_azione.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_post_permission_on_apiview(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.check_azione.return_value = False

        request = _mock_request(method="POST")
        view = _mock_view(area="vendite")
        view.post_permission = "genera_fatture_lotti"
        self.assertFalse(self.perm.has_permission(request, view))

    # Scopo: View senza area_funzionale e senza skip_area_check viene negata (fail-closed).
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_no_area_without_skip_denied(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"

        request = _mock_request(method="GET")
        request.path = "/api/v1/test/"
        view = _mock_view()
        view.area_funzionale = None
        del view.skip_area_check
        self.assertFalse(self.perm.has_permission(request, view))

    # Scopo: View senza area_funzionale ma con skip_area_check=True e' ammessa.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_no_area_with_skip_allowed(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"

        request = _mock_request(method="GET")
        view = _mock_view()
        view.area_funzionale = None
        view.skip_area_check = True
        self.assertTrue(self.perm.has_permission(request, view))

    # Scopo: Fail-closed senza skip logga warning di sicurezza.
    @patch("apps.core.api.permissions.logger")
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_no_area_denied_logs_warning(self, mock_resolver, mock_logger):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"

        request = _mock_request(method="GET")
        request.path = "/api/v1/test/"
        view = _mock_view()
        view.area_funzionale = None
        del view.skip_area_check
        self.perm.has_permission(request, view)
        mock_logger.warning.assert_called_once()
        log_msg = mock_logger.warning.call_args[0][0]
        self.assertIn("area_non_definita", log_msg)

    # Scopo: DISABILITATO produce messaggio specifico.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_disabilitato_message(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "DISABILITATO"
        request = _mock_request()
        view = _mock_view(area="vendite")
        self.perm.has_permission(request, view)
        self.assertIn("disabilitato", self.perm.message.lower())

    # Scopo: BLOCCATO senza profilo reparto produce messaggio specifico.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_bloccato_senza_profilo_message(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.get_livello_area.return_value = "BLOCCATO"
        mock_resolver.get_area_schema_db.return_value = "vendite"
        mock_resolver.has_profilo_reparto_area.return_value = False

        request = _mock_request(method="GET")
        view = _mock_view(area="vendite")
        self.perm.has_permission(request, view)
        self.assertIn("profilo", self.perm.message.lower())

    # Scopo: BLOCCATO con profilo reparto produce messaggio generico.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_bloccato_con_profilo_message(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.get_livello_area.return_value = "BLOCCATO"
        mock_resolver.get_area_schema_db.return_value = "vendite"
        mock_resolver.has_profilo_reparto_area.return_value = True

        request = _mock_request(method="GET")
        view = _mock_view(area="vendite")
        self.perm.has_permission(request, view)
        self.assertIn("permessi", self.perm.message.lower())
        self.assertNotIn("profilo", self.perm.message.lower())

    # Scopo: Azione negata produce messaggio generico permessi.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_azione_negata_message(self, mock_resolver):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.check_azione.return_value = False

        request = _mock_request(method="POST")
        view = _mock_view(area="vendite")
        view.post_permission = "genera_fatture_lotti"
        self.perm.has_permission(request, view)
        self.assertIn("permessi", self.perm.message.lower())

    # Scopo: DISABILITATO logga warning di sicurezza.
    @patch("apps.core.api.permissions.logger")
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_log_warning_disabilitato(self, mock_resolver, mock_logger):
        mock_resolver.get_ruolo_sistema.return_value = "DISABILITATO"
        request = _mock_request()
        request.path = "/api/v1/vendite/lotti/"
        view = _mock_view(area="vendite")
        self.perm.has_permission(request, view)
        mock_logger.warning.assert_called_once()
        log_msg = mock_logger.warning.call_args[0][0]
        self.assertIn("DISABILITATO", log_msg)

    # Scopo: Azione negata logga warning di sicurezza.
    @patch("apps.core.api.permissions.logger")
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_log_warning_azione_negata(self, mock_resolver, mock_logger):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.check_azione.return_value = False
        request = _mock_request(method="POST")
        request.path = "/api/v1/vendite/lotti/123/reset-draft/"
        view = _mock_view(area="vendite")
        view.post_permission = "reset_lotto_draft"
        self.perm.has_permission(request, view)
        mock_logger.warning.assert_called_once()
        log_msg = mock_logger.warning.call_args[0][0]
        self.assertIn("azione_negata", log_msg)

    # Scopo: Livello insufficiente logga warning di sicurezza.
    @patch("apps.core.api.permissions.logger")
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_log_warning_livello_insufficiente(self, mock_resolver, mock_logger):
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"
        mock_resolver.get_livello_area.return_value = "LETTURA"
        mock_resolver.get_area_schema_db.return_value = "vendite"
        request = _mock_request(method="POST")
        request.path = "/api/v1/vendite/lotti/"
        view = _mock_view(area="vendite")
        self.perm.has_permission(request, view)
        mock_logger.warning.assert_called_once()
        log_msg = mock_logger.warning.call_args[0][0]
        self.assertIn("livello_insufficiente", log_msg)
