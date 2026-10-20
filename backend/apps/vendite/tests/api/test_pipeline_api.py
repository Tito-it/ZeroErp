"""
Indice test eseguiti:
1) VenditePipelineApiTests.test_run_lotto_pipeline_ok
2) VenditePipelineApiTests.test_run_lotto_pipeline_invalid_json
3) VenditePipelineApiTests.test_run_lotto_pipeline_pipeline_error
4) VenditePipelineApiTests.test_run_lotto_pipeline_retryable_error
5) VenditePipelineApiTests.test_run_lotto_pipeline_echoes_idempotency_key
6) VenditePipelineApiTests.test_run_lotto_pipeline_requires_idempotency_key
7) VenditePipelineApiTests.test_run_lotto_pipeline_v1_requires_jwt
8) VenditePipelineApiTests.test_legacy_vendite_path_not_found_when_disabled
9) VenditePipelineApiTests.test_run_lotto_pipeline_hides_technical_detail_for_generic_errors
10) VenditePipelineApiTests.test_run_lotto_pipeline_exposes_technical_message_in_debug_mode
11) VenditePipelineApiTests.test_run_lotto_pipeline_replays_completed_response_when_strong_idempotency_enabled
12) VenditePipelineApiTests.test_run_lotto_pipeline_returns_conflict_when_idempotency_in_progress
13) VenditePipelineApiTests.test_run_lotto_pipeline_accepts_null_lotto_id
14) VenditePipelineApiTests.test_run_lotto_pipeline_converts_zero_optional_ids_to_none
15) VenditePipelineApiTests.test_run_lotto_pipeline_full_payload_new_lotto_massivo_ok
16) VenditePipelineApiTests.test_get_lotto_segnalazioni_summary_ok
17) VenditePipelineApiTests.test_get_lotto_segnalazioni_rows_filtri_dal_query_param
18) VenditePipelineApiTests.test_get_lotto_segnalazioni_summary_v1_requires_jwt
19) VenditePipelineApiTests.test_get_lotto_segnalazioni_summary_rejects_invalid_lotto_id
20) VenditePipelineApiTests.test_get_lotto_task_runs_ok
20-bis) VenditePipelineApiTests.test_get_lotto_task_runs_filtri
20-ter) VenditePipelineApiTests.test_get_lotto_task_runs_stato_vuoto_non_filtra
21) VenditePipelineApiTests.test_get_lotto_task_runs_v1_requires_jwt
22) VenditePipelineApiTests.test_get_lotto_task_runs_rejects_invalid_lotto_id
"""

import json
from unittest.mock import patch
from unittest.mock import Mock

from django.test import Client, override_settings
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

from apps.core.services.idempotency_store import IdempotencyDecision
from apps.core.services.service_errors import ServiceError


class VenditePipelineApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: Verifica il caso `test_run_lotto_pipeline_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_ok(self, mocked_service, _mock_auth):
        mocked_service.return_value = 123
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"tipo_lotto": "MASSIVO", "dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["lotto_id"], 123)
        self.assertIn("request_id", response.json()["meta"])
        self.assertTrue(response["X-Request-ID"])
        mocked_service.assert_called_once()

    # Scopo: Verifica il caso `test_run_lotto_pipeline_invalid_json`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_run_lotto_pipeline_invalid_json(self, _mock_auth):
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data="{invalid",
            content_type="application/json",
            headers={"Idempotency-Key": "idem-ok-2"},
        )
        self.assertEqual(response.status_code, 400)
        # Nell'envelope dal 2026-10-07 (E-6), come le view DRF.
        self.assertEqual(response.json()["error"]["code"], "E_VALIDATION_INPUT")

    # Scopo: Verifica il caso `test_run_lotto_pipeline_pipeline_error`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_pipeline_error(self, mocked_service, _mock_auth):
        mocked_service.side_effect = ServiceError(
            code="E_PIPELINE_LOTTO_NOT_FOUND",
            message="Lotto pipeline non trovato.",
            detail="Lotto non trovato",
        )
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"lotto_id": 999}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-ok-3"},
        )
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_PIPELINE_LOTTO_NOT_FOUND")
        self.assertIn("Lotto non trovato", body["detail"])
        self.assertEqual(body["ui_action"], "show_empty_state")

    # Scopo: Verifica il caso `test_run_lotto_pipeline_retryable_error`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_retryable_error(self, mocked_service, _mock_auth):
        mocked_service.side_effect = ServiceError(
            code="E_DATABASE_RETRYABLE",
            message="Conflitto transazionale, riprovare.",
            retryable=True,
        )
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"lotto_id": 1}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-ok-4"},
        )
        self.assertEqual(response.status_code, 409)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_DATABASE_RETRYABLE")
        self.assertEqual(body["ui_action"], "show_retry_dialog")
        self.assertEqual(response["Retry-After"], "3")

    # Scopo: Verifica il caso `test_run_lotto_pipeline_echoes_idempotency_key`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_echoes_idempotency_key(self, mocked_service, _mock_auth):
        mocked_service.return_value = 321
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-abc-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Idempotency-Key"], "idem-abc-123")
        self.assertEqual(response.json()["meta"]["idempotency_key"], "idem-abc-123")

    # Scopo: Verifica il caso `test_run_lotto_pipeline_requires_idempotency_key`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_run_lotto_pipeline_requires_idempotency_key(self, _mock_auth):
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_IDEMPOTENCY_KEY_REQUIRED")

    # Scopo: Verifica il caso `test_run_lotto_pipeline_accepts_null_lotto_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_accepts_null_lotto_id(self, mocked_service, _mock_auth):
        mocked_service.return_value = 777
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"lotto_id": None, "dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-null-lotto-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["lotto_id"], 777)
        mocked_service.assert_called_once()
        self.assertIsNone(mocked_service.call_args.kwargs["lotto_id"])

    # Scopo: Verifica il caso `test_run_lotto_pipeline_converts_zero_optional_ids_to_none`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_converts_zero_optional_ids_to_none(self, mocked_service, _mock_auth):
        mocked_service.return_value = 778
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps(
                {
                    "lotto_id": 0,
                    "tipo_doc_fiscale_id": 0,
                    "utility_id": 0,
                    "billing_account_id": 0,
                    "emittente_soggetto_ruolo_id": 0,
                    "dry_run": True,
                }
            ),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-zero-to-null-1"},
        )
        self.assertEqual(response.status_code, 200)
        mocked_service.assert_called_once()
        kwargs = mocked_service.call_args.kwargs
        self.assertIsNone(kwargs["lotto_id"])
        self.assertIsNone(kwargs["tipo_doc_fiscale_id"])
        self.assertIsNone(kwargs["utility_id"])
        self.assertIsNone(kwargs["billing_account_id"])
        self.assertIsNone(kwargs["emittente_soggetto_ruolo_id"])

    # Scopo: Verifica il caso `test_run_lotto_pipeline_full_payload_new_lotto_massivo_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_full_payload_new_lotto_massivo_ok(self, mocked_service, _mock_auth):
        mocked_service.return_value = 78
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps(
                {
                    "lotto_id": 0,
                    "competenza_mese": "2026-02-18",
                    "tipo_doc_fiscale_id": 1,
                    "utility_id": 2,
                    "billing_account_id": 0,
                    "emittente_soggetto_ruolo_id": 0,
                    "lock_batch_id": None,
                    "meta": {
                        "additionalProp1": "string",
                        "additionalProp2": "string",
                        "additionalProp3": "string",
                    },
                    "dry_run": False,
                    "tipo_lotto": "MASSIVO",
                }
            ),
            content_type="application/json",
            headers={"Idempotency-Key": "lotto2-2026-02-18"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["lotto_id"], 78)
        mocked_service.assert_called_once()
        kwargs = mocked_service.call_args.kwargs
        self.assertIsNone(kwargs["lotto_id"])
        self.assertEqual(kwargs["competenza_mese"].isoformat(), "2026-02-18")
        self.assertEqual(kwargs["tipo_doc_fiscale_id"], 1)
        self.assertEqual(kwargs["utility_id"], 2)
        self.assertIsNone(kwargs["billing_account_id"])
        self.assertIsNone(kwargs["emittente_soggetto_ruolo_id"])
        self.assertEqual(kwargs["tipo_lotto"], "MASSIVO")
        self.assertFalse(kwargs["dry_run"])

    # Scopo: Verifica il caso `test_run_lotto_pipeline_v1_requires_jwt`.
    def test_run_lotto_pipeline_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"tipo_lotto": "MASSIVO"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-v1-missing-auth"},
        )
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica il caso `test_legacy_vendite_path_not_found_when_disabled`.
    def test_legacy_vendite_path_not_found_when_disabled(self):
        response = self.client.post(
            "/api/vendite/pipeline/run/",
            data=json.dumps({"tipo_lotto": "MASSIVO"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-legacy-1"},
        )
        self.assertEqual(response.status_code, 404)

    # Scopo: Verifica il caso `test_run_lotto_pipeline_hides_technical_detail_for_generic_errors`.
    @override_settings(API_EXPOSE_TECHNICAL_DETAILS=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_hides_technical_detail_for_generic_errors(self, mocked_service, _mock_auth):
        mocked_service.side_effect = RuntimeError("CONTEXT: SQL interno sensibile")
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-safe-err-1"},
        )
        self.assertEqual(response.status_code, 500)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_GENERICO")
        self.assertEqual(body["message"], "Errore non gestito.")
        self.assertNotIn("SQL interno", body["detail"])
        self.assertIn("request_id", body["detail"])
        self.assertNotIn("technical_message", body)

    # Scopo: Verifica il caso `test_run_lotto_pipeline_exposes_technical_message_in_debug_mode`.
    @override_settings(API_EXPOSE_TECHNICAL_DETAILS=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_exposes_technical_message_in_debug_mode(self, mocked_service, _mock_auth):
        mocked_service.side_effect = RuntimeError("CONTEXT: SQL interno sensibile")
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-safe-err-2"},
        )
        self.assertEqual(response.status_code, 500)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_GENERICO")
        self.assertEqual(body["message"], "Errore non gestito.")
        self.assertEqual(body["technical_message"], "CONTEXT: SQL interno sensibile")

    # Scopo: Verifica il caso `test_run_lotto_pipeline_replays_completed_response_when_strong_idempotency_enabled`.
    @override_settings(API_STRONG_IDEMPOTENCY_ENABLED=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.endpoint_helpers.IdempotencyStore.claim_or_replay")
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_replays_completed_response_when_strong_idempotency_enabled(
        self,
        mocked_service,
        mocked_claim,
        _mock_auth,
    ):
        mocked_claim.return_value = IdempotencyDecision(
            should_execute=False,
            replay_payload={
                "data": {"lotto_id": 555, "status": "ok"},
                "meta": {"request_id": "00000000-0000-0000-0000-000000000001"},
            },
        )

        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-replay-1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Idempotency-Replayed"], "1")
        self.assertEqual(response.json()["data"]["lotto_id"], 555)
        mocked_service.assert_not_called()

    # Scopo: Verifica il caso `test_run_lotto_pipeline_returns_conflict_when_idempotency_in_progress`.
    @override_settings(API_STRONG_IDEMPOTENCY_ENABLED=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.endpoint_helpers.IdempotencyStore.claim_or_replay")
    @patch("apps.vendite.api.views.run_lotto_pipeline")
    def test_run_lotto_pipeline_returns_conflict_when_idempotency_in_progress(
        self,
        mocked_service,
        mocked_claim,
        _mock_auth,
    ):
        mocked_claim.return_value = IdempotencyDecision(
            should_execute=False,
            in_progress=True,
        )

        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-progress-1"},
        )

        self.assertEqual(response.status_code, 409)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_IDEMPOTENCY_IN_PROGRESS")
        mocked_service.assert_not_called()

    # Scopo: Verifica il caso `test_get_lotto_segnalazioni_summary_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_lotto_segnalazioni_summary")
    def test_get_lotto_segnalazioni_summary_ok(self, mocked_summary, _mock_auth):
        mocked_summary.return_value = {
            "lotto_id": 80,
            "critical_count": 1,
            "warning_count": 2,
            "attention_count": 3,
            "is_error": True,
            "blocks_next_step": True,
            "summary": {
                "fatture_critical_count": 1,
                "fatture_warning_count": 1,
                "lotto_critical_count": 0,
                "lotto_warning_count": 1,
                "lotto_info_count": 3,
            },
        }
        response = self.client.get("/api/v1/vendite/lotti/80/segnalazioni/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["lotto_id"], 80)
        self.assertTrue(data["blocks_next_step"])
        self.assertEqual(data["critical_count"], 1)
        # Il riepilogo CONTA e basta: le righe hanno un endpoint suo
        # (`/segnalazioni/rows/`), cosi' il drawer non si porta dietro l'elenco
        # a ogni apertura per mostrarne un numero.
        # L'utente della richiesta arriva al cancello di perimetro (2026-10-20).
        mocked_summary.assert_called_once_with(lotto_id=80, auth_user_id=None)

    # Scopo: ⭐ L'ELENCO delle segnalazioni sta su una rotta SUA, e i filtri
    #        arrivano dal query string. Presidia anche i due default che non
    #        sono neutri: `solo_attive=True` (una segnalazione ritirata non si
    #        mostra) e `solo_job_corrente=False` (si vede tutto lo storico
    #        finche' qualcuno non chiede l'ultima corsa).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_lotto_segnalazioni")
    def test_get_lotto_segnalazioni_rows_filtri_dal_query_param(self, mocked_rows, _mock_auth):
        mocked_rows.return_value = {"lotto_id": 80, "results": []}
        response = self.client.get(
            "/api/v1/vendite/lotti/80/segnalazioni/rows/?livello=W&origine=LOTTO&page=2&page_size=10"
        )
        self.assertEqual(response.status_code, 200)
        mocked_rows.assert_called_once_with(
            lotto_id=80, auth_user_id=None, livello="W", origine="LOTTO",
            solo_attive=True, solo_job_corrente=False,
            page=2, page_size=10, order_by=None, order_dir="desc",
        )

    # Scopo: Verifica il caso `test_get_lotto_segnalazioni_summary_v1_requires_jwt`.
    def test_get_lotto_segnalazioni_summary_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/lotti/80/segnalazioni/")
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica il caso `test_get_lotto_segnalazioni_summary_rejects_invalid_lotto_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_get_lotto_segnalazioni_summary_rejects_invalid_lotto_id(self, _mock_auth):
        response = self.client.get("/api/v1/vendite/lotti/0/segnalazioni/")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_PIPELINE_VALIDATION")

    # Scopo: Verifica il caso `test_get_lotto_task_runs_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_lotto_task_runs")
    def test_get_lotto_task_runs_ok(self, mocked_task_runs, _mock_auth):
        mocked_task_runs.return_value = {
            "lotto_id": 80,
            "count": 1,
            "task_runs": [
                {
                    "id": 1001,
                    "lotto_id": 80,
                    "pipeline_id": 4,
                    "stato_doc_fiscale_id": 8,
                    "task_code": "numera_fatture",
                    "fase": "Numerazione fatture",
                    "tentativo": 1,
                    "task_stato": "COMPLETATO",
                    "started_at": "2026-02-19T10:00:00+01:00",
                    "ended_at": "2026-02-19T10:00:02+01:00",
                    "error_code": None,
                    "error_message": None,
                    "meta": {"rollback": False},
                }
            ],
        }
        response = self.client.get("/api/v1/vendite/lotti/80/task-runs/?limit=50")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["lotto_id"], 80)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["task_runs"][0]["task_code"], "numera_fatture")
        # ⚠️ `limit` resta il nome che il client manda e arriva come `page_size`:
        # l'endpoint e' diventato paginato (BE-2) senza rompere il chiamante.
        # ⭐ E i due filtri del `20260824-11` arrivano SPENTI quando non si
        #    chiedono: nessun default nasconde righe: chi chiama senza vede
        #    quello che vedeva prima.
        mocked_task_runs.assert_called_once_with(
            lotto_id=80, auth_user_id=None, page_size=50, offset=0, order_by=None, order_dir="desc",
            task_stato=None, solo_giro_corrente=False,
        )

    # Scopo: il filtro multi-valore `task_stato` arriva al service come LISTA,
    #        normalizzato a maiuscolo, sia ripetuto sia separato da virgole — e
    #        `solo_giro_corrente` come booleano.
    # ⚠️ Il presidio sta qui e non sul vocabolario: quale stato sia ammesso lo
    #    decide la funzione DB, e ricopiarlo nel backend sarebbe la seconda
    #    verita' sullo stesso elenco.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_lotto_task_runs")
    def test_get_lotto_task_runs_filtri(self, mocked_task_runs, _mock_auth):
        mocked_task_runs.return_value = {
            "lotto_id": 80, "count": 0, "esclusi_count": 90, "task_runs": [], "results": [],
        }

        self.client.get(
            "/api/v1/vendite/lotti/80/task-runs/"
            "?task_stato=errore,completato&solo_giro_corrente=true"
        )
        chiamata = mocked_task_runs.call_args.kwargs
        self.assertEqual(chiamata["task_stato"], ["ERRORE", "COMPLETATO"])
        self.assertTrue(chiamata["solo_giro_corrente"])

        mocked_task_runs.reset_mock()
        self.client.get(
            "/api/v1/vendite/lotti/80/task-runs/?task_stato=ERRORE&task_stato=ANNULLATO"
        )
        self.assertEqual(
            mocked_task_runs.call_args.kwargs["task_stato"], ["ERRORE", "ANNULLATO"]
        )

    # Scopo: un `task_stato` vuoto NON e' un filtro che non seleziona niente:
    #        e' l'assenza di filtro. ⛔ La distinzione conta perche' una lista
    #        vuota e una lista non filtrata direbbero la stessa cosa a video.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_lotto_task_runs")
    def test_get_lotto_task_runs_stato_vuoto_non_filtra(self, mocked_task_runs, _mock_auth):
        mocked_task_runs.return_value = {
            "lotto_id": 80, "count": 0, "esclusi_count": 0, "task_runs": [], "results": [],
        }

        self.client.get("/api/v1/vendite/lotti/80/task-runs/?task_stato=%20,")
        self.assertIsNone(mocked_task_runs.call_args.kwargs["task_stato"])

    # Scopo: Verifica il caso `test_get_lotto_task_runs_v1_requires_jwt`.
    def test_get_lotto_task_runs_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/lotti/80/task-runs/")
        self.assertEqual(response.status_code, 401)

    # Scopo: Verifica il caso `test_get_lotto_task_runs_rejects_invalid_lotto_id`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_get_lotto_task_runs_rejects_invalid_lotto_id(self, _mock_auth):
        response = self.client.get("/api/v1/vendite/lotti/0/task-runs/")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_PIPELINE_VALIDATION")
