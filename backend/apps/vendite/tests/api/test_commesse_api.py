# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test HTTP contract endpoint API commesse (§25.6).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) VenditeCommesseApiTests.test_post_run_commesse_push_ok
2) VenditeCommesseApiTests.test_post_run_commesse_push_v1_requires_jwt
3) VenditeCommesseApiTests.test_post_run_commesse_push_skipped
4) VenditeCommesseApiTests.test_get_commesse_push_log_ok
5) VenditeCommesseApiTests.test_get_commesse_push_log_v1_requires_jwt
6) VenditeCommesseApiTests.test_get_commesse_push_log_not_found
7) VenditeCommesseApiTests.test_get_commessa_stato_ok
8) VenditeCommesseApiTests.test_get_commessa_stato_v1_requires_jwt
9) VenditeCommesseApiTests.test_get_commessa_stato_not_found
10) VenditeCommesseApiTests.test_get_commessa_attivita_ok
11) VenditeCommesseApiTests.test_get_commessa_attivita_v1_requires_jwt
12) VenditeCommesseApiTests.test_get_commessa_attivita_invalid_limit
13) VenditeCommesseApiTests.test_get_commessa_attivita_con_filtri
"""

import json

from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase, override_settings

from apps.core.services.service_errors import ServiceError


@override_settings(API_STRONG_IDEMPOTENCY_ENABLED=False)
class VenditeCommesseApiTests(SimpleTestCase):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        self.client = Client()

    # ------------------------------------------------------------------ #
    # POST /api/v1/vendite/commesse/push/run/                            #
    # ------------------------------------------------------------------ #

    # Scopo: push ok → 200 con stato COMPLETATO.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_commesse_push")
    def test_post_run_commesse_push_ok(self, mocked_push, _mock_auth):
        mocked_push.return_value = {
            "stato": "COMPLETATO",
            "dry_run": False,
            "push_log_id": 10,
            "durata_ms": 150,
            "handlers": [{"handler_name": "HandlerA", "created": 2, "updated": 0, "skipped": 0, "errors": []}],
        }
        response = self.client.post(
            "/api/v1/vendite/commesse/push/run/",
            data=json.dumps({"dry_run": False}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-push-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["stato"], "COMPLETATO")
        self.assertEqual(data["push_log_id"], 10)
        mocked_push.assert_called_once()

    # Scopo: endpoint V1 richiede JWT.
    def test_post_run_commesse_push_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/commesse/push/run/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-push-auth-1"},
        )
        self.assertEqual(response.status_code, 401)

    # Scopo: lock occupato → 200 con stato SKIPPED.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_commesse_push")
    def test_post_run_commesse_push_skipped(self, mocked_push, _mock_auth):
        mocked_push.return_value = {
            "stato": "SKIPPED",
            "dry_run": False,
            "push_log_id": None,
            "durata_ms": 0,
            "handlers": [],
        }
        response = self.client.post(
            "/api/v1/vendite/commesse/push/run/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-push-skip-1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["stato"], "SKIPPED")

    # ------------------------------------------------------------------ #
    # GET /api/v1/vendite/commesse/push/<log_id>/                        #
    # ------------------------------------------------------------------ #

    # Scopo: push log trovato → 200.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_commesse_push_log")
    def test_get_commesse_push_log_ok(self, mocked_log, _mock_auth):
        mocked_log.return_value = {
            "id": 5,
            "run_at": "2026-02-26T10:00:00",
            "dry_run": False,
            "source_types": ["HandlerA"],
            "risultato": {"HandlerA": {"created": 1}},
            "stato": "COMPLETATO",
            "durata_ms": 100,
        }
        response = self.client.get("/api/v1/vendite/commesse/push/5/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["id"], 5)
        mocked_log.assert_called_once_with(push_log_id=5)

    # Scopo: endpoint V1 richiede JWT.
    def test_get_commesse_push_log_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/commesse/push/5/")
        self.assertEqual(response.status_code, 401)

    # Scopo: push log non trovato → 404.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_commesse_push_log")
    def test_get_commesse_push_log_not_found(self, mocked_log, _mock_auth):
        mocked_log.side_effect = ServiceError(
            code="E_COMMESSA_PUSH_LOG_NOT_FOUND",
            message="Push log non trovato.",
            detail="id=999",
        )
        response = self.client.get("/api/v1/vendite/commesse/push/999/")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_COMMESSA_PUSH_LOG_NOT_FOUND")

    # ------------------------------------------------------------------ #
    # GET /api/v1/vendite/commesse/<id>/stato/                           #
    # ------------------------------------------------------------------ #

    # Scopo: commessa trovata → 200 con contatori.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_commessa_stato")
    def test_get_commessa_stato_ok(self, mocked_stato, _mock_auth):
        mocked_stato.return_value = {
            "commessa_id": 1,
            "total_attivita": 10,
            "total_approvate": 8,
            "total_emesse": 5,
        }
        response = self.client.get("/api/v1/vendite/commesse/1/stato/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["commessa_id"], 1)
        self.assertEqual(data["total_attivita"], 10)
        mocked_stato.assert_called_once_with(commessa_id=1)

    # Scopo: endpoint V1 richiede JWT.
    def test_get_commessa_stato_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/commesse/1/stato/")
        self.assertEqual(response.status_code, 401)

    # Scopo: commessa non trovata → 404.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_commessa_stato")
    def test_get_commessa_stato_not_found(self, mocked_stato, _mock_auth):
        mocked_stato.side_effect = ServiceError(
            code="E_COMMESSA_NOT_FOUND",
            message="Commessa non trovata.",
            detail="id=999",
        )
        response = self.client.get("/api/v1/vendite/commesse/999/stato/")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_COMMESSA_NOT_FOUND")

    # ------------------------------------------------------------------ #
    # GET /api/v1/vendite/commesse/<id>/attivita/                        #
    # ------------------------------------------------------------------ #

    # Scopo: lista attivita ok → 200.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_commessa_attivita")
    def test_get_commessa_attivita_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = {
            "commessa_id": 1,
            "count": 0,
            "rows": [],
        }
        response = self.client.get("/api/v1/vendite/commesse/1/attivita/?limit=20&offset=0")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["commessa_id"], 1)
        self.assertEqual(data["count"], 0)
        mocked_list.assert_called_once_with(
            commessa_id=1, stato_emissione=None, stato_approvazione=None,
            competenza_mese=None, limit=20, offset=0,
        )

    # Scopo: endpoint V1 richiede JWT.
    def test_get_commessa_attivita_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/commesse/1/attivita/")
        self.assertEqual(response.status_code, 401)

    # Scopo: filtri opzionali propagati al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_commessa_attivita")
    def test_get_commessa_attivita_con_filtri(self, mocked_list, _mock_auth):
        mocked_list.return_value = {"commessa_id": 1, "count": 0, "rows": []}
        response = self.client.get(
            "/api/v1/vendite/commesse/1/attivita/?stato_emissione=NON_EMESSA&stato_approvazione=APPROVATA&competenza_mese=2026-02-01"
        )
        self.assertEqual(response.status_code, 200)
        mocked_list.assert_called_once_with(
            commessa_id=1, stato_emissione="NON_EMESSA", stato_approvazione="APPROVATA",
            competenza_mese="2026-02-01", limit=50, offset=0,
        )

    # Scopo: limit fuori range → 400.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_commessa_attivita")
    def test_get_commessa_attivita_invalid_limit(self, mocked_list, _mock_auth):
        mocked_list.side_effect = ServiceError(
            code="E_COMMESSA_VALIDATION",
            message="Parametri non validi.",
            detail="limit deve essere compreso tra 1 e 200",
        )
        response = self.client.get("/api/v1/vendite/commesse/1/attivita/?limit=500")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_COMMESSA_VALIDATION")
