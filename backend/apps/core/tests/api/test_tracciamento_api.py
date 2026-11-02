# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari endpoint API tracciamento processi e job.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) TestApiAuditLog.test_audit_log_200 — risultati paginati
2) TestApiAuditLog.test_audit_log_invalid_status — errore validazione
3) TestApiDominiTask.test_domini_task_200 — lista domini
4) TestApiTaskRegistry.test_task_registry_200 — lista task
5) TestApiTaskImplementations.test_task_implementations_200 — lista implementazioni
6) TestApiJobRuns.test_job_runs_200 — lista esecuzioni
7) TestApiJobSummary.test_job_summary_200 — riepilogo job
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import RequestFactory


def _make_get_request(path: str = "/", query_params: dict | None = None):
    # Scopo: Crea una request GET con DRF wrapper per test.
    from rest_framework.request import Request
    factory = RequestFactory()
    url = path
    if query_params:
        qs = "&".join(f"{k}={v}" for k, v in query_params.items())
        url = f"{path}?{qs}"
    django_request = factory.get(url)
    django_request.user = MagicMock(is_authenticated=True)
    return Request(django_request)


class TestApiAuditLog(TestCase):

    # Scopo: Verifica risposta 200 con dati paginati.
    @patch("apps.core.api.views_tracciamento.fn_list_audit_logs")
    def test_audit_log_200(self, mock_fn):
        from apps.core.api.views_tracciamento import ApiAuditLog

        mock_fn.return_value = {
            "count": 1, "page": 1, "page_size": 50, "total_pages": 1,
            "results": [{"id": 1, "status": "SUCCESS"}],
        }
        view = ApiAuditLog()
        request = _make_get_request("/api/v1/core/tracciamento/audit-log/")
        response = view.get(request)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body["data"]["count"], 1)

    # Scopo: Verifica propagazione errore con status non valido.
    @patch("apps.core.api.views_tracciamento.fn_list_audit_logs")
    def test_audit_log_invalid_status(self, mock_fn):
        from apps.core.services.service_errors import ServiceError
        from apps.core.api.views_tracciamento import ApiAuditLog

        mock_fn.side_effect = ServiceError(
            code="E_CORE_VALIDATION", message="status non valido",
        )
        view = ApiAuditLog()
        request = _make_get_request(
            "/api/v1/core/tracciamento/audit-log/",
            query_params={"status": "INVALIDO"},
        )
        with self.assertRaises(ServiceError):
            view.get(request)


class TestApiDominiTask(TestCase):

    # Scopo: Verifica risposta 200 lista domini.
    @patch("apps.core.api.views_tracciamento.fn_list_domini_task")
    def test_domini_task_200(self, mock_fn):
        from apps.core.api.views_tracciamento import ApiDominiTask

        mock_fn.return_value = {
            "count": 2, "page": 1, "page_size": 50, "total_pages": 1,
            "results": [
                {"id": 1, "codice": "FATTURAZIONE"},
                {"id": 2, "codice": "ATTIVITA_FATTURABILI"},
            ],
        }
        view = ApiDominiTask()
        request = _make_get_request("/api/v1/core/tracciamento/domini-task/")
        response = view.get(request)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body["data"]["count"], 2)


class TestApiTaskRegistry(TestCase):

    # Scopo: Verifica risposta 200 lista task.
    @patch("apps.core.api.views_tracciamento.fn_list_task_registry")
    def test_task_registry_200(self, mock_fn):
        from apps.core.api.views_tracciamento import ApiTaskRegistry

        mock_fn.return_value = {
            "count": 1, "page": 1, "page_size": 100, "total_pages": 1,
            "results": [{"id": 1, "task_code": "select_attivita"}],
        }
        view = ApiTaskRegistry()
        request = _make_get_request(
            "/api/v1/core/tracciamento/task-registry/",
            query_params={"dominio": "FATTURAZIONE"},
        )
        response = view.get(request)
        self.assertEqual(response.status_code, 200)


class TestApiTaskImplementations(TestCase):

    # Scopo: Verifica risposta 200 lista implementazioni.
    @patch("apps.core.api.views_tracciamento.fn_list_task_implementations")
    def test_task_implementations_200(self, mock_fn):
        from apps.core.api.views_tracciamento import ApiTaskImplementations

        mock_fn.return_value = {
            "count": 1, "page": 1, "page_size": 100, "total_pages": 1,
            "results": [{"id": 1, "handler_code": "select_attivita_default"}],
        }
        view = ApiTaskImplementations()
        request = _make_get_request("/api/v1/core/tracciamento/task-implementations/")
        response = view.get(request)
        self.assertEqual(response.status_code, 200)


class TestApiJobRuns(TestCase):

    # Scopo: Verifica risposta 200 lista esecuzioni job.
    @patch("apps.core.api.views_tracciamento.fn_list_job_runs")
    def test_job_runs_200(self, mock_fn):
        from apps.core.api.views_tracciamento import ApiJobRuns

        mock_fn.return_value = {
            "count": 1, "page": 1, "page_size": 50, "total_pages": 1,
            "results": [{"id": 1, "jobname": "cleanup_weekly", "ok": True}],
        }
        view = ApiJobRuns()
        request = _make_get_request("/api/v1/core/tracciamento/job-runs/")
        response = view.get(request)
        self.assertEqual(response.status_code, 200)


class TestApiJobSummary(TestCase):

    # Scopo: Verifica risposta 200 riepilogo job.
    @patch("apps.core.api.views_tracciamento.fn_list_job_summary")
    def test_job_summary_200(self, mock_fn):
        from apps.core.api.views_tracciamento import ApiJobSummary

        mock_fn.return_value = {
            "count": 1, "page": 1, "page_size": 50, "total_pages": 1,
            "results": [{"jobname": "cleanup_weekly", "total_runs": 5}],
        }
        view = ApiJobSummary()
        request = _make_get_request("/api/v1/core/tracciamento/job-summary/")
        response = view.get(request)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body["data"]["results"][0]["total_runs"], 5)
