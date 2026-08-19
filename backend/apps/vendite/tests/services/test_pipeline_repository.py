# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari repository pipeline vendite.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) VenditePipelineRepositoryUnitTests.test_get_step_processes_returns_list_from_jsonb_list
2) VenditePipelineRepositoryUnitTests.test_get_step_processes_decodes_jsonb_string_list
3) VenditePipelineRepositoryUnitTests.test_get_step_processes_returns_empty_on_invalid_json
4) VenditePipelineRepositoryUnitTests.test_run_prepare_sdi_payload_lotto_task_maps_rows
5) VenditePipelineRepositoryUnitTests.test_run_prepare_sdi_payload_lotto_task_returns_empty_list
6) VenditePipelineRepositoryUnitTests.test_log_fattura_inserts_with_explicit_critical
7) VenditePipelineRepositoryUnitTests.test_log_fatture_lotto_sets_critical_from_status
8) VenditePipelineRepositoryUnitTests.test_is_lotto_in_errore_returns_true_when_stato_is_errore
9) VenditePipelineRepositoryUnitTests.test_is_lotto_in_errore_returns_false_when_lotto_not_found
10) VenditePipelineRepositoryUnitTests.test_get_lotto_segnalazioni_summary_maps_counts
11) VenditePipelineRepositoryUnitTests.test_get_pipeline_id_for_step_returns_id_when_found
12) VenditePipelineRepositoryUnitTests.test_get_pipeline_id_for_step_returns_none_when_not_found
13) VenditePipelineRepositoryUnitTests.test_task_policy_exists_returns_true_when_policy_active
14) VenditePipelineRepositoryUnitTests.test_task_policy_exists_returns_false_when_no_policy
15) VenditePipelineRepositoryUnitTests.test_resolve_lotto_task_execution_mode_maps_row
16) VenditePipelineRepositoryUnitTests.test_resolve_lotto_task_execution_mode_decodes_meta_strings
17) VenditePipelineRepositoryUnitTests.test_start_lotto_task_run_returns_task_run_result
18) VenditePipelineRepositoryUnitTests.test_complete_lotto_task_run_calls_sql_function
19) VenditePipelineRepositoryUnitTests.test_fail_lotto_task_run_calls_sql_function_with_error_params
20) VenditePipelineRepositoryUnitTests.test_set_lotto_job_stato_updates_only_stato_lotto
21) VenditePipelineRepositoryUnitTests.test_set_lotto_job_stato_rejects_invalid_target_state
22) VenditePipelineRepositoryUnitTests.test_set_lotto_job_stato_rejects_invalid_transition
23) VenditePipelineRepositoryUnitTests.test_list_lotto_task_runs_maps_rows
24) VenditePipelineRepositoryUnitTests.test_popola_fatture_rettifiche_chiama_la_fn_e_ritorna_le_coppie
25) VenditePipelineRepositoryUnitTests.test_popola_fatture_rettifiche_casta_id_a_intero
"""

from unittest.mock import MagicMock
from unittest.mock import patch
from unittest import TestCase
from datetime import date
from decimal import Decimal

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.pipeline_repository import TaskExecutionMode, TaskRunResult, VenditePipelineRepository


class VenditePipelineRepositoryUnitTests(TestCase):
    # Scopo: Verifica il caso `test_get_step_processes_returns_list_from_jsonb_list`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_step_processes_returns_list_from_jsonb_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ([{"task": "select_attivita"}],)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        processi = repo.get_step_processes(
            1,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )

        self.assertEqual(processi, [{"task": "select_attivita"}])

    # Scopo: Verifica il caso `test_get_step_processes_decodes_jsonb_string_list`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_step_processes_decodes_jsonb_string_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ('[{"task":"generate_fatture_righe"}]',)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        processi = repo.get_step_processes(
            1,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )

        self.assertEqual(processi, [{"task": "generate_fatture_righe"}])

    # Scopo: Verifica il caso `test_get_step_processes_returns_empty_on_invalid_json`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_step_processes_returns_empty_on_invalid_json(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ("not-a-json",)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        processi = repo.get_step_processes(
            1,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )

        self.assertEqual(processi, [])

    # Scopo: Verifica il caso `test_run_prepare_sdi_payload_lotto_task_maps_rows`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_run_prepare_sdi_payload_lotto_task_maps_rows(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            (
                101, 2001, 1, 3, "2026/A/123", 123, date(2026, 2, 17),
                501, 601, 1, Decimal("99.50"),
            )
        ]
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.run_prepare_sdi_payload_lotto_task(
            lotto_id=10,
            stato_sdi_codice_interno="DA_INVIARE",
            force_new_tentativo=False,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].fattura_sdi_id, 101)
        self.assertEqual(result[0].fattura_id, 2001)
        self.assertEqual(result[0].codice_documento, "2026/A/123")
        self.assertEqual(result[0].billing_account_id, 501)
        self.assertEqual(result[0].emittente_soggetto_ruolo_id, 601)

    # Scopo: Verifica il caso `test_run_prepare_sdi_payload_lotto_task_returns_empty_list`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_run_prepare_sdi_payload_lotto_task_returns_empty_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = []
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.run_prepare_sdi_payload_lotto_task(
            lotto_id=10,
            stato_sdi_codice_interno="DA_INVIARE",
            force_new_tentativo=False,
        )

        self.assertEqual(result, [])

    # Scopo: Verifica il caso `test_log_fattura_inserts_with_explicit_critical`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_log_fattura_inserts_with_explicit_critical(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.log_fattura(
            fattura_id=123,
            status="W",
            messaggio="warning test",
            critical=True,
            meta={"scope": "FATTURA"},
        )

        cursor.execute.assert_called_once()
        _, execute_params = cursor.execute.call_args.args
        self.assertEqual(execute_params[0], "warning test")
        self.assertEqual(execute_params[1], "W")
        self.assertEqual(execute_params[3], 123)

    # Scopo: Verifica il caso `test_log_fatture_lotto_sets_critical_from_status`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_log_fatture_lotto_sets_critical_from_status(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.log_fatture_lotto(
            lotto_id=55,
            status="C",
            messaggio="critical lotto",
            meta={"scope": "LOTTO"},
        )

        cursor.execute.assert_called_once()
        _, execute_params = cursor.execute.call_args.args
        self.assertEqual(execute_params[0], "critical lotto")
        self.assertEqual(execute_params[1], "C")
        self.assertEqual(execute_params[3], 55)

    # Scopo: Verifica il caso `test_is_lotto_in_errore_returns_true_when_stato_is_errore`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_is_lotto_in_errore_returns_true_when_stato_is_errore(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (True,)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.is_lotto_in_errore(10)

        self.assertTrue(result)

    # Scopo: Verifica il caso `test_is_lotto_in_errore_returns_false_when_lotto_not_found`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_is_lotto_in_errore_returns_false_when_lotto_not_found(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = None
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.is_lotto_in_errore(999999)

        self.assertFalse(result)

    # Scopo: Verifica il caso `test_get_lotto_segnalazioni_summary_maps_counts`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_lotto_segnalazioni_summary_maps_counts(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (1, 2, 3, 4, 5, 7)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.get_lotto_segnalazioni_summary(10)

        self.assertEqual(
            result,
            {
                "fatture_critical_count": 1,
                "fatture_warning_count": 2,
                "lotto_critical_count": 3,
                "lotto_warning_count": 4,
                "lotto_info_count": 5,
                "fatture_stato_esecuzione_errore_count": 7,
            },
        )
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_get_lotto_segnalazioni_summary", execute_sql)
        self.assertEqual(execute_params, [10])

    # Scopo: Verifica il caso `test_get_pipeline_id_for_step_returns_id_when_found`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_pipeline_id_for_step_returns_id_when_found(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (42,)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.get_pipeline_id_for_step("MASSIVO", 2, None, None)

        self.assertEqual(result, 42)
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_resolve_fatturazione_pipeline_step", execute_sql)
        self.assertEqual(execute_params, ["MASSIVO", 2, None, None])

    # Scopo: Verifica il caso `test_get_pipeline_id_for_step_returns_none_when_not_found`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_pipeline_id_for_step_returns_none_when_not_found(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = None
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.get_pipeline_id_for_step("MASSIVO", 2, None, None)

        self.assertIsNone(result)

    # Scopo: Verifica il caso `test_task_policy_exists_returns_true_when_policy_active`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_task_policy_exists_returns_true_when_policy_active(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (True,)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.task_policy_exists(100, "generate_fatture_righe")

        self.assertTrue(result)
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fatturazione_pipeline_task_policy", execute_sql)
        self.assertEqual(execute_params, [100, "generate_fatture_righe"])

    # Scopo: Verifica il caso `test_task_policy_exists_returns_false_when_no_policy`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_task_policy_exists_returns_false_when_no_policy(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (False,)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.task_policy_exists(100, "task_senza_policy")

        self.assertFalse(result)

    # Scopo: Verifica il caso `test_resolve_lotto_task_execution_mode_maps_row`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_resolve_lotto_task_execution_mode_maps_row(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (
            "RUN", True, "RESUME_TASK", None, None, {"max_tentativi": 3}, {},
        )
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.resolve_lotto_task_execution_mode(1, 100, 2, "generate_fatture_righe")

        self.assertIsInstance(result, TaskExecutionMode)
        self.assertEqual(result.execution_mode, "RUN")
        self.assertTrue(result.annullabile)
        self.assertEqual(result.resume_mode, "RESUME_TASK")
        self.assertIsNone(result.last_task_stato)
        self.assertIsNone(result.last_tentativo)
        self.assertEqual(result.policy_meta, {"max_tentativi": 3})
        self.assertEqual(result.run_meta, {})
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_resolve_lotto_task_execution_mode", execute_sql)
        self.assertEqual(execute_params, [1, 100, 2, "generate_fatture_righe"])

    # Scopo: Verifica che policy_meta e run_meta vengano decodificati correttamente da stringa JSON.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_resolve_lotto_task_execution_mode_decodes_meta_strings(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (
            "SKIP", False, "NO_RESUME", "COMPLETATO", 2,
            '{"key": "val"}', '{"run": true}',
        )
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.resolve_lotto_task_execution_mode(5, 10, 3, "numera_fatture")

        self.assertEqual(result.execution_mode, "SKIP")
        self.assertEqual(result.last_task_stato, "COMPLETATO")
        self.assertEqual(result.last_tentativo, 2)
        self.assertEqual(result.policy_meta, {"key": "val"})
        self.assertEqual(result.run_meta, {"run": True})

    # Scopo: Verifica il caso `test_start_lotto_task_run_returns_task_run_result`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_start_lotto_task_run_returns_task_run_result(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (999, 1)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.start_lotto_task_run(
            lotto_id=1,
            pipeline_id=100,
            stato_doc_fiscale_id=2,
            task_code="generate_fatture_righe",
            fase="Genera righe",
            meta={"rollback": False},
        )

        self.assertIsInstance(result, TaskRunResult)
        self.assertEqual(result.task_run_id, 999)
        self.assertEqual(result.tentativo, 1)
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_start_lotto_task_run", execute_sql)
        self.assertEqual(execute_params[0], 1)
        self.assertEqual(execute_params[1], 100)
        self.assertEqual(execute_params[3], "generate_fatture_righe")

    # Scopo: Verifica il caso `test_complete_lotto_task_run_calls_sql_function`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_complete_lotto_task_run_calls_sql_function(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.complete_lotto_task_run(999)

        cursor.execute.assert_called_once()
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_complete_lotto_task_run", execute_sql)
        self.assertEqual(execute_params[0], 999)

    # Scopo: Verifica il caso `test_fail_lotto_task_run_calls_sql_function_with_error_params`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_fail_lotto_task_run_calls_sql_function_with_error_params(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.fail_lotto_task_run(999, "E_TASK", "Errore task boom")

        cursor.execute.assert_called_once()
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_fail_lotto_task_run", execute_sql)
        self.assertEqual(execute_params[0], 999)
        self.assertEqual(execute_params[1], "E_TASK")
        self.assertEqual(execute_params[2], "Errore task boom")

    # Scopo: Verifica che set_lotto_job_stato aggiorni solo stato_lotto e meta senza toccare stato_operativo.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_set_lotto_job_stato_updates_only_stato_lotto(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ("IN_ESECUZIONE",)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.set_lotto_job_stato(10, "COMPLETATO", "Pipeline completata")

        self.assertEqual(cursor.execute.call_count, 2)
        first_sql, first_params = cursor.execute.call_args_list[0].args
        second_sql, second_params = cursor.execute.call_args_list[1].args
        self.assertIn("SELECT stato_lotto", first_sql)
        self.assertEqual(first_params, [10])
        self.assertIn("UPDATE vendite.fatturazione_lotti", second_sql)
        self.assertIn("SET stato_lotto = %s", second_sql)
        self.assertNotIn("stato_operativo", second_sql)
        self.assertEqual(second_params, ["COMPLETATO", "Pipeline completata", "Pipeline completata", 10])

    # Scopo: Verifica che set_lotto_job_stato rifiuti uno stato target non valido.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_set_lotto_job_stato_rejects_invalid_target_state(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        with self.assertRaises(ServiceError) as exc:
            repo.set_lotto_job_stato(10, "DRAFT", "stato non ammesso")

        self.assertEqual(exc.exception.code, "E_PIPELINE_STATO_LOTTO")
        self.assertEqual(cursor.execute.call_count, 1)
        execute_sql, _ = cursor.execute.call_args.args
        self.assertIn("fn_log_error_only", execute_sql)

    # Scopo: Verifica che set_lotto_job_stato applichi le transizioni ammesse dello stato tecnico lotto.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_set_lotto_job_stato_rejects_invalid_transition(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ("ERRORE",)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        with self.assertRaises(ServiceError) as exc:
            repo.set_lotto_job_stato(10, "COMPLETATO", "transizione non valida")

        self.assertEqual(exc.exception.code, "E_PIPELINE_STATO_LOTTO")
        self.assertEqual(cursor.execute.call_count, 2)
        first_sql, _ = cursor.execute.call_args_list[0].args
        second_sql, _ = cursor.execute.call_args_list[1].args
        self.assertIn("SELECT stato_lotto", first_sql)
        self.assertIn("fn_log_error_only", second_sql)

    # Scopo: Verifica che list_lotto_task_runs mappi correttamente righe runtime task da DB.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_list_lotto_task_runs_maps_rows(self, mocked_cursor_factory):
        class _DT:
            # Scopo: Simula data/ora DB serializzabile in isoformat per i test repository.
            def __init__(self, value: str):
                self._value = value

            def isoformat(self):
                return self._value

        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            (
                1001,
                80,
                4,
                8,
                "numera_fatture",
                "Numerazione fatture",
                1,
                "COMPLETATO",
                _DT("2026-02-19T10:00:00+01:00"),
                _DT("2026-02-19T10:00:02+01:00"),
                None,
                None,
                '{"rollback": false}',
            )
        ]
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.list_lotto_task_runs(80, limit=50)

        self.assertEqual(len(result), 1)
        row = result[0]
        self.assertEqual(row["id"], 1001)
        self.assertEqual(row["lotto_id"], 80)
        self.assertEqual(row["pipeline_id"], 4)
        self.assertEqual(row["task_code"], "numera_fatture")
        self.assertEqual(row["task_stato"], "COMPLETATO")
        self.assertEqual(row["meta"], {"rollback": False})
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fatturazione_lotti_task_runs", execute_sql)
        self.assertEqual(execute_params, [80, 50])

    # Scopo: il legame documentale delle note di credito (N10/BE-8) passa da una
    #        sola `SELECT fn_()` per fattura e ritorna quante coppie ha aggiunto.
    #        L'handler di pipeline mocka il repository, quindi questa e' l'unica
    #        rete sulla stringa SQL: senza, il nome della funzione sarebbe
    #        verificato solo dalla whitelist, che e' una stringa a sua volta.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_popola_fatture_rettifiche_chiama_la_fn_e_ritorna_le_coppie(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (2,)
        mocked_cursor_factory.return_value = cursor

        result = VenditePipelineRepository().popola_fatture_rettifiche(7701)

        self.assertEqual(result, 2)
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("vendite.fn_popola_fatture_rettifiche", execute_sql)
        self.assertEqual(execute_params, [7701])

    # Scopo: il confine SQL casta l'id; il guard di merito (NULL / <= 0) sta
    #        nella funzione DB e non si ripete qui.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_popola_fatture_rettifiche_casta_id_a_intero(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (0,)
        mocked_cursor_factory.return_value = cursor

        VenditePipelineRepository().popola_fatture_rettifiche("7701")

        self.assertEqual(cursor.execute.call_args.args[1], [7701])
