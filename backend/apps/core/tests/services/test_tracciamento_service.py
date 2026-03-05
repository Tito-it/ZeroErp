# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per tracciamento_service (facade audit log, task registry, job runs).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) TestListAuditLogs.test_list_audit_logs_ok — risultati paginati
2) TestListAuditLogs.test_list_audit_logs_empty — nessun risultato
3) TestListAuditLogs.test_list_audit_logs_invalid_status — solleva ServiceError
4) TestListAuditLogs.test_list_audit_logs_invalid_page — solleva ServiceError
5) TestListDominiTask.test_list_domini_task_ok — risultati paginati
6) TestListDominiTask.test_list_domini_task_empty — nessun risultato
7) TestListTaskRegistry.test_list_task_registry_ok — risultati con dominio
8) TestListTaskImplementations.test_list_task_implementations_ok — impl con handler
9) TestListJobRuns.test_list_job_runs_ok — esecuzioni job paginati
10) TestListJobRuns.test_list_job_runs_empty — nessun risultato
11) TestListJobSummary.test_list_job_summary_ok — riepilogo job
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError


class TestListAuditLogs(TestCase):

    # Scopo: Verifica che list_audit_logs restituisca risultati paginati.
    @patch("apps.core.services.tracciamento_service.DbopsRepository")
    def test_list_audit_logs_ok(self, MockRepo):
        from apps.core.services.tracciamento_service import fn_list_audit_logs

        mock_repo = MockRepo.return_value
        mock_repo.list_audit_logs.return_value = (
            [{"id": 1, "function_name": "test", "status": "SUCCESS"}],
            1,
        )
        result = fn_list_audit_logs(page=1, page_size=50)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["page"], 1)
        self.assertEqual(len(result["results"]), 1)
        mock_repo.list_audit_logs.assert_called_once()

    # Scopo: Verifica lista vuota.
    @patch("apps.core.services.tracciamento_service.DbopsRepository")
    def test_list_audit_logs_empty(self, MockRepo):
        from apps.core.services.tracciamento_service import fn_list_audit_logs

        mock_repo = MockRepo.return_value
        mock_repo.list_audit_logs.return_value = ([], 0)
        result = fn_list_audit_logs(page=1, page_size=50)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["results"], [])

    # Scopo: Status non valido solleva ServiceError.
    def test_list_audit_logs_invalid_status(self):
        from apps.core.services.tracciamento_service import fn_list_audit_logs

        with self.assertRaises(ServiceError) as ctx:
            fn_list_audit_logs(status="INVALIDO")
        self.assertEqual(ctx.exception.code, "E_CORE_VALIDATION")

    # Scopo: Page < 1 solleva ServiceError.
    def test_list_audit_logs_invalid_page(self):
        from apps.core.services.tracciamento_service import fn_list_audit_logs

        with self.assertRaises(ServiceError) as ctx:
            fn_list_audit_logs(page=0)
        self.assertEqual(ctx.exception.code, "E_CORE_VALIDATION")


class TestListDominiTask(TestCase):

    # Scopo: Verifica lista domini task paginata.
    @patch("apps.core.services.tracciamento_service.DbopsRepository")
    def test_list_domini_task_ok(self, MockRepo):
        from apps.core.services.tracciamento_service import fn_list_domini_task

        mock_repo = MockRepo.return_value
        mock_repo.list_domini_task.return_value = (
            [{"id": 1, "codice": "FATTURAZIONE", "descrizione": "Pipeline fatturazione", "attivo": True}],
            1,
        )
        result = fn_list_domini_task(page=1, page_size=50)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["codice"], "FATTURAZIONE")

    # Scopo: Verifica lista vuota.
    @patch("apps.core.services.tracciamento_service.DbopsRepository")
    def test_list_domini_task_empty(self, MockRepo):
        from apps.core.services.tracciamento_service import fn_list_domini_task

        mock_repo = MockRepo.return_value
        mock_repo.list_domini_task.return_value = ([], 0)
        result = fn_list_domini_task(page=1, page_size=50)
        self.assertEqual(result["count"], 0)


class TestListTaskRegistry(TestCase):

    # Scopo: Verifica lista task registry con dominio.
    @patch("apps.core.services.tracciamento_service.DbopsRepository")
    def test_list_task_registry_ok(self, MockRepo):
        from apps.core.services.tracciamento_service import fn_list_task_registry

        mock_repo = MockRepo.return_value
        mock_repo.list_task_registry.return_value = (
            [{"id": 1, "dominio_id": 1, "dominio_codice": "FATTURAZIONE",
              "task_code": "select_attivita", "descrizione": "Seleziona attivita", "attivo": True}],
            1,
        )
        result = fn_list_task_registry(dominio_codice="FATTURAZIONE", page=1, page_size=100)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["task_code"], "select_attivita")


class TestListTaskImplementations(TestCase):

    # Scopo: Verifica lista implementazioni task.
    @patch("apps.core.services.tracciamento_service.DbopsRepository")
    def test_list_task_implementations_ok(self, MockRepo):
        from apps.core.services.tracciamento_service import fn_list_task_implementations

        mock_repo = MockRepo.return_value
        mock_repo.list_task_implementations.return_value = (
            [{"id": 1, "task_registry_id": 1, "task_code": "select_attivita",
              "implementation_key": "default", "handler_code": "select_attivita_default",
              "is_default": True, "attivo": True}],
            1,
        )
        result = fn_list_task_implementations(task_code="select_attivita", page=1, page_size=100)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["handler_code"], "select_attivita_default")


class TestListJobRuns(TestCase):

    # Scopo: Verifica lista job runs paginata.
    @patch("apps.core.services.tracciamento_service.MaintenanceRepository")
    def test_list_job_runs_ok(self, MockRepo):
        from apps.core.services.tracciamento_service import fn_list_job_runs

        mock_repo = MockRepo.return_value
        mock_repo.list_job_runs.return_value = (
            [{"id": 1, "jobname": "apply_storicizza_weekly", "ok": True,
              "started_at": "2026-03-01T10:00:00+00:00"}],
            1,
        )
        result = fn_list_job_runs(page=1, page_size=50)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["jobname"], "apply_storicizza_weekly")

    # Scopo: Verifica lista vuota.
    @patch("apps.core.services.tracciamento_service.MaintenanceRepository")
    def test_list_job_runs_empty(self, MockRepo):
        from apps.core.services.tracciamento_service import fn_list_job_runs

        mock_repo = MockRepo.return_value
        mock_repo.list_job_runs.return_value = ([], 0)
        result = fn_list_job_runs(page=1, page_size=50)
        self.assertEqual(result["count"], 0)


class TestListJobSummary(TestCase):

    # Scopo: Verifica riepilogo job.
    @patch("apps.core.services.tracciamento_service.MaintenanceRepository")
    def test_list_job_summary_ok(self, MockRepo):
        from apps.core.services.tracciamento_service import fn_list_job_summary

        mock_repo = MockRepo.return_value
        mock_repo.list_job_summary.return_value = (
            [{"jobname": "apply_storicizza_weekly", "total_runs": 10,
              "ok_count": 9, "fail_count": 1,
              "last_run_at": "2026-03-01T10:00:00+00:00", "last_ok": True}],
            1,
        )
        result = fn_list_job_summary(page=1, page_size=50)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["total_runs"], 10)
