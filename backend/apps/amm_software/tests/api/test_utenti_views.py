# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API utenti modulo Amm. Software.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_utenti_success — GET lista con risultati
 2) test_list_utenti_empty — GET lista vuota
 3) test_list_utenti_with_filters — GET lista con filtri
 4) test_list_utenti_permission_denied — OPERATIVO non puo' accedere
 5) test_detail_utente_success — GET dettaglio utente
 6) test_detail_utente_not_found — GET utente inesistente -> errore
 7) test_detail_utente_anonymous — Utente non autenticato -> 403
 8) test_patch_utente_success — PATCH modifica campi
 9) test_patch_utente_invalidates_cache — PATCH invalida cache permessi
10) test_patch_utente_not_found — PATCH utente inesistente -> errore
11) test_patch_ruolo_sistema — PATCH cambio ruolo
12) test_patch_attivo — PATCH cambio attivo
13) test_disabilita_success — POST disabilita utente
14) test_disabilita_invalidates_cache — POST disabilita invalida cache
15) test_disabilita_not_found — POST disabilita utente inesistente -> errore
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import (
    UtentiDetailView,
    UtentiDisabilitaView,
    UtentiListView,
)


SAMPLE_UTENTE = {
    "auth_user_id": 1,
    "username": "operatore1",
    "email": "op1@test.it",
    "first_name": "Mario",
    "last_name": "Rossi",
    "ruolo_sistema": "OPERATIVO",
    "is_active": True,
    "unita_organizzativa_id": 10,
    "unita_organizzativa_nome": "Reparto A",
    "risorsa_umana_id": 100,
    "attivo": True,
    "valido_al": None,
    "data_insert": "2026-01-01",
}

SAMPLE_DETAIL = {
    **SAMPLE_UTENTE,
    "override_aree_count": 2,
    "override_azioni_count": 1,
    "emittenti_count": 0,
}


def _admin_request(method: str = "GET", data: dict | None = None, query_params: dict | None = None) -> MagicMock:
    """Scopo: Crea un mock request autenticato come ADMIN."""
    request = MagicMock()
    request.method = method
    request.path = "/api/v1/amm-software/utenti/"
    user = MagicMock()
    user.id = 99
    user.is_authenticated = True
    user.is_superuser = True  # Bypass permission per focus su logica view
    request.user = user
    request.query_params = query_params or {}
    request.data = data or {}
    return request


def _operativo_request() -> MagicMock:
    """Scopo: Crea un mock request autenticato come OPERATIVO (non admin)."""
    request = MagicMock()
    request.method = "GET"
    request.path = "/api/v1/amm-software/utenti/"
    user = MagicMock()
    user.id = 50
    user.is_authenticated = True
    user.is_superuser = False
    request.user = user
    request.query_params = {}
    # Simula assenza cache per-request
    del request._zeroerp_perms_cache
    del request._zeroerp_perms_cache_loaded_from_redis
    return request


class TestUtentiListView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_list_utenti_success(self, MockRepo: MagicMock) -> None:
        """Scopo: GET lista con risultati ritorna count e results."""
        repo_instance = MockRepo.return_value
        repo_instance.list_utenti.return_value = ([SAMPLE_UTENTE], 1)

        view = UtentiListView()
        view.check_permissions = MagicMock()  # Bypass permission (tested separately)
        response = view.get(_admin_request())

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"]["count"], 1)
        self.assertEqual(len(body["data"]["results"]), 1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_list_utenti_empty(self, MockRepo: MagicMock) -> None:
        """Scopo: GET lista vuota ritorna count=0 e results=[]."""
        repo_instance = MockRepo.return_value
        repo_instance.list_utenti.return_value = ([], 0)

        view = UtentiListView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request())

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"]["count"], 0)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_list_utenti_with_filters(self, MockRepo: MagicMock) -> None:
        """Scopo: I filtri query string vengono passati al repository."""
        repo_instance = MockRepo.return_value
        repo_instance.list_utenti.return_value = ([], 0)

        qp = {"search": "mario", "ruolo_sistema": "ADMIN", "is_active": "true", "limit": "10"}
        view = UtentiListView()
        view.check_permissions = MagicMock()
        view.get(_admin_request(query_params=qp))

        call_kwargs = repo_instance.list_utenti.call_args.kwargs
        self.assertEqual(call_kwargs["search"], "mario")
        self.assertEqual(call_kwargs["ruolo_sistema"], "ADMIN")
        self.assertTrue(call_kwargs["is_active"])
        self.assertEqual(call_kwargs["limit"], 10)

    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.api.permissions.PermissionResolver.get_ruolo_sistema", return_value="OPERATIVO")
    def test_list_utenti_permission_denied(
        self, mock_ruolo: MagicMock, _mock_load: MagicMock, _mock_save: MagicMock,
    ) -> None:
        """Scopo: Un utente OPERATIVO non puo' accedere alla lista utenti."""
        from apps.core.api.permissions import IsAdminZeroERP
        perm = IsAdminZeroERP()
        request = _operativo_request()
        view = UtentiListView()
        result = perm.has_permission(request, view)
        self.assertFalse(result)


class TestUtentiDetailView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_detail_utente_success(self, MockRepo: MagicMock) -> None:
        """Scopo: GET dettaglio ritorna i dati completi dell'utente."""
        repo_instance = MockRepo.return_value
        repo_instance.get_utente_detail.return_value = SAMPLE_DETAIL

        view = UtentiDetailView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request(), auth_user_id=1)

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"]["username"], "operatore1")
        self.assertEqual(body["data"]["override_aree_count"], 2)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_detail_utente_not_found(self, MockRepo: MagicMock) -> None:
        """Scopo: GET dettaglio per utente inesistente solleva errore."""
        repo_instance = MockRepo.return_value
        repo_instance.get_utente_detail.return_value = None

        view = UtentiDetailView()
        view.check_permissions = MagicMock()

        from apps.core.services.service_errors import ServiceError
        with self.assertRaises(ServiceError):
            view.get(_admin_request(), auth_user_id=999)

    def test_detail_utente_anonymous(self) -> None:
        """Scopo: Un utente non autenticato non puo' accedere al dettaglio."""
        from apps.core.api.permissions import IsAdminZeroERP
        perm = IsAdminZeroERP()
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = False
        self.assertFalse(perm.has_permission(request, UtentiDetailView()))


class TestUtentiPatchView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_utente_success(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: PATCH modifica i campi e ritorna il dettaglio aggiornato."""
        repo_instance = MockRepo.return_value
        repo_instance.get_utente_detail.return_value = SAMPLE_DETAIL

        view = UtentiDetailView()
        view.check_permissions = MagicMock()
        data = {"email": "nuovo@test.it"}
        response = view.patch(_admin_request(method="PATCH", data=data), auth_user_id=1)

        self.assertEqual(response.status_code, 200)
        repo_instance.update_utente.assert_called_once()

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_utente_invalidates_cache(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: PATCH invalida la cache permessi dell'utente modificato."""
        repo_instance = MockRepo.return_value
        repo_instance.get_utente_detail.return_value = SAMPLE_DETAIL

        view = UtentiDetailView()
        view.check_permissions = MagicMock()
        view.patch(_admin_request(method="PATCH", data={"ruolo_sistema": "ADMIN"}), auth_user_id=1)

        mock_invalidate.assert_called_once_with(1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_utente_not_found(self, MockRepo: MagicMock) -> None:
        """Scopo: PATCH su utente inesistente solleva errore."""
        repo_instance = MockRepo.return_value
        repo_instance.get_utente_detail.return_value = None

        view = UtentiDetailView()
        view.check_permissions = MagicMock()

        from apps.core.services.service_errors import ServiceError
        with self.assertRaises(ServiceError):
            view.patch(_admin_request(method="PATCH", data={"email": "x@y.it"}), auth_user_id=999)

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_ruolo_sistema(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: PATCH cambio ruolo_sistema passa il valore corretto al repository."""
        repo_instance = MockRepo.return_value
        repo_instance.get_utente_detail.return_value = SAMPLE_DETAIL

        view = UtentiDetailView()
        view.check_permissions = MagicMock()
        view.patch(_admin_request(method="PATCH", data={"ruolo_sistema": "ADMIN"}), auth_user_id=1)

        call_kwargs = repo_instance.update_utente.call_args.kwargs
        self.assertEqual(call_kwargs["ruolo_sistema"], "ADMIN")

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_attivo(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: PATCH cambio attivo passa il valore corretto al repository."""
        repo_instance = MockRepo.return_value
        repo_instance.get_utente_detail.return_value = SAMPLE_DETAIL

        view = UtentiDetailView()
        view.check_permissions = MagicMock()
        view.patch(_admin_request(method="PATCH", data={"attivo": False}), auth_user_id=1)

        call_kwargs = repo_instance.update_utente.call_args.kwargs
        self.assertFalse(call_kwargs["attivo"])


class TestUtentiDisabilitaView(TestCase):

    @patch("apps.amm_software.services.amm_software_service._blacklist_user_tokens")
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_disabilita_success(self, MockRepo: MagicMock, mock_invalidate: MagicMock, mock_blacklist: MagicMock) -> None:
        """Scopo: POST disabilita imposta stato e ritorna dettaglio aggiornato."""
        repo_instance = MockRepo.return_value
        disabled = {**SAMPLE_DETAIL, "ruolo_sistema": "DISABILITATO", "attivo": False, "is_active": False}
        repo_instance.get_utente_detail.side_effect = [SAMPLE_DETAIL, disabled]

        view = UtentiDisabilitaView()
        view.check_permissions = MagicMock()
        response = view.post(_admin_request(method="POST"), auth_user_id=1)

        self.assertEqual(response.status_code, 200)
        repo_instance.disabilita_utente.assert_called_once_with(1)

    @patch("apps.amm_software.services.amm_software_service._blacklist_user_tokens")
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_disabilita_invalidates_cache(self, MockRepo: MagicMock, mock_invalidate: MagicMock, mock_blacklist: MagicMock) -> None:
        """Scopo: POST disabilita invalida cache permessi."""
        repo_instance = MockRepo.return_value
        repo_instance.get_utente_detail.return_value = SAMPLE_DETAIL

        view = UtentiDisabilitaView()
        view.check_permissions = MagicMock()
        view.post(_admin_request(method="POST"), auth_user_id=1)

        mock_invalidate.assert_called_once_with(1)
        mock_blacklist.assert_called_once_with(1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_disabilita_not_found(self, MockRepo: MagicMock) -> None:
        """Scopo: POST disabilita su utente inesistente solleva errore."""
        repo_instance = MockRepo.return_value
        repo_instance.get_utente_detail.return_value = None

        view = UtentiDisabilitaView()
        view.check_permissions = MagicMock()

        from apps.core.services.service_errors import ServiceError
        with self.assertRaises(ServiceError):
            view.post(_admin_request(method="POST"), auth_user_id=999)
