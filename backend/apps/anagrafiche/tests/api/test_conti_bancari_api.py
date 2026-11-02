# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints conti bancari.
#        Mock del service e JWT auth, nessun accesso DB (compatibilita CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_lookup_conti_bancari_ok — GET lookup IBAN
 2) test_lookup_bank_branches_ok — GET lookup filiali
 3) test_list_conti_soggetto_ok — GET lista conti soggetto
 4) test_create_conto_soggetto_ok — POST crea legame soggetto
 5) test_create_conto_soggetto_validation_error — POST con dati mancanti
 6) test_update_conto_soggetto_ok — PATCH aggiorna legame soggetto
 7) test_delete_conto_soggetto_ok — DELETE elimina legame soggetto
 8) test_list_conti_ruolo_ok — GET lista conti ruolo
 9) test_create_conto_ruolo_ok — POST crea legame ruolo
10) test_update_conto_ruolo_ok — PATCH aggiorna legame ruolo
11) test_delete_conto_ruolo_ok — DELETE elimina legame ruolo
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

from apps.core.services.service_errors import ServiceError

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.anagrafiche.api.views_conti_bancari.ContiBancariService"

_FAKE_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_FAKE_IBAN = "IT60X0542811101000000123456"


class TestContiBancariLookupApi(JwtMockedApiTest):
    """Test endpoint lookup registro IBAN e filiali."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_lookup_conti_bancari_ok(self, mock_svc_cls, _auth):
        """GET /anagrafiche/conti-bancari/lookup/ — risultati."""
        mock_svc_cls.return_value.search_conti_bancari.return_value = [
            {"id": 1, "iban": _FAKE_IBAN},
        ]
        resp = self.client.get("/api/v1/anagrafiche/conti-bancari/lookup/?search=IT60")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_lookup_bank_branches_ok(self, mock_svc_cls, _auth):
        """GET /anagrafiche/bank-branches/lookup/ — risultati."""
        mock_svc_cls.return_value.search_bank_branches.return_value = [
            {"id": 1, "filiale_nome": "Filiale Milano"},
        ]
        resp = self.client.get("/api/v1/anagrafiche/bank-branches/lookup/?search=Milano")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 1)


class TestContiBancariSoggettoApi(JwtMockedApiTest):
    """Test endpoint CRUD conti bancari soggetto."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_list_conti_soggetto_ok(self, mock_svc_cls, _auth):
        """GET /anagrafiche/soggetti/{id}/conti-bancari/ — lista."""
        mock_svc_cls.return_value.list_conti_soggetto.return_value = [
            {"id": 1, "iban": _FAKE_IBAN, "uso": "INCASSO"},
        ]
        resp = self.client.get(f"/api/v1/anagrafiche/soggetti/{_FAKE_UUID}/conti-bancari/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_create_conto_soggetto_ok(self, mock_svc_cls, _auth):
        """POST /anagrafiche/soggetti/{id}/conti-bancari/ — crea."""
        mock_svc_cls.return_value.create_conto_soggetto.return_value = {
            "id": 10, "conto_bancario_id": 1, "uso": "INCASSO",
        }
        resp = self.client.post(
            f"/api/v1/anagrafiche/soggetti/{_FAKE_UUID}/conti-bancari/",
            data=json.dumps({
                "iban": _FAKE_IBAN, "bank_branch_id": 1,
                "uso": "INCASSO", "predefinito": True,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["id"], 10)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_create_conto_soggetto_validation_error(self, mock_svc_cls, _auth):
        """POST con dati mancanti → errore service."""
        mock_svc_cls.return_value.create_conto_soggetto.side_effect = ServiceError(
            code="E_ANAG_VALIDAZIONE", message="IBAN obbligatorio.",
        )
        resp = self.client.post(
            f"/api/v1/anagrafiche/soggetti/{_FAKE_UUID}/conti-bancari/",
            data=json.dumps({"bank_branch_id": 1}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 422))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_ANAG_VALIDAZIONE")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_update_conto_soggetto_ok(self, mock_svc_cls, _auth):
        """PATCH /anagrafiche/soggetti/{id}/conti-bancari/{cb_id}/ — aggiorna."""
        mock_svc_cls.return_value.update_conto_soggetto.return_value = {"updated": True}
        resp = self.client.patch(
            f"/api/v1/anagrafiche/soggetti/{_FAKE_UUID}/conti-bancari/10/",
            data=json.dumps({"uso": "PAGAMENTO"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["updated"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_delete_conto_soggetto_ok(self, mock_svc_cls, _auth):
        """DELETE /anagrafiche/soggetti/{id}/conti-bancari/{cb_id}/ — elimina."""
        mock_svc_cls.return_value.delete_conto_soggetto.return_value = {"deleted": True}
        resp = self.client.delete(
            f"/api/v1/anagrafiche/soggetti/{_FAKE_UUID}/conti-bancari/10/",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["deleted"])


class TestContiBancariRuoloApi(JwtMockedApiTest):
    """Test endpoint CRUD conti bancari ruolo."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_list_conti_ruolo_ok(self, mock_svc_cls, _auth):
        """GET /anagrafiche/ruoli/{id}/conti-bancari/ — lista con ereditati."""
        mock_svc_cls.return_value.list_conti_ruolo.return_value = {
            "conti_ruolo": [{"id": 1, "uso": "INCASSO"}],
            "conti_ereditati": [{"id": 2, "uso": "GENERICO"}],
        }
        resp = self.client.get("/api/v1/anagrafiche/ruoli/10/conti-bancari/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["conti_ruolo"]), 1)
        self.assertEqual(len(body["data"]["conti_ereditati"]), 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_create_conto_ruolo_ok(self, mock_svc_cls, _auth):
        """POST /anagrafiche/ruoli/{id}/conti-bancari/ — crea."""
        mock_svc_cls.return_value.create_conto_ruolo.return_value = {
            "id": 20, "conto_bancario_id": 1, "uso": "PAGAMENTO",
        }
        resp = self.client.post(
            "/api/v1/anagrafiche/ruoli/10/conti-bancari/",
            data=json.dumps({
                "iban": _FAKE_IBAN, "bank_branch_id": 1, "uso": "PAGAMENTO",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["id"], 20)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_update_conto_ruolo_ok(self, mock_svc_cls, _auth):
        """PATCH /anagrafiche/ruoli/{id}/conti-bancari/{cb_id}/ — aggiorna."""
        mock_svc_cls.return_value.update_conto_ruolo.return_value = {"updated": True}
        resp = self.client.patch(
            "/api/v1/anagrafiche/ruoli/10/conti-bancari/20/",
            data=json.dumps({"predefinito": True}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_delete_conto_ruolo_ok(self, mock_svc_cls, _auth):
        """DELETE /anagrafiche/ruoli/{id}/conti-bancari/{cb_id}/ — elimina."""
        mock_svc_cls.return_value.delete_conto_ruolo.return_value = {"deleted": True}
        resp = self.client.delete("/api/v1/anagrafiche/ruoli/10/conti-bancari/20/")
        self.assertEqual(resp.status_code, 200)
