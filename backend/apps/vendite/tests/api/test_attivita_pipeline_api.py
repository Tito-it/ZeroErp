# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test HTTP contract endpoint pipeline attivita fatturabili (BE-3.2).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  VenditeAttivitaPipelineApiTests.test_run_attivita_pipeline_ok
2)  VenditeAttivitaPipelineApiTests.test_run_attivita_pipeline_invalid_json
3)  VenditeAttivitaPipelineApiTests.test_run_attivita_pipeline_requires_idempotency_key
4)  VenditeAttivitaPipelineApiTests.test_run_attivita_pipeline_v1_requires_jwt
5)  VenditeAttivitaPipelineApiTests.test_run_attivita_pipeline_service_error
6)  VenditeAttivitaPipelineApiTests.test_run_attivita_pipeline_converts_zero_ids_to_none
7)  VenditeAttivitaPipelineApiTests.test_run_attivita_pipeline_passes_sorgente_tipo_id
8)  VenditeAttivitaPipelineApiTests.test_get_attivita_pipeline_status_ok
9)  VenditeAttivitaPipelineApiTests.test_get_attivita_pipeline_status_v1_requires_jwt
10) VenditeAttivitaPipelineApiTests.test_get_attivita_pipeline_status_lotto_not_found
11) VenditeAttivitaPipelineApiTests.test_get_attivita_pipeline_status_invalid_lotto_id
12) VenditeAttivitaPipelineApiTests.test_get_attivita_task_runs_ok
13) VenditeAttivitaPipelineApiTests.test_get_attivita_task_runs_v1_requires_jwt
14) VenditeAttivitaPipelineApiTests.test_get_attivita_task_runs_with_branch_code_filter
"""

import json
from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase, override_settings

from apps.core.services.service_errors import ServiceError


@override_settings(API_STRONG_IDEMPOTENCY_ENABLED=False)
class VenditeAttivitaPipelineApiTests(SimpleTestCase):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        self.client = Client()

    # ------------------------------------------------------------------ #
    # POST /api/v1/vendite/attivita_fatturabili/pipeline/run/             #
    # ------------------------------------------------------------------ #

    # Scopo: Verifica il caso `test_run_attivita_pipeline_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_attivita_pipeline")
    def test_run_attivita_pipeline_ok(self, mocked_service, _mock_auth):
        mocked_service.return_value = 10
        response = self.client.post(
            "/api/v1/vendite/attivita_fatturabili/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "attivita-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["lotto_id"], 10)
        self.assertEqual(data["status"], "ok")
        self.assertIn("request_id", response.json()["meta"])
        mocked_service.assert_called_once()

    # Scopo: Verifica il caso `test_run_attivita_pipeline_invalid_json`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_run_attivita_pipeline_invalid_json(self, _mock_auth):
        response = self.client.post(
            "/api/v1/vendite/attivita_fatturabili/pipeline/run/",
            data="{invalid",
            content_type="application/json",
            headers={"Idempotency-Key": "attivita-inv-json-1"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_json")

    # Scopo: Verifica il caso `test_run_attivita_pipeline_requires_idempotency_key`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_run_attivita_pipeline_requires_idempotency_key(self, _mock_auth):
        response = self.client.post(
            "/api/v1/vendite/attivita_fatturabili/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_IDEMPOTENCY_KEY_REQUIRED")

    # Scopo: Verifica il caso `test_run_attivita_pipeline_v1_requires_jwt`.
    def test_run_attivita_pipeline_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/attivita_fatturabili/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "attivita-no-jwt-1"},
        )
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica il caso `test_run_attivita_pipeline_service_error`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_attivita_pipeline")
    def test_run_attivita_pipeline_service_error(self, mocked_service, _mock_auth):
        mocked_service.side_effect = ServiceError(
            code="E_ATTIVITA_PIPELINE",
            message="Lotto gia` in esecuzione.",
            detail="Operazione bloccata",
        )
        response = self.client.post(
            "/api/v1/vendite/attivita_fatturabili/pipeline/run/",
            data=json.dumps({"lotto_id": 5}),
            content_type="application/json",
            headers={"Idempotency-Key": "attivita-err-1"},
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_ATTIVITA_PIPELINE")

    # Scopo: Verifica il caso `test_run_attivita_pipeline_converts_zero_ids_to_none`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_attivita_pipeline")
    def test_run_attivita_pipeline_converts_zero_ids_to_none(self, mocked_service, _mock_auth):
        mocked_service.return_value = 11
        response = self.client.post(
            "/api/v1/vendite/attivita_fatturabili/pipeline/run/",
            data=json.dumps({
                "lotto_id": 0,
                "utility_id": 0,
                "billing_account_id": 0,
                "sorgente_tipo_id": 0,
                "emittente_soggetto_ruolo_id": 0,
                "dry_run": True,
            }),
            content_type="application/json",
            headers={"Idempotency-Key": "attivita-zero-1"},
        )
        self.assertEqual(response.status_code, 200)
        kwargs = mocked_service.call_args.kwargs
        self.assertIsNone(kwargs["lotto_id"])
        self.assertIsNone(kwargs["utility_id"])
        self.assertIsNone(kwargs["billing_account_id"])
        self.assertIsNone(kwargs["sorgente_tipo_id"])
        self.assertIsNone(kwargs["emittente_soggetto_ruolo_id"])

    # Scopo: Verifica il caso `test_run_attivita_pipeline_passes_sorgente_tipo_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_attivita_pipeline")
    def test_run_attivita_pipeline_passes_sorgente_tipo_id(self, mocked_service, _mock_auth):
        mocked_service.return_value = 20
        response = self.client.post(
            "/api/v1/vendite/attivita_fatturabili/pipeline/run/",
            data=json.dumps({"sorgente_tipo_id": 3, "dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "attivita-sorgente-1"},
        )
        self.assertEqual(response.status_code, 200)
        kwargs = mocked_service.call_args.kwargs
        self.assertEqual(kwargs["sorgente_tipo_id"], 3)

    # ------------------------------------------------------------------ #
    # GET /api/v1/vendite/attivita_fatturabili/pipeline/<id>/status/      #
    # ------------------------------------------------------------------ #

    # Scopo: Verifica il caso `test_get_attivita_pipeline_status_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_attivita_pipeline_status")
    def test_get_attivita_pipeline_status_ok(self, mocked_status, _mock_auth):
        mocked_status.return_value = {
            "lotto_id": 10,
            "stato_lotto": "COMPLETATO",
            "stato_operativo": "APERTO",
            "branch_summary": {
                "PREVENTIVI": {"COMPLETATO": 2},
                "ORDINI": {"COMPLETATO": 3, "ERRORE": 1},
            },
        }
        response = self.client.get("/api/v1/vendite/attivita_fatturabili/pipeline/10/status/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["lotto_id"], 10)
        self.assertEqual(data["stato_lotto"], "COMPLETATO")
        self.assertIn("branch_summary", data)
        self.assertIn("PREVENTIVI", data["branch_summary"])
        mocked_status.assert_called_once_with(lotto_id=10)

    # Scopo: Verifica il caso `test_get_attivita_pipeline_status_v1_requires_jwt`.
    def test_get_attivita_pipeline_status_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/attivita_fatturabili/pipeline/10/status/")
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica il caso `test_get_attivita_pipeline_status_lotto_not_found`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_attivita_pipeline_status")
    def test_get_attivita_pipeline_status_lotto_not_found(self, mocked_status, _mock_auth):
        mocked_status.side_effect = ServiceError(
            code="E_ATTIVITA_LOTTO_NOT_FOUND",
            message="Lotto attivita non trovato.",
            detail="id=999",
        )
        response = self.client.get("/api/v1/vendite/attivita_fatturabili/pipeline/999/status/")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_ATTIVITA_LOTTO_NOT_FOUND")

    # Scopo: Verifica il caso `test_get_attivita_pipeline_status_invalid_lotto_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_attivita_pipeline_status")
    def test_get_attivita_pipeline_status_invalid_lotto_id(self, mocked_status, _mock_auth):
        mocked_status.side_effect = ServiceError(
            code="E_ATTIVITA_VALIDATION",
            message="Parametri non validi.",
            detail="lotto_id obbligatorio e > 0",
        )
        response = self.client.get("/api/v1/vendite/attivita_fatturabili/pipeline/0/status/")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_ATTIVITA_VALIDATION")

    # ------------------------------------------------------------------ #
    # GET /api/v1/vendite/attivita_fatturabili/pipeline/<id>/task-runs/  #
    # ------------------------------------------------------------------ #

    # Scopo: Verifica il caso `test_get_attivita_task_runs_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_attivita_task_runs")
    def test_get_attivita_task_runs_ok(self, mocked_task_runs, _mock_auth):
        mocked_task_runs.return_value = {
            "lotto_id": 10,
            "count": 1,
            "task_runs": [
                {
                    "id": 1,
                    "lotto_attivita_id": 10,
                    "pipeline_id": 1,
                    "sorgente_tipo_id": 3,
                    "branch_code": "PREVENTIVI",
                    "task_code": "acquisisci_preventivi_default",
                    "fase": "Acquisizione",
                    "tentativo": 1,
                    "task_stato": "COMPLETATO",
                    "block_scope": "BRANCH",
                    "depends_on": [],
                    "started_at": "2026-02-23T10:00:00",
                    "ended_at": "2026-02-23T10:00:02",
                    "error_code": None,
                    "error_message": None,
                    "meta": {},
                }
            ],
        }
        response = self.client.get(
            "/api/v1/vendite/attivita_fatturabili/pipeline/10/task-runs/?limit=50"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["lotto_id"], 10)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["task_runs"][0]["branch_code"], "PREVENTIVI")
        mocked_task_runs.assert_called_once_with(lotto_id=10, limit=50, branch_code=None)

    # Scopo: Verifica il caso `test_get_attivita_task_runs_v1_requires_jwt`.
    def test_get_attivita_task_runs_v1_requires_jwt(self):
        response = self.client.get(
            "/api/v1/vendite/attivita_fatturabili/pipeline/10/task-runs/"
        )
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica il caso `test_get_attivita_task_runs_with_branch_code_filter`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_attivita_task_runs")
    def test_get_attivita_task_runs_with_branch_code_filter(self, mocked_task_runs, _mock_auth):
        mocked_task_runs.return_value = {"lotto_id": 10, "count": 0, "task_runs": []}
        response = self.client.get(
            "/api/v1/vendite/attivita_fatturabili/pipeline/10/task-runs/?branch_code=DEFAULT"
        )
        self.assertEqual(response.status_code, 200)
        mocked_task_runs.assert_called_once_with(lotto_id=10, limit=100, branch_code="DEFAULT")
