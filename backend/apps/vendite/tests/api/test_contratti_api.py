# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints contratti v5 (F2-BE-06).
#        Mock service + JWT mockata. Nessun DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_contratti_ok
 2) test_list_contratti_filters
 3) test_list_contratti_requires_jwt
 4) test_get_detail_ok
 5) test_post_create_ok
 6) test_post_create_validation_error
 7) test_post_create_overlap_409
 8) test_patch_update_ok
 9) test_patch_immutabile_rifiutato
10) test_post_cambia_stato_ok
11) test_post_cambia_stato_modalita_c_tradotto
12) test_post_riga_ok
13) test_patch_riga_ok
14) test_delete_riga_ok
15) test_post_utility_ok
16) test_patch_utility_ok
"""

import json
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.api.views_contratti.ContrattiService"
_BASE = "/api/v1/vendite/contratti/"


class _BaseApiTest(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()
        self._req_log_patcher = patch(
            "apps.core.middleware.request_log_middleware.RequestLogMiddleware._insert_log",
            return_value=None,
        )
        self._req_log_patcher.start()
        self.addCleanup(self._req_log_patcher.stop)


class TestList(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_list_contratti_ok(self, svc_cls, _auth):
        svc_cls.return_value.list_contratti.return_value = (
            [{"id": 1, "numero": "CNT0000001"}], 1,
        )
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["count"], 1)
        self.assertEqual(body["data"]["results"][0]["numero"], "CNT0000001")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_list_contratti_filters(self, svc_cls, _auth):
        svc_cls.return_value.list_contratti.return_value = ([], 0)
        self.client.get(
            _BASE
            + "?billing_account_id=10&stato_doc_contratto_id=1&utility_id=3"
            + "&ambito=COMMODITY&listino_id=100&data_da=2025-01-01&data_a=2026-12-31"
            + "&search=CNT&order_by=numero&order_dir=asc&limit=10&offset=20"
        )
        kwargs = svc_cls.return_value.list_contratti.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 10)
        self.assertEqual(kwargs["stato_doc_contratto_id"], 1)
        self.assertEqual(kwargs["utility_id"], 3)
        self.assertEqual(kwargs["ambito"], "COMMODITY")
        self.assertEqual(kwargs["listino_id"], 100)
        self.assertEqual(str(kwargs["data_da"]), "2025-01-01")
        self.assertEqual(str(kwargs["data_a"]), "2026-12-31")
        self.assertEqual(kwargs["search"], "CNT")
        self.assertEqual(kwargs["order_by"], "numero")
        self.assertEqual(kwargs["order_dir"], "asc")
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 20)

    def test_list_contratti_requires_jwt(self):
        resp = self.client.get(_BASE)
        self.assertEqual(resp.status_code, 401)


class TestDetailGet(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_get_detail_ok(self, svc_cls, _auth):
        svc_cls.return_value.get_contratto.return_value = {
            "id": 7,
            "numero": "CNT0000007",
            "righe": [],
            "utility": None,
        }
        resp = self.client.get(_BASE + "7/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 7)


class TestRighePreview(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_get_righe_preview_ok(self, svc_cls, _auth):
        svc_cls.return_value.list_righe_preview.return_value = {
            "contratto_id": 7,
            "modalita": "A",
            "listino_id": 100,
            "listino_codice": "COM-001",
            "righe": [
                {"articolo_id": "uuid", "prezzo_finale": "90.00", "origine": "DA_LISTINO"},
            ],
        }
        resp = self.client.get(_BASE + "7/righe-preview/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["modalita"], "A")
        self.assertEqual(len(body["righe"]), 1)
        self.assertEqual(body["righe"][0]["origine"], "DA_LISTINO")


class TestPost(_BaseApiTest):
    _OK = {
        "billing_account_id": 10,
        "istanza_utility_id": 20,
        "utility_id": 3,
        "valido_dal": "2026-01-01",
        "listino_id": 100,
        "tipo_variazione_globale": "PERCENTUALE",
        "valore_variazione_globale": "10",
    }

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_create_ok(self, svc_cls, _auth):
        svc_cls.return_value.create_contratto.return_value = {
            "id": 1,
            "numero": "CNT0000001",
        }
        resp = self.client.post(
            _BASE, data=json.dumps(self._OK), content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_create_validation_error(self, svc_cls, _auth):
        svc_cls.return_value.create_contratto.side_effect = ServiceError(
            code="E_VENDITE_VALIDATION",
            message="Payload contratto non valido.",
        )
        resp = self.client.post(
            _BASE, data=json.dumps({"billing_account_id": 10}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_VENDITE_VALIDATION")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_create_overlap_409(self, svc_cls, _auth):
        svc_cls.return_value.create_contratto.side_effect = ServiceError(
            code="E_VENDITE_CONTRATTO_OVERLAP",
            message="Contratto sovrapposto.",
        )
        resp = self.client.post(
            _BASE, data=json.dumps(self._OK), content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["error"]["code"], "E_VENDITE_CONTRATTO_OVERLAP")


class TestPatch(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_update_ok(self, svc_cls, _auth):
        svc_cls.return_value.update_contratto.return_value = {"id": 5, "ambito": "COMMERCIO"}
        resp = self.client.patch(
            _BASE + "5/", data=json.dumps({"ambito": "COMMERCIO"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(svc_cls.return_value.update_contratto.call_args.args[0], 5)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_immutabile_rifiutato(self, svc_cls, _auth):
        svc_cls.return_value.update_contratto.side_effect = ServiceError(
            code="E_VENDITE_VALIDATION",
            message="Identificativi contratto non modificabili.",
        )
        resp = self.client.patch(
            _BASE + "5/", data=json.dumps({"numero": "CNT9999999"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_VENDITE_VALIDATION")


class TestCambiaStato(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_cambia_stato_ok(self, svc_cls, _auth):
        svc_cls.return_value.cambia_stato.return_value = {"id": 1, "stato_codice": "ATTIVO"}
        resp = self.client.post(
            _BASE + "1/cambia-stato/",
            data=json.dumps({"codice_interno": "ATTIVO"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        kwargs = svc_cls.return_value.cambia_stato.call_args.kwargs
        self.assertEqual(kwargs["codice_interno"], "ATTIVO")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_cambia_stato_modalita_c_tradotto(self, svc_cls, _auth):
        svc_cls.return_value.cambia_stato.side_effect = ServiceError(
            code="E_CONTRATTO_MODALITA_C_SENZA_RIGHE",
            message="Contratto in modalita' C senza righe.",
        )
        resp = self.client.post(
            _BASE + "1/cambia-stato/",
            data=json.dumps({"codice_interno": "ATTIVO"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["error"]["code"], "E_CONTRATTO_MODALITA_C_SENZA_RIGHE"
        )


class TestRighe(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_riga_ok(self, svc_cls, _auth):
        svc_cls.return_value.create_riga.return_value = {"id": 99, "prezzo_unitario": "25"}
        resp = self.client.post(
            _BASE + "1/righe/",
            data=json.dumps({
                "articolo_id": "00000000-0000-0000-0000-000000000001",
                "prezzo_unitario": "25",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(svc_cls.return_value.create_riga.call_args.args[0], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_riga_ok(self, svc_cls, _auth):
        svc_cls.return_value.update_riga.return_value = {"id": 99, "prezzo_unitario": "30"}
        resp = self.client.patch(
            _BASE + "1/righe/99/",
            data=json.dumps({"prezzo_unitario": "30"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(svc_cls.return_value.update_riga.call_args.args[0], 99)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_delete_riga_ok(self, svc_cls, _auth):
        svc_cls.return_value.delete_riga.return_value = None
        resp = self.client.delete(_BASE + "1/righe/99/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 99)
        svc_cls.return_value.delete_riga.assert_called_once_with(99)


class TestUtility(_BaseApiTest):
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_post_utility_ok(self, svc_cls, _auth):
        svc_cls.return_value.create_utility.return_value = {"id": 5, "tipo_utenza_id": 2}
        resp = self.client.post(
            _BASE + "1/utility/",
            data=json.dumps({"tipo_utenza_id": 2, "classe_utenza_id": 7}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(svc_cls.return_value.create_utility.call_args.args[0], 1)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_patch_utility_ok(self, svc_cls, _auth):
        svc_cls.return_value.update_utility.return_value = {"id": 5}
        resp = self.client.patch(
            _BASE + "1/utility/",
            data=json.dumps({"param_2_txt": "abc"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
