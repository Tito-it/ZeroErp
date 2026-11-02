# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari ZeroERPPermission — permission class DRF.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_anonymous_user_denied
 2) test_superuser_allowed
 3) test_admin_ruolo_allowed
 4) test_operativo_area_tutto_get_allowed
 5) test_operativo_area_lettura_post_denied
 6) test_operativo_area_lettura_get_allowed
 7) test_operativo_area_bloccato_denied
 8) test_action_permission_checked
 9) test_post_permission_on_apiview
10) test_no_area_without_skip_denied (fail-closed)
11) test_no_area_with_skip_allowed (skip_area_check=True)
12) test_no_area_denied_logs_warning
13) test_bloccato_senza_profilo_message
14) test_bloccato_con_profilo_message
15) test_azione_negata_message
16) test_log_warning_azione_negata
17) test_log_warning_livello_insufficiente
18) test_model_permission_uses_livello_oggetto
19) test_model_permission_fallback_area
20) test_no_model_permission_uses_area
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
    # Rimuovi gli attributi *_permission e model_permission per default
    del view.list_permission
    del view.retrieve_permission
    del view.create_permission
    del view.get_permission
    del view.post_permission
    del view.put_permission
    del view.patch_permission
    del view.delete_permission
    del view.model_permission
    # L'oggetto dalla richiesta (D-P7, 2026-09-25): su un MagicMock il metodo
    # esisterebbe e la catena lo userebbe al posto dell'area.
    del view.oggetto_permesso_da_richiesta
    # Idem per `<chiave>_accesso` (dal 2026-09-25): su un MagicMock
    # l'attributo esisterebbe, e la catena lo leggerebbe come una
    # dichiarazione non valida. Le chiavi si leggono dalla catena, non si
    # ricopiano: un'action o un metodo nuovo resterebbero fuori in silenzio.
    for chiave in (
        *ZeroERPPermission.ACTION_REQUIRES,
        *(metodo.lower() for metodo in ZeroERPPermission.METHOD_REQUIRES),
    ):
        delattr(view, f"{chiave}_accesso")
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

    # Scopo: Utente con ruolo_sistema ADMIN deve essere ammesso.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_admin_ruolo_allowed(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = True
        request = _mock_request()
        view = _mock_view(area="vendite")
        self.assertTrue(self.perm.has_permission(request, view))

    # Scopo: OPERATIVO con TUTTO su area puo' fare GET.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_operativo_area_tutto_get_allowed(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_livello_area.return_value = "TUTTO"
        mock_resolver.get_area_schema_db.return_value = "vendite"

        request = _mock_request(method="GET")
        view = _mock_view(area="vendite")
        self.assertTrue(self.perm.has_permission(request, view))

    # Scopo: OPERATIVO con LETTURA su area non puo' fare POST.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_operativo_area_lettura_post_denied(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_livello_area.return_value = "LETTURA"
        mock_resolver.get_area_schema_db.return_value = "vendite"

        request = _mock_request(method="POST")
        view = _mock_view(area="vendite")
        self.assertFalse(self.perm.has_permission(request, view))

    # Scopo: OPERATIVO con LETTURA su area puo' fare GET.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_operativo_area_lettura_get_allowed(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_livello_area.return_value = "LETTURA"
        mock_resolver.get_area_schema_db.return_value = "vendite"

        request = _mock_request(method="GET")
        view = _mock_view(area="vendite")
        self.assertTrue(self.perm.has_permission(request, view))

    # Scopo: OPERATIVO con BLOCCATO su area viene negato sempre.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_operativo_area_bloccato_denied(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_livello_area.return_value = "BLOCCATO"
        mock_resolver.get_area_schema_db.return_value = "vendite"

        request = _mock_request(method="GET")
        view = _mock_view(area="vendite")
        self.assertFalse(self.perm.has_permission(request, view))

    # Scopo: ViewSet con action e *_permission usa check_azione.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_action_permission_checked(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.check_azione.return_value = True

        request = _mock_request(method="POST")
        view = _mock_view(action="run_pipeline", area="vendite")
        view.run_pipeline_permission = "genera_fatture_lotti"
        self.assertTrue(self.perm.has_permission(request, view))
        mock_resolver.check_azione.assert_called_once()

    # Scopo: APIView con post_permission usa check_azione.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_post_permission_on_apiview(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.check_azione.return_value = False

        request = _mock_request(method="POST")
        view = _mock_view(area="vendite")
        view.post_permission = "genera_fatture_lotti"
        self.assertFalse(self.perm.has_permission(request, view))

    # Scopo: View senza area_funzionale e senza skip_area_check viene negata (fail-closed).
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_no_area_without_skip_denied(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False

        request = _mock_request(method="GET")
        request.path = "/api/v1/test/"
        view = _mock_view()
        view.area_funzionale = None
        del view.skip_area_check
        self.assertFalse(self.perm.has_permission(request, view))

    # Scopo: View senza area_funzionale ma con skip_area_check=True e' ammessa.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_no_area_with_skip_allowed(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False

        request = _mock_request(method="GET")
        view = _mock_view()
        view.area_funzionale = None
        view.skip_area_check = True
        self.assertTrue(self.perm.has_permission(request, view))

    # Scopo: Fail-closed senza skip logga warning di sicurezza.
    @patch("apps.core.api.permissions.logger")
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_no_area_denied_logs_warning(self, mock_resolver, mock_logger):
        mock_resolver.is_super_admin.return_value = False

        request = _mock_request(method="GET")
        request.path = "/api/v1/test/"
        view = _mock_view()
        view.area_funzionale = None
        del view.skip_area_check
        self.perm.has_permission(request, view)
        mock_logger.warning.assert_called_once()
        log_msg = mock_logger.warning.call_args[0][0]
        self.assertIn("area_non_definita", log_msg)

    # Scopo: BLOCCATO senza profilo reparto produce messaggio specifico.
    # Si applica solo agli OPERATORI interni (il messaggio e' legato al
    # reparto; utenti portale/shop ricevono il messaggio generico).
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_bloccato_senza_profilo_message(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_ruolo_applicativo.return_value = "OPERATORE"
        mock_resolver.get_livello_area.return_value = "BLOCCATO"
        mock_resolver.get_area_schema_db.return_value = "vendite"
        mock_resolver.has_profilo_applicabile_per_area.return_value = False

        request = _mock_request(method="GET")
        view = _mock_view(area="vendite")
        self.perm.has_permission(request, view)
        self.assertIn("profilo", self.perm.message.lower())

    # Scopo: BLOCCATO con profilo reparto produce messaggio generico.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_bloccato_con_profilo_message(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_livello_area.return_value = "BLOCCATO"
        mock_resolver.get_area_schema_db.return_value = "vendite"
        mock_resolver.has_profilo_applicabile_per_area.return_value = True

        request = _mock_request(method="GET")
        view = _mock_view(area="vendite")
        self.perm.has_permission(request, view)
        self.assertIn("permessi", self.perm.message.lower())
        self.assertNotIn("profilo", self.perm.message.lower())

    # Scopo: Azione negata produce messaggio generico permessi.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_azione_negata_message(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.check_azione.return_value = False

        request = _mock_request(method="POST")
        view = _mock_view(area="vendite")
        view.post_permission = "genera_fatture_lotti"
        self.perm.has_permission(request, view)
        self.assertIn("permessi", self.perm.message.lower())

    # Scopo: Azione negata logga warning di sicurezza.
    @patch("apps.core.api.permissions.logger")
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_log_warning_azione_negata(self, mock_resolver, mock_logger):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.check_azione.return_value = False
        request = _mock_request(method="POST")
        request.path = "/api/v1/vendite/fatturazione/numera/"
        view = _mock_view(area="vendite")
        view.post_permission = "numera_fatture_lotti"
        self.perm.has_permission(request, view)
        mock_logger.warning.assert_called_once()
        log_msg = mock_logger.warning.call_args[0][0]
        self.assertIn("azione_negata", log_msg)

    # Scopo: Livello insufficiente logga warning di sicurezza.
    @patch("apps.core.api.permissions.logger")
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_log_warning_livello_insufficiente(self, mock_resolver, mock_logger):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_livello_area.return_value = "LETTURA"
        mock_resolver.get_area_schema_db.return_value = "vendite"
        request = _mock_request(method="POST")
        request.path = "/api/v1/vendite/lotti/"
        view = _mock_view(area="vendite")
        self.perm.has_permission(request, view)
        mock_logger.warning.assert_called_once()
        log_msg = mock_logger.warning.call_args[0][0]
        self.assertIn("livello_insufficiente", log_msg)

    # --- model_permission v2 ---

    # Scopo: View con model_permission usa get_livello_oggetto con override.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_model_permission_uses_livello_oggetto(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_livello_oggetto.return_value = "LETTURA"

        request = _mock_request(method="POST")
        view = _mock_view(area="anagrafiche")
        view.model_permission = ("anagrafiche", "conto_bancario")
        self.assertFalse(self.perm.has_permission(request, view))
        mock_resolver.get_livello_oggetto.assert_called_once_with(
            request.user, "anagrafiche", "conto_bancario", "anagrafiche", cache=mock_resolver.get_livello_oggetto.call_args.kwargs.get("cache"),
        )

    # Scopo: View con model_permission senza override fa fallback al livello area
    #        (fn_resolve_livello_oggetto ritorna il livello area se nessun override).
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_model_permission_fallback_area(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_livello_oggetto.return_value = "TUTTO"

        request = _mock_request(method="POST")
        view = _mock_view(area="anagrafiche")
        view.model_permission = ("anagrafiche", "conto_bancario")
        self.assertTrue(self.perm.has_permission(request, view))
        # get_livello_area NON deve essere chiamato (scavalcato da get_livello_oggetto)
        mock_resolver.get_livello_area.assert_not_called()

    # Scopo: View senza model_permission continua a usare get_livello_area.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_no_model_permission_uses_area(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_livello_area.return_value = "TUTTO"

        request = _mock_request(method="GET")
        view = _mock_view(area="anagrafiche")
        self.assertTrue(self.perm.has_permission(request, view))
        mock_resolver.get_livello_area.assert_called_once()
        mock_resolver.get_livello_oggetto.assert_not_called()
