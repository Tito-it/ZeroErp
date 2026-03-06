# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per i repository tracciamento (dbops task registry,
#        audit log, maintenance job_run_log).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) TestDbopsAuditLog.test_list_audit_logs_ok — righe audit con filtri
2) TestDbopsAuditLog.test_list_audit_logs_empty — nessun risultato
3) TestDbopsDominiTask.test_list_domini_task_ok — domini con conteggio
4) TestDbopsDominiTask.test_list_domini_task_empty — nessun dominio
5) TestDbopsTaskRegistry.test_list_task_registry_ok — task con dominio
6) TestDbopsTaskImpl.test_list_task_implementations_ok — implementazioni
7) TestMaintenanceJobRuns.test_list_job_runs_ok — esecuzioni job
8) TestMaintenanceJobRuns.test_list_job_runs_empty — nessuna esecuzione
9) TestMaintenanceJobSummary.test_list_job_summary_ok — riepilogo
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch


def _mock_cursor(mock_conn, rows):
    # Scopo: Configura mock cursor con righe predefinite.
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_cursor


# ------------------------------------------------------------------
# Audit Log
# ------------------------------------------------------------------

class TestDbopsAuditLog(TestCase):

    # Scopo: Verifica parsing righe audit_log.
    @patch("apps.core.db.dbops_repository.connection")
    def test_list_audit_logs_ok(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [
            (1, "fn_run_automations", "zeroerp", "2026-03-01 10:00:00+00",
             "SUCCESS", "done", 120, "abc-uuid", "FULL", "STORICO",
             False, 42, None, None, 1),
        ])
        repo = DbopsRepository()
        results, count = repo.list_audit_logs(limit=50, offset=0)
        self.assertEqual(count, 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["function_name"], "fn_run_automations")
        self.assertEqual(results[0]["status"], "SUCCESS")

    # Scopo: Verifica lista vuota.
    @patch("apps.core.db.dbops_repository.connection")
    def test_list_audit_logs_empty(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [])
        repo = DbopsRepository()
        results, count = repo.list_audit_logs(limit=50, offset=0)
        self.assertEqual(count, 0)
        self.assertEqual(results, [])


# ------------------------------------------------------------------
# Domini Task
# ------------------------------------------------------------------

class TestDbopsDominiTask(TestCase):

    # Scopo: Verifica parsing righe domini_task.
    @patch("apps.core.db.dbops_repository.connection")
    def test_list_domini_task_ok(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [
            (1, "FATTURAZIONE", "Pipeline fatturazione", True, 2),
            (2, "ATTIVITA_FATTURABILI", "Pipeline attivita", True, 2),
        ])
        repo = DbopsRepository()
        results, count = repo.list_domini_task(limit=50, offset=0)
        self.assertEqual(count, 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["codice"], "FATTURAZIONE")

    # Scopo: Verifica lista vuota.
    @patch("apps.core.db.dbops_repository.connection")
    def test_list_domini_task_empty(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [])
        repo = DbopsRepository()
        results, count = repo.list_domini_task(limit=50, offset=0)
        self.assertEqual(count, 0)


# ------------------------------------------------------------------
# Task Registry
# ------------------------------------------------------------------

class TestDbopsTaskRegistry(TestCase):

    # Scopo: Verifica parsing righe task registry con join dominio.
    @patch("apps.core.db.dbops_repository.connection")
    def test_list_task_registry_ok(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [
            (1, 1, "FATTURAZIONE", "select_attivita",
             "Seleziona e blocca attivita", True, 1),
        ])
        repo = DbopsRepository()
        results, count = repo.list_task_registry(
            dominio_codice="FATTURAZIONE", limit=100, offset=0,
        )
        self.assertEqual(count, 1)
        self.assertEqual(results[0]["task_code"], "select_attivita")
        self.assertEqual(results[0]["dominio_codice"], "FATTURAZIONE")


# ------------------------------------------------------------------
# Task Implementations
# ------------------------------------------------------------------

class TestDbopsTaskImpl(TestCase):

    # Scopo: Verifica parsing righe implementazioni.
    @patch("apps.core.db.dbops_repository.connection")
    def test_list_task_implementations_ok(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [
            (1, 1, "select_attivita", "default",
             "select_attivita_default", True, True, 1),
        ])
        repo = DbopsRepository()
        results, count = repo.list_task_implementations(
            task_code="select_attivita", limit=100, offset=0,
        )
        self.assertEqual(count, 1)
        self.assertEqual(results[0]["handler_code"], "select_attivita_default")
        self.assertTrue(results[0]["is_default"])


# ------------------------------------------------------------------
# Maintenance Job Run Log
# ------------------------------------------------------------------

class TestMaintenanceJobRuns(TestCase):

    # Scopo: Verifica parsing righe job_run_log.
    @patch("apps.core.db.maintenance_repository.connection")
    def test_list_job_runs_ok(self, mock_conn):
        from apps.core.db.maintenance_repository import MaintenanceRepository

        _mock_cursor(mock_conn, [
            (1, "apply_storicizza_weekly", "step_1",
             "2026-03-01 10:00:00+00", "2026-03-01 10:00:05+00",
             True, 42, "done", None, None,
             "10.0.0.1", "uuid-abc", 1),
        ])
        repo = MaintenanceRepository()
        results, count = repo.list_job_runs(limit=50, offset=0)
        self.assertEqual(count, 1)
        self.assertEqual(results[0]["jobname"], "apply_storicizza_weekly")
        self.assertTrue(results[0]["ok"])

    # Scopo: Verifica lista vuota.
    @patch("apps.core.db.maintenance_repository.connection")
    def test_list_job_runs_empty(self, mock_conn):
        from apps.core.db.maintenance_repository import MaintenanceRepository

        _mock_cursor(mock_conn, [])
        repo = MaintenanceRepository()
        results, count = repo.list_job_runs(limit=50, offset=0)
        self.assertEqual(count, 0)
        self.assertEqual(results, [])


class TestMaintenanceJobSummary(TestCase):

    # Scopo: Verifica riepilogo job.
    @patch("apps.core.db.maintenance_repository.connection")
    def test_list_job_summary_ok(self, mock_conn):
        from apps.core.db.maintenance_repository import MaintenanceRepository

        _mock_cursor(mock_conn, [
            ("apply_storicizza_weekly", 10, 9, 1,
             "2026-03-01 10:00:00+00", True, 1),
        ])
        repo = MaintenanceRepository()
        results, count = repo.list_job_summary(limit=50, offset=0)
        self.assertEqual(count, 1)
        self.assertEqual(results[0]["total_runs"], 10)
        self.assertEqual(results[0]["ok_count"], 9)
