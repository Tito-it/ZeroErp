# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

# ⚠️ Dal 2026-09-28 queste liste passano da `fetch_paged_with_total`: la query
#    parte dal BB, quindi si sostituisce la `connection` del BB e non quella del
#    repository (che non la usa piu'), e il cursore porta i NOMI delle colonne,
#    come il DB vero: il BB legge le righe per nome.
_CONN = "apps.core.db._helpers.connection"

_COLONNE = {
    "audit_logs": ("id", "function_name", "executed_by", "executed_at", "status",
                   "message", "duration_ms", "tx_id", "exec_mode", "rule_type",
                   "dry_run", "rows_affected", "params", "result", "total_count"),
    "domini": ("id", "codice", "descrizione", "attivo", "total_count"),
    "registry": ("id", "dominio_id", "dominio_codice", "task_code", "descrizione",
                 "attivo", "total_count"),
    "impl": ("id", "task_registry_id", "task_code", "implementation_key",
             "handler_code", "is_default", "attivo", "total_count"),
    "job_runs": ("id", "jobname", "stepname", "started_at", "ended_at", "ok",
                 "rows_affected", "message", "error_code", "error_detail",
                 "agent_host", "run_uuid", "saltata", "total_count"),
    "job_summary": ("jobname", "total_runs", "ok_count", "fail_count",
                    "saltate_count", "last_run_at", "in_corso", "started_at", "ended_at", "ok",
                    "total_count"),
}


def _mock_cursor(mock_conn, rows, colonne=()):
    # Scopo: Configura mock cursor con righe predefinite e i nomi di colonna.
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows
    mock_cursor.description = [SimpleNamespace(name=c) for c in colonne]
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_cursor


# ------------------------------------------------------------------
# Audit Log
# ------------------------------------------------------------------

class TestDbopsAuditLog(TestCase):

    # Scopo: Verifica parsing righe audit_log.
    @patch(_CONN)
    def test_list_audit_logs_ok(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [
            (1, "fn_run_automations", "zeroerp", "2026-03-01 10:00:00+00",
             "SUCCESS", "done", 120, "abc-uuid", "FULL", "STORICO",
             False, 42, None, None, 1),
        ], _COLONNE["audit_logs"])
        repo = DbopsRepository()
        results, count = repo.list_audit_logs(limit=50, offset=0)
        self.assertEqual(count, 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["function_name"], "fn_run_automations")
        self.assertEqual(results[0]["status"], "SUCCESS")

    # Scopo: Verifica lista vuota.
    @patch(_CONN)
    def test_list_audit_logs_empty(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [], _COLONNE["audit_logs"])
        repo = DbopsRepository()
        results, count = repo.list_audit_logs(limit=50, offset=0)
        self.assertEqual(count, 0)
        self.assertEqual(results, [])


# ------------------------------------------------------------------
# Domini Task
# ------------------------------------------------------------------

class TestDbopsDominiTask(TestCase):

    # Scopo: Verifica parsing righe domini_task.
    @patch(_CONN)
    def test_list_domini_task_ok(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [
            (1, "FATTURAZIONE", "Pipeline fatturazione", True, 2),
            (2, "ATTIVITA_FATTURABILI", "Pipeline attivita", True, 2),
        ], _COLONNE["domini"])
        repo = DbopsRepository()
        results, count = repo.list_domini_task(limit=50, offset=0)
        self.assertEqual(count, 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["codice"], "FATTURAZIONE")

    # Scopo: Verifica lista vuota.
    @patch(_CONN)
    def test_list_domini_task_empty(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [], _COLONNE["domini"])
        repo = DbopsRepository()
        results, count = repo.list_domini_task(limit=50, offset=0)
        self.assertEqual(count, 0)


# ------------------------------------------------------------------
# Task Registry
# ------------------------------------------------------------------

class TestDbopsTaskRegistry(TestCase):

    # Scopo: Verifica parsing righe task registry con join dominio.
    @patch(_CONN)
    def test_list_task_registry_ok(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [
            (1, 1, "FATTURAZIONE", "select_attivita",
             "Seleziona e blocca attivita", True, 1),
        ], _COLONNE["registry"])
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
    @patch(_CONN)
    def test_list_task_implementations_ok(self, mock_conn):
        from apps.core.db.dbops_repository import DbopsRepository

        _mock_cursor(mock_conn, [
            (1, 1, "select_attivita", "default",
             "select_attivita_default", True, True, 1),
        ], _COLONNE["impl"])
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
    @patch(_CONN)
    def test_list_job_runs_ok(self, mock_conn):
        from apps.core.db.maintenance_repository import MaintenanceRepository

        _mock_cursor(mock_conn, [
            (1, "apply_storicizza_weekly", "step_1",
             "2026-03-01 10:00:00+00", "2026-03-01 10:00:05+00",
             True, 42, "done", None, None,
             "10.0.0.1", "uuid-abc", False, 1),
        ], _COLONNE["job_runs"])
        repo = MaintenanceRepository()
        results, count = repo.list_job_runs(limit=50, offset=0)
        self.assertEqual(count, 1)
        self.assertEqual(results[0]["jobname"], "apply_storicizza_weekly")
        self.assertTrue(results[0]["ok"])
        self.assertFalse(results[0]["saltata"])

    # Scopo: Verifica lista vuota.
    @patch(_CONN)
    def test_list_job_runs_empty(self, mock_conn):
        from apps.core.db.maintenance_repository import MaintenanceRepository

        _mock_cursor(mock_conn, [], _COLONNE["job_runs"])
        repo = MaintenanceRepository()
        results, count = repo.list_job_runs(limit=50, offset=0)
        self.assertEqual(count, 0)
        self.assertEqual(results, [])


class TestMaintenanceJobSummary(TestCase):

    # Scopo: Verifica riepilogo job.
    @patch(_CONN)
    def test_list_job_summary_ok(self, mock_conn):
        from apps.core.db.maintenance_repository import MaintenanceRepository

        avvio = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
        fine = datetime(2026, 3, 1, 10, 0, 5, tzinfo=UTC)
        _mock_cursor(mock_conn, [
            # jobname, total, ok, fail, saltate, last_run_at::text, in_corso,
            # conclusa.started_at, conclusa.ended_at, conclusa.ok, total_count
            ("apply_storicizza_weekly", 10, 9, 1, 2,
             "2026-03-01 10:00:00+00", False, avvio, fine, True, 1),
        ], _COLONNE["job_summary"])
        repo = MaintenanceRepository()
        results, count = repo.list_job_summary(limit=50, offset=0)
        self.assertEqual(count, 1)
        self.assertEqual(results[0]["total_runs"], 10)
        self.assertEqual(results[0]["ok_count"], 9)
        self.assertEqual(results[0]["saltate_count"], 2)
        # La forma delle corse (2026-09-14): `in_corso` dalla riga piu'
        # recente, l'ultima conclusa con data ED esito insieme, in ISO-8601.
        self.assertFalse(results[0]["in_corso"])
        self.assertEqual(
            results[0]["ultima_conclusa"],
            {"started_at": avvio.isoformat(), "ended_at": fine.isoformat(), "ok": True},
        )

    # Scopo: senza filtri nessuna condizione aggiunta e soli limit/offset come
    #        parametri (comportamento storico invariato). NB: non si asserisce
    #        l'assenza di "WHERE" — gli aggregati contengono sempre
    #        `FILTER (WHERE ok = ...)`; si verificano le condizioni opzionali.
    @patch(_CONN)
    def test_list_job_summary_senza_filtri_nessuna_condizione(self, mock_conn):
        from apps.core.db.maintenance_repository import MaintenanceRepository

        _mock_cursor(mock_conn, [], _COLONNE["job_summary"])
        MaintenanceRepository().list_job_summary(limit=50, offset=0)
        sql, params = mock_conn.cursor.return_value.__enter__.return_value \
            .execute.call_args[0]
        self.assertNotIn("jobname LIKE", sql)
        self.assertNotIn("meta ->>", sql)
        self.assertEqual(params, [50, 0])
        # ⚠️ E senza condizioni la CTE `conclusa` deve restare un `WHERE` valido:
        #    e' l'unica delle tre con una condizione propria.
        self.assertIn("WHERE ended_at IS NOT NULL", sql)
        self.assertNotIn("WHERE  AND", sql)

    # Scopo: filtri opzionali → WHERE su jobname (LIKE prefisso) e sul mese
    #        ATTRIBUITO al run, con i VALORI parametrizzati (mai interpolati).
    @patch(_CONN)
    def test_list_job_summary_filtra_prefisso_e_mese(self, mock_conn):
        from apps.core.db.maintenance_repository import MaintenanceRepository

        _mock_cursor(mock_conn, [], _COLONNE["job_summary"])
        MaintenanceRepository().list_job_summary(
            limit=10, offset=0,
            jobname_prefix="run_fatturazione_batch",
            meta_month_equals=("competenza", "2026-07-01"),
        )
        sql, params = mock_conn.cursor.return_value.__enter__.return_value \
            .execute.call_args[0]
        self.assertIn("jobname LIKE %s", sql)
        # Attribuzione: mese DICHIARATO nel meta, con ripiego sul mese di
        # esecuzione — senza il COALESCE i run che non scrivono la chiave (tutti
        # quelli storici) non matcherebbero mai alcun mese.
        self.assertIn("meta ->> 'competenza'", sql)
        # ... e il mese di esecuzione e' quello dell'AZIENDA (BB DB), non della sessione.
        self.assertIn("date_trunc('month', script.fn_giorno_operativo(started_at)::timestamp)", sql)
        self.assertIn("COALESCE", sql)
        # Il filtro è PRIMA del GROUP BY: i conteggi sono relativi ai soli run
        # che matchano, non al totale del job.
        self.assertLess(sql.index("WHERE"), sql.index("GROUP BY"))
        # ⚠️ Le condizioni compaiono TRE volte (summary, recente, conclusa) e i
        #    valori seguono, nello stesso ordine, prima di limit/offset: un
        #    valore in meno qui non fallisce — filtra una CTE sulla cosa
        #    sbagliata e la riga cuce corse di job diversi.
        self.assertEqual(sql.count("jobname LIKE %s"), 3)
        self.assertEqual(
            params,
            ["run_fatturazione_batch%", "2026-07-01"] * 3 + [10, 0],
        )

    # Scopo: la CHIAVE di meta_month_equals finisce nell'SQL come letterale (non
    #        parametrizzabile): una chiave non alfanumerica va rifiutata, non
    #        interpolata. Guard anti-injection sul solo punto non parametrizzato.
    @patch(_CONN)
    def test_list_job_summary_meta_chiave_non_valida_raises(self, mock_conn):
        from apps.core.db.maintenance_repository import MaintenanceRepository

        _mock_cursor(mock_conn, [], _COLONNE["job_summary"])
        with self.assertRaises(ValueError):
            MaintenanceRepository().list_job_summary(
                meta_month_equals=("x' OR '1'='1", "2026-07-01"),
            )
