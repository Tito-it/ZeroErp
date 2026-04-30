# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API operatori modulo Amm. Software.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_operatori_success — GET lista con risultati
 2) test_list_operatori_empty — GET lista vuota
 3) test_list_operatori_with_filters — GET lista con filtri
 4) test_list_operatori_permission_denied — OPERATIVO non puo' accedere
 5) test_detail_operatore_success — GET dettaglio operatore
 6) test_detail_operatore_not_found — GET operatore inesistente -> errore
 7) test_detail_operatore_anonymous — Utente non autenticato -> 403
 8) test_patch_operatore_success — PATCH modifica campi
 9) test_patch_operatore_invalidates_cache — PATCH invalida cache permessi
10) test_patch_operatore_not_found — PATCH operatore inesistente -> errore
11) test_patch_is_super_admin — PATCH cambio super-admin (contract Fase 1 multi-face)
12) test_patch_attivo — PATCH cambio attivo
13) test_disabilita_success — POST disabilita operatore
14) test_disabilita_invalidates_cache — POST disabilita invalida cache
15) test_disabilita_not_found — POST disabilita operatore inesistente -> errore
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import (
    OperatoriDetailView,
    OperatoriDisabilitaView,
    OperatoriListView,
)


SAMPLE_OPERATORE = {
    "auth_user_id": 1,
    "username": "operatore1",
    "email": "op1@test.it",
    "first_name": "Mario",
    "last_name": "Rossi",
    "is_super_admin": False,
    "ruolo_applicativo": "OPERATORE",
    "is_active": True,
    "unita_organizzativa_id": 10,
    "unita_organizzativa_nome": "Reparto A",
    "risorsa_umana_id": 100,
    "attivo": True,
    "valido_al": None,
    "data_insert": "2026-01-01",
}

SAMPLE_DETAIL = {
    **SAMPLE_OPERATORE,
    "override_aree_count": 2,
    "override_azioni_count": 1,
    "emittenti_count": 0,
}


def _admin_request(method: str = "GET", data: dict | None = None, query_params: dict | None = None) -> MagicMock:
    """Scopo: Crea un mock request autenticato come ADMIN."""
    request = MagicMock()
    request.method = method
    request.path = "/api/v1/amm-software/operatori/"
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
    request.path = "/api/v1/amm-software/operatori/"
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


class TestOperatoriListView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_list_operatori_success(self, MockRepo: MagicMock) -> None:
        """Scopo: GET lista con risultati ritorna count e results."""
        repo_instance = MockRepo.return_value
        repo_instance.list_operatori.return_value = ([SAMPLE_OPERATORE], 1)

        view = OperatoriListView()
        view.check_permissions = MagicMock()  # Bypass permission (tested separately)
        response = view.get(_admin_request())

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"]["count"], 1)
        self.assertEqual(len(body["data"]["results"]), 1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_list_operatori_empty(self, MockRepo: MagicMock) -> None:
        """Scopo: GET lista vuota ritorna count=0 e results=[]."""
        repo_instance = MockRepo.return_value
        repo_instance.list_operatori.return_value = ([], 0)

        view = OperatoriListView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request())

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"]["count"], 0)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_list_operatori_with_filters(self, MockRepo: MagicMock) -> None:
        """Scopo: Fase 7 — i filtri multi-face arrivano al repository."""
        repo_instance = MockRepo.return_value
        repo_instance.list_operatori.return_value = ([], 0)

        qp = {
            "search": "mario", "is_super_admin": "true",
            "is_active": "true", "limit": "10",
        }
        view = OperatoriListView()
        view.check_permissions = MagicMock()
        view.get(_admin_request(query_params=qp))

        call_kwargs = repo_instance.list_operatori.call_args.kwargs
        self.assertEqual(call_kwargs["search"], "mario")
        self.assertTrue(call_kwargs["is_super_admin"])
        self.assertTrue(call_kwargs["is_active"])
        self.assertEqual(call_kwargs["limit"], 10)
        # Niente piu' ruolo_sistema nei filtri (Fase 7).
        self.assertNotIn("ruolo_sistema", call_kwargs)

    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.api.permissions.PermissionResolver.is_super_admin", return_value=False)
    def test_list_operatori_permission_denied(
        self, mock_ruolo: MagicMock, _mock_load: MagicMock, _mock_save: MagicMock,
    ) -> None:
        """Scopo: Un operatore OPERATIVO non puo' accedere alla lista operatori."""
        from apps.core.api.permissions import IsAdminZeroERP
        perm = IsAdminZeroERP()
        request = _operativo_request()
        view = OperatoriListView()
        result = perm.has_permission(request, view)
        self.assertFalse(result)


class TestOperatoriDetailView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_detail_operatore_success(self, MockRepo: MagicMock) -> None:
        """Scopo: GET dettaglio ritorna i dati completi dell'operatore."""
        repo_instance = MockRepo.return_value
        repo_instance.get_operatore_detail.return_value = SAMPLE_DETAIL

        view = OperatoriDetailView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request(), auth_user_id=1)

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"]["username"], "operatore1")
        self.assertEqual(body["data"]["override_aree_count"], 2)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_detail_operatore_not_found(self, MockRepo: MagicMock) -> None:
        """Scopo: GET dettaglio per operatore inesistente solleva errore."""
        repo_instance = MockRepo.return_value
        repo_instance.get_operatore_detail.return_value = None

        view = OperatoriDetailView()
        view.check_permissions = MagicMock()

        from apps.core.services.service_errors import ServiceError
        with self.assertRaises(ServiceError):
            view.get(_admin_request(), auth_user_id=999)

    def test_detail_operatore_anonymous(self) -> None:
        """Scopo: Un utente non autenticato non puo' accedere al dettaglio."""
        from apps.core.api.permissions import IsAdminZeroERP
        perm = IsAdminZeroERP()
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = False
        self.assertFalse(perm.has_permission(request, OperatoriDetailView()))


class TestOperatoriPatchView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_operatore_success(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: PATCH modifica i campi e ritorna il dettaglio aggiornato."""
        repo_instance = MockRepo.return_value
        repo_instance.get_operatore_detail.return_value = SAMPLE_DETAIL

        view = OperatoriDetailView()
        view.check_permissions = MagicMock()
        data = {"email": "nuovo@test.it"}
        response = view.patch(_admin_request(method="PATCH", data=data), auth_user_id=1)

        self.assertEqual(response.status_code, 200)
        repo_instance.update_operatore.assert_called_once()

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_operatore_invalidates_cache(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: PATCH invalida la cache permessi dell'operatore modificato."""
        repo_instance = MockRepo.return_value
        repo_instance.get_operatore_detail.return_value = SAMPLE_DETAIL

        view = OperatoriDetailView()
        view.check_permissions = MagicMock()
        # Contract Fase 1: is_super_admin + attivo (no ruolo_sistema)
        view.patch(
            _admin_request(method="PATCH", data={"is_super_admin": True, "attivo": True}),
            auth_user_id=1,
        )

        mock_invalidate.assert_called_once_with(1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_operatore_not_found(self, MockRepo: MagicMock) -> None:
        """Scopo: PATCH su operatore inesistente solleva errore."""
        repo_instance = MockRepo.return_value
        repo_instance.get_operatore_detail.return_value = None

        view = OperatoriDetailView()
        view.check_permissions = MagicMock()

        from apps.core.services.service_errors import ServiceError
        with self.assertRaises(ServiceError):
            view.patch(_admin_request(method="PATCH", data={"email": "x@y.it"}), auth_user_id=999)

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_is_super_admin(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: Fase 7 — PATCH `is_super_admin: true, attivo: true` arriva
        al repo come bool nel contract multi-face (no traduzione legacy)."""
        repo_instance = MockRepo.return_value
        repo_instance.get_operatore_detail.return_value = SAMPLE_DETAIL

        view = OperatoriDetailView()
        view.check_permissions = MagicMock()
        view.patch(
            _admin_request(method="PATCH", data={"is_super_admin": True, "attivo": True}),
            auth_user_id=1,
        )

        call_kwargs = repo_instance.update_operatore.call_args.kwargs
        self.assertTrue(call_kwargs["is_super_admin"])
        self.assertTrue(call_kwargs["attivo"])
        self.assertNotIn("ruolo_sistema", call_kwargs)

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_attivo(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: PATCH cambio attivo passa il valore corretto al repository."""
        repo_instance = MockRepo.return_value
        repo_instance.get_operatore_detail.return_value = SAMPLE_DETAIL

        view = OperatoriDetailView()
        view.check_permissions = MagicMock()
        view.patch(_admin_request(method="PATCH", data={"attivo": False}), auth_user_id=1)

        call_kwargs = repo_instance.update_operatore.call_args.kwargs
        self.assertFalse(call_kwargs["attivo"])


class TestOperatoriDisabilitaView(TestCase):

    @patch("apps.amm_software.services.amm_software_service._blacklist_user_tokens")
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_disabilita_success(self, MockRepo: MagicMock, mock_invalidate: MagicMock, mock_blacklist: MagicMock) -> None:
        """Scopo: POST disabilita imposta stato e ritorna dettaglio aggiornato."""
        repo_instance = MockRepo.return_value
        disabled = {**SAMPLE_DETAIL, "ruolo_applicativo": "DISABILITATO", "attivo": False, "is_active": False}
        repo_instance.get_operatore_detail.side_effect = [SAMPLE_DETAIL, disabled]

        view = OperatoriDisabilitaView()
        view.check_permissions = MagicMock()
        response = view.post(_admin_request(method="POST"), auth_user_id=1)

        self.assertEqual(response.status_code, 200)
        repo_instance.disabilita_operatore.assert_called_once_with(1)

    @patch("apps.amm_software.services.amm_software_service._blacklist_user_tokens")
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_disabilita_invalidates_cache(self, MockRepo: MagicMock, mock_invalidate: MagicMock, mock_blacklist: MagicMock) -> None:
        """Scopo: POST disabilita invalida cache permessi."""
        repo_instance = MockRepo.return_value
        repo_instance.get_operatore_detail.return_value = SAMPLE_DETAIL

        view = OperatoriDisabilitaView()
        view.check_permissions = MagicMock()
        view.post(_admin_request(method="POST"), auth_user_id=1)

        mock_invalidate.assert_called_once_with(1)
        mock_blacklist.assert_called_once_with(1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_disabilita_not_found(self, MockRepo: MagicMock) -> None:
        """Scopo: POST disabilita su operatore inesistente solleva errore."""
        repo_instance = MockRepo.return_value
        repo_instance.get_operatore_detail.return_value = None

        view = OperatoriDisabilitaView()
        view.check_permissions = MagicMock()

        from apps.core.services.service_errors import ServiceError
        with self.assertRaises(ServiceError):
            view.post(_admin_request(method="POST"), auth_user_id=999)
