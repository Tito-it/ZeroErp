# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
16) test_credenziale_per_email_trovata — GET credenziale-per-email con credenziale
17) test_credenziale_per_email_assente — GET su email senza credenziale -> credenziale null
18) test_credenziale_per_email_solo_admin — OPERATIVO non puo' leggerla
19) test_list_operatori_includi_di_prova — gli utenti di prova solo a chi li chiede
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import (
    CredenzialePerEmailView,
    OperatoriDetailView,
    OperatoriDisabilitaView,
    OperatoriListView,
)
from apps.core.services.invito_veste import PORTA_OPERATORE
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova


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
    user = operatore_di_prova(user_id=50)
    request.user = user
    request.query_params = {}
    # Simula assenza cache per-request
    del request._zeroerp_perms_cache
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
        # Senza chiederli, gli utenti di prova restano fuori.
        self.assertIs(call_kwargs["includi_di_prova"], False)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_list_operatori_includi_di_prova(self, MockRepo: MagicMock) -> None:
        """Scopo: `includi_di_prova=true` arriva al repository; un valore estraneo e' un errore."""
        repo_instance = MockRepo.return_value
        repo_instance.list_operatori.return_value = ([], 0)
        view = OperatoriListView()
        view.check_permissions = MagicMock()

        view.get(_admin_request(query_params={"includi_di_prova": "true"}))
        self.assertIs(repo_instance.list_operatori.call_args.kwargs["includi_di_prova"], True)

        with self.assertRaises(ValueError):
            view.get(_admin_request(query_params={"includi_di_prova": "banana"}))

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
        repo_instance.get_categoria_accesso.return_value = "OPERATORE"
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
        repo_instance.get_categoria_accesso.return_value = "OPERATORE"
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

    # ⛔ Spegnere l'operatore invalida gli inviti pendenti (A-5): senza questo
    #    mock l'UPDATE andrebbe su `config.token_monouso` del DB di sviluppo.
    def setUp(self):
        patcher = patch("apps.amm_software.services.amm_software_service.InvitoVeste")
        self.mock_invito = patcher.start()
        self.addCleanup(patcher.stop)

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_operatore_success(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: PATCH modifica i campi e ritorna il dettaglio aggiornato."""
        repo_instance = MockRepo.return_value
        repo_instance.get_categoria_accesso.return_value = "OPERATORE"
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
        repo_instance.get_categoria_accesso.return_value = "OPERATORE"
        repo_instance.get_operatore_detail.return_value = {**SAMPLE_DETAIL, "veste_attiva": True}

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
        repo_instance.get_categoria_accesso.return_value = "OPERATORE"
        repo_instance.get_operatore_detail.return_value = None

        view = OperatoriDetailView()
        view.check_permissions = MagicMock()

        from apps.core.services.service_errors import ServiceError
        with self.assertRaises(ServiceError):
            view.patch(_admin_request(method="PATCH", data={"email": "x@y.it"}), auth_user_id=999)

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_is_super_admin(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: Fase 7 — PATCH `is_super_admin: true` arriva al repo come
        bool nel contract multi-face (no traduzione legacy); `attivo: true` su
        una veste gia' accesa non e' una transizione: nessuno spegnimento (D-3)."""
        repo_instance = MockRepo.return_value
        repo_instance.get_categoria_accesso.return_value = "OPERATORE"
        repo_instance.get_operatore_detail.return_value = {**SAMPLE_DETAIL, "veste_attiva": True}

        view = OperatoriDetailView()
        view.check_permissions = MagicMock()
        view.patch(
            _admin_request(method="PATCH", data={"is_super_admin": True, "attivo": True}),
            auth_user_id=1,
        )

        call_kwargs = repo_instance.update_operatore.call_args.kwargs
        self.assertTrue(call_kwargs["is_super_admin"])
        self.assertNotIn("attivo", call_kwargs)
        self.assertNotIn("ruolo_sistema", call_kwargs)
        repo_instance.disabilita_operatore.assert_not_called()

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_patch_attivo(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: PATCH `attivo: false` spegne con la scrittura di «Disabilita»
        (2026-10-04), e chiude le sessioni della sola veste operatore (A-5, D-5)."""
        repo_instance = MockRepo.return_value
        repo_instance.get_categoria_accesso.return_value = "OPERATORE"
        # Una veste ACCESA che si spegne: solo allora si chiudono sessioni e inviti.
        repo_instance.get_operatore_detail.return_value = {**SAMPLE_DETAIL, "veste_attiva": True}
        repo_instance.get_veste_operatore_id.return_value = 7

        view = OperatoriDetailView()
        view.check_permissions = MagicMock()
        view.patch(_admin_request(method="PATCH", data={"attivo": False}), auth_user_id=1)

        repo_instance.disabilita_operatore.assert_called_once_with(1)
        self.mock_invito.return_value.chiudi_veste_spenta.assert_called_once_with(
            PORTA_OPERATORE, auth_user_id=1, identita_id=7,
        )


class TestOperatoriDisabilitaView(TestCase):

    # ⛔ Spegnere l'operatore invalida gli inviti pendenti (A-5): senza questo
    #    mock l'UPDATE andrebbe su `config.token_monouso` del DB di sviluppo.
    def setUp(self):
        patcher = patch("apps.amm_software.services.amm_software_service.InvitoVeste")
        self.mock_invito = patcher.start()
        self.addCleanup(patcher.stop)

    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_disabilita_success(self, MockRepo: MagicMock, mock_invalidate: MagicMock) -> None:
        """Scopo: POST disabilita imposta stato e ritorna dettaglio aggiornato."""
        repo_instance = MockRepo.return_value
        disabled = {**SAMPLE_DETAIL, "veste_attiva": False, "attivo": False, "is_active": False}
        repo_instance.get_categoria_accesso.return_value = "OPERATORE"
        repo_instance.get_operatore_detail.side_effect = [SAMPLE_DETAIL, disabled]

        view = OperatoriDisabilitaView()
        view.check_permissions = MagicMock()
        response = view.post(_admin_request(method="POST"), auth_user_id=1)

        self.assertEqual(response.status_code, 200)
        repo_instance.disabilita_operatore.assert_called_once_with(1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_disabilita_invalidates_cache(self, MockRepo: MagicMock) -> None:
        """Scopo: POST disabilita chiude la veste operatore spenta col BB
        (`InvitoVeste.chiudi_veste_spenta`: inviti, sessioni e cache, provati
        in `core/tests/services/test_invito_veste.py`)."""
        repo_instance = MockRepo.return_value
        repo_instance.get_categoria_accesso.return_value = "OPERATORE"
        repo_instance.get_operatore_detail.return_value = SAMPLE_DETAIL
        repo_instance.get_veste_operatore_id.return_value = 7

        view = OperatoriDisabilitaView()
        view.check_permissions = MagicMock()
        view.post(_admin_request(method="POST"), auth_user_id=1)

        self.mock_invito.return_value.chiudi_veste_spenta.assert_called_once_with(
            PORTA_OPERATORE, auth_user_id=1, identita_id=7,
        )

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_disabilita_not_found(self, MockRepo: MagicMock) -> None:
        """Scopo: POST disabilita su operatore inesistente solleva errore."""
        repo_instance = MockRepo.return_value
        repo_instance.get_categoria_accesso.return_value = "OPERATORE"
        repo_instance.get_operatore_detail.return_value = None

        view = OperatoriDisabilitaView()
        view.check_permissions = MagicMock()

        from apps.core.services.service_errors import ServiceError
        with self.assertRaises(ServiceError):
            view.post(_admin_request(method="POST"), auth_user_id=999)


# B-20 (brief-db-credenziale-per-email §3): i dati del dialog di conferma del
# riuso. Il binding con la funzione del DB lo prova il test sul DB vero
# (`core/tests/db/test_login_credenziale_db`, consenso in due tempi).
class TestCredenzialePerEmailView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_credenziale_per_email_trovata(self, MockRepo: MagicMock) -> None:
        """Scopo: la credenziale arriva intera, e l'email passa com'e' (ripulita) al DB."""
        credenziale = {
            "auth_user_id": 42, "username": "mario.rossi",
            "vesti": [{"ruolo_applicativo": "CLIENTE_PORTALE", "attivo": True, "soggetto": "Rossi Srl"}],
        }
        MockRepo.return_value.get_credenziale_per_email.return_value = credenziale

        view = CredenzialePerEmailView()
        response = view.get(_admin_request(query_params={"email": "  Mario.Rossi@example.com "}))

        self.assertEqual(response.status_code, 200)
        import json
        self.assertEqual(json.loads(response.content)["data"], {"credenziale": credenziale})
        MockRepo.return_value.get_credenziale_per_email.assert_called_once_with("Mario.Rossi@example.com")

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_credenziale_per_email_assente(self, MockRepo: MagicMock) -> None:
        """Scopo: email senza credenziale (o vuota) -> `credenziale` null, non un errore."""
        MockRepo.return_value.get_credenziale_per_email.return_value = None

        view = CredenzialePerEmailView()
        response = view.get(_admin_request(query_params={"email": ""}))

        self.assertEqual(response.status_code, 200)
        import json
        self.assertEqual(json.loads(response.content)["data"], {"credenziale": None})
        # Vuota -> None: la regola «email vuota = nessuna» la applica il DB.
        MockRepo.return_value.get_credenziale_per_email.assert_called_once_with(None)

    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.api.permissions.PermissionResolver.is_super_admin", return_value=False)
    def test_credenziale_per_email_solo_admin(
        self, _mock_admin: MagicMock, _mock_load: MagicMock, _mock_save: MagicMock,
    ) -> None:
        """Scopo: dice se un'email ha un accesso: solo SUPER_ADMIN (nessun guard a DB)."""
        from apps.core.api.permissions import IsAdminZeroERP
        self.assertFalse(IsAdminZeroERP().has_permission(_operativo_request(), CredenzialePerEmailView()))
