# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari POST creazione operatore modulo Amm. Software.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_crea_operatore_success — POST crea operatore con successo (flusso A)
 2) test_crea_operatore_missing_cognome — POST senza cognome -> errore (flusso A)
 3) test_crea_operatore_password_rifiutata — POST con password -> errore (la sceglie l'operatore)
 4) test_crea_operatore_missing_cf — POST senza codice_fiscale -> errore (flusso A)
 5) test_crea_operatore_missing_qualifica — POST senza qualifica_id -> errore
 6) test_crea_operatore_senza_password_dell_admin — segnaposto non utilizzabile, riuso in risposta
 7) test_crea_operatore_permission_denied — OPERATIVO non puo' creare
 8) test_crea_operatore_with_sprint3_params — POST con comune_nascita e indirizzi
 9) test_crea_operatore_sprint3_params_optional — POST senza params Sprint 3 (retrocompatibile)
10) test_crea_operatore_flow_b_soggetto_esistente — POST con soggetto_id (flusso B)
11) test_crea_operatore_flow_b_cognome_non_richiesto — flusso B: cognome assente OK
12) test_crea_operatore_flow_b_uuid_invalido — soggetto_id malformato -> errore 400
13) test_crea_operatore_qualifica_non_numerica — qualifica_id non numerico -> errore 400
14) test_crea_operatore_is_super_admin_stringa_rifiutato — "false" come stringa: 400 sul campo, nessun operatore creato
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import OperatoriListView


SAMPLE_DETAIL = {
    "auth_user_id": 42,
    "username": "nuovo_op",
    "email": "nuovo@test.it",
    "first_name": "Luca",
    "last_name": "Bianchi",
    "is_super_admin": False,
    "ruolo_applicativo": "OPERATORE",
    "is_active": True,
    "unita_organizzativa_id": 10,
    "unita_organizzativa_nome": "Reparto A",
    "risorsa_umana_id": 200,
    "attivo": True,
    "valido_al": None,
    "data_insert": "2026-03-12",
    "override_aree_count": 0,
    "override_azioni_count": 0,
    "emittenti_count": 0,
}

VALID_PAYLOAD = {
    "cognome": "Bianchi",
    "nome": "Luca",
    "codice_fiscale": "BNCLCU90A01H501X",
    "sesso": "M",
    "username": "nuovo_op",
    "email": "nuovo@test.it",
    "qualifica_id": 1,
    "unita_organizzativa_id": 10,
}


# Il ritorno della madre (P-2): credenziale, username effettivo, riuso.
_CREATO = {"auth_user_id": 42, "username": "nuovo_op", "credenziale_riusata": False}


def _make_admin_request(payload: dict) -> MagicMock:
    """Crea una request mock POST con payload JSON e utente ADMIN."""
    request = MagicMock()
    request.method = "POST"
    request.content_type = "application/json"
    request.body = json.dumps(payload).encode("utf-8")
    request.data = payload
    request.user = MagicMock(is_authenticated=True, is_superuser=True, id=1)
    request.META = {"CONTENT_TYPE": "application/json"}
    return request


def _make_operativo_request(payload: dict) -> MagicMock:
    """Crea una request mock POST con utente OPERATIVO."""
    request = _make_admin_request(payload)
    request.user = MagicMock(is_authenticated=True, is_superuser=False, id=2)
    return request


class TestCreaOperatoreSuccess(TestCase):
    """POST /api/v1/amm-software/operatori/ — creazione con successo."""

    @patch("apps.amm_software.api.views.handle_post_json")
    def test_crea_operatore_success(self, mock_handle):
        """POST crea operatore con successo — handler invocato."""
        mock_handle.return_value = MagicMock(status_code=200)
        view = OperatoriListView()
        request = _make_admin_request(VALID_PAYLOAD)

        view.post(request)
        mock_handle.assert_called_once()
        # Verifica che handler kwarg sia passato
        _, kwargs = mock_handle.call_args
        self.assertIn("handler", kwargs)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_senza_password_dell_admin(
        self, mock_parse, mock_idemp, mock_reqid, mock_repo_cls
    ):
        """La credenziale nuova nasce col segnaposto NON utilizzabile: la
        password la sceglie l'operatore attivando l'invito (L-3). La risposta
        dice se la credenziale e' stata riusata (D-6)."""
        from django.contrib.auth.hashers import is_password_usable

        mock_parse.return_value = VALID_PAYLOAD
        mock_repo = MagicMock()
        mock_repo.crea_operatore.return_value = _CREATO
        mock_repo.get_operatore_detail.return_value = SAMPLE_DETAIL
        mock_repo_cls.return_value = mock_repo

        view = OperatoriListView()
        request = _make_admin_request(VALID_PAYLOAD)
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        call_kwargs = mock_repo.crea_operatore.call_args.kwargs
        self.assertFalse(is_password_usable(call_kwargs["password_hash"]))
        self.assertNotIn("attivo", call_kwargs)
        self.assertFalse(json.loads(response.content)["data"]["credenziale_riusata"])


class TestCreaOperatoreValidation(TestCase):
    """POST /api/v1/amm-software/operatori/ — validazione campi obbligatori."""

    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_missing_cognome(self, mock_parse, mock_idemp, mock_reqid):
        """POST senza cognome -> errore validazione."""
        payload = {**VALID_PAYLOAD, "cognome": ""}
        mock_parse.return_value = payload

        view = OperatoriListView()
        request = _make_admin_request(payload)
        response = view.post(request)

        data = json.loads(response.content)
        self.assertIn("error", data)

    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_password_rifiutata(self, mock_parse, mock_idemp, mock_reqid):
        """POST con password -> errore: la sceglie l'operatore all'attivazione."""
        payload = {**VALID_PAYLOAD, "password": "SecurePass123!"}
        mock_parse.return_value = payload

        view = OperatoriListView()
        request = _make_admin_request(payload)
        response = view.post(request)

        data = json.loads(response.content)
        self.assertIn("error", data)

    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_missing_cf(self, mock_parse, mock_idemp, mock_reqid):
        """POST senza codice_fiscale -> errore validazione."""
        payload = {**VALID_PAYLOAD, "codice_fiscale": ""}
        mock_parse.return_value = payload

        view = OperatoriListView()
        request = _make_admin_request(payload)
        response = view.post(request)

        data = json.loads(response.content)
        self.assertIn("error", data)

    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_missing_qualifica(self, mock_parse, mock_idemp, mock_reqid):
        """POST senza qualifica_id -> errore validazione."""
        payload = {**VALID_PAYLOAD}
        payload.pop("qualifica_id")
        mock_parse.return_value = payload

        view = OperatoriListView()
        request = _make_admin_request(payload)
        response = view.post(request)

        data = json.loads(response.content)
        self.assertIn("error", data)


VALID_PAYLOAD_SPRINT3 = {
    **VALID_PAYLOAD,
    "comune_nascita_id": 4517,
    "indirizzo_resid_dettaglio_id": 101,
    "indirizzo_domfisc_dettaglio_id": 102,
}


class TestCreaOperatoreSprint3(TestCase):
    """POST /api/v1/amm-software/operatori/ — parametri Sprint 3."""

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_with_sprint3_params(
        self, mock_parse, mock_idemp, mock_reqid, mock_repo_cls
    ):
        """POST con comune_nascita_id e indirizzi — passati al repository."""
        mock_parse.return_value = VALID_PAYLOAD_SPRINT3
        mock_repo = MagicMock()
        mock_repo.crea_operatore.return_value = _CREATO
        mock_repo.get_operatore_detail.return_value = SAMPLE_DETAIL
        mock_repo_cls.return_value = mock_repo

        view = OperatoriListView()
        request = _make_admin_request(VALID_PAYLOAD_SPRINT3)
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        call_kwargs = mock_repo.crea_operatore.call_args.kwargs
        self.assertEqual(call_kwargs["comune_nascita_id"], 4517)
        self.assertEqual(call_kwargs["indirizzo_resid_dettaglio_id"], 101)
        self.assertEqual(call_kwargs["indirizzo_domfisc_dettaglio_id"], 102)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_sprint3_params_optional(
        self, mock_parse, mock_idemp, mock_reqid, mock_repo_cls
    ):
        """POST senza parametri Sprint 3 — retrocompatibile, valori None."""
        mock_parse.return_value = VALID_PAYLOAD
        mock_repo = MagicMock()
        mock_repo.crea_operatore.return_value = _CREATO
        mock_repo.get_operatore_detail.return_value = SAMPLE_DETAIL
        mock_repo_cls.return_value = mock_repo

        view = OperatoriListView()
        request = _make_admin_request(VALID_PAYLOAD)
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        call_kwargs = mock_repo.crea_operatore.call_args.kwargs
        self.assertIsNone(call_kwargs["comune_nascita_id"])
        self.assertIsNone(call_kwargs["indirizzo_resid_dettaglio_id"])
        self.assertIsNone(call_kwargs["indirizzo_domfisc_dettaglio_id"])


VALID_PAYLOAD_FLOW_B = {
    "soggetto_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "op_existing",
    "email": "op@test.it",
    "qualifica_id": 1,
    "unita_organizzativa_id": 10,
}


class TestCreaOperatoreFlowB(TestCase):
    """POST /api/v1/amm-software/operatori/ — flusso B (soggetto esistente)."""

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_flow_b_soggetto_esistente(
        self, mock_parse, mock_idemp, mock_reqid, mock_repo_cls
    ):
        """POST con soggetto_id — flusso B: soggetto_id passato al repository."""
        mock_parse.return_value = VALID_PAYLOAD_FLOW_B
        mock_repo = MagicMock()
        mock_repo.crea_operatore.return_value = _CREATO
        mock_repo.get_operatore_detail.return_value = SAMPLE_DETAIL
        mock_repo_cls.return_value = mock_repo

        view = OperatoriListView()
        request = _make_admin_request(VALID_PAYLOAD_FLOW_B)
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        call_kwargs = mock_repo.crea_operatore.call_args.kwargs
        self.assertEqual(call_kwargs["soggetto_id"], "550e8400-e29b-41d4-a716-446655440000")
        self.assertIsNone(call_kwargs["cognome"])
        self.assertIsNone(call_kwargs["nome"])
        self.assertIsNone(call_kwargs["codice_fiscale"])
        # Col soggetto esistente il sesso non serve e non si inventa.
        self.assertIsNone(call_kwargs["sesso"])

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_flow_b_cognome_non_richiesto(
        self, mock_parse, mock_idemp, mock_reqid, mock_repo_cls
    ):
        """Flusso B: cognome vuoto e' accettato (soggetto gia' esiste)."""
        payload = {**VALID_PAYLOAD_FLOW_B, "cognome": ""}
        mock_parse.return_value = payload
        mock_repo = MagicMock()
        mock_repo.crea_operatore.return_value = _CREATO
        mock_repo.get_operatore_detail.return_value = SAMPLE_DETAIL
        mock_repo_cls.return_value = mock_repo

        view = OperatoriListView()
        request = _make_admin_request(payload)
        response = view.post(request)

        # Nessun errore di validazione — cognome non richiesto in flusso B
        self.assertEqual(response.status_code, 200)

    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_flow_b_uuid_invalido(self, mock_parse, mock_idemp, mock_reqid):
        """Flusso B: soggetto_id non UUID valido -> errore 400."""
        payload = {**VALID_PAYLOAD_FLOW_B, "soggetto_id": "non-un-uuid"}
        mock_parse.return_value = payload

        view = OperatoriListView()
        request = _make_admin_request(payload)
        response = view.post(request)

        data = json.loads(response.content)
        self.assertIn("error", data)

    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_qualifica_non_numerica(self, mock_parse, mock_idemp, mock_reqid):
        """qualifica_id non numerico -> errore 400."""
        payload = {**VALID_PAYLOAD, "qualifica_id": "abc"}
        mock_parse.return_value = payload

        view = OperatoriListView()
        request = _make_admin_request(payload)
        response = view.post(request)

        data = json.loads(response.content)
        self.assertIn("error", data)


    # Scopo: ⛔ `is_super_admin` dal BB, non da `bool(...)`. Con `bool("false")`
    #        (che e' True) una stringa nel corpo creava un SUPER_ADMIN: ora e'
    #        un 400 `E_AMM_VALIDAZIONE` sul campo, e il repository non e' toccato.
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.core.api.endpoint_helpers.get_request_id", return_value=None)
    @patch("apps.core.api.endpoint_helpers.get_idempotency_key", return_value=None)
    @patch("apps.core.api.endpoint_helpers.parse_json_body")
    def test_crea_operatore_is_super_admin_stringa_rifiutato(
        self, mock_parse, mock_idemp, mock_reqid, repo_cls,
    ):
        payload = {**VALID_PAYLOAD, "is_super_admin": "false"}
        mock_parse.return_value = payload

        response = OperatoriListView().post(_make_admin_request(payload))

        self.assertEqual(response.status_code, 400)
        errore = json.loads(response.content)["error"]
        self.assertEqual(errore["code"], "E_AMM_VALIDAZIONE")
        repo_cls.return_value.crea_operatore.assert_not_called()


class TestCreaOperatorePermission(TestCase):
    """POST /api/v1/amm-software/operatori/ — verifica permessi."""

    @patch("apps.core.api.permissions.PermissionResolver")
    @patch("apps.core.api.permissions.ZeroERPPermission._get_cache", return_value={})
    @patch("apps.core.api.permissions.ZeroERPPermission._save_cache_to_redis")
    def test_crea_operatore_permission_denied(self, mock_save, mock_cache, mock_resolver):
        """OPERATIVO non puo' creare operatori."""
        mock_resolver.is_super_admin.return_value = False

        view = OperatoriListView()
        request = _make_operativo_request(VALID_PAYLOAD)
        view.request = request

        from apps.core.api.permissions import IsAdminZeroERP
        perm = IsAdminZeroERP()
        result = perm.has_permission(request, view)
        self.assertFalse(result)
