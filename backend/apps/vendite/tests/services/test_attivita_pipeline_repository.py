# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari repository pipeline attivita fatturabili.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) AttivitaPipelineRepositoryUnitTests.test_list_attivita_pipeline_steps_maps_rows
2) AttivitaPipelineRepositoryUnitTests.test_get_attivita_step_processes_returns_jsonb_list
3) AttivitaPipelineRepositoryUnitTests.test_get_attivita_step_processes_decodes_jsonb_string
4) AttivitaPipelineRepositoryUnitTests.test_get_attivita_step_processes_returns_empty_when_no_row
5) AttivitaPipelineRepositoryUnitTests.test_get_attivita_pipeline_id_for_step_returns_id
6) AttivitaPipelineRepositoryUnitTests.test_get_attivita_pipeline_id_for_step_returns_none
7) AttivitaPipelineRepositoryUnitTests.test_task_policy_exists_returns_true
8) AttivitaPipelineRepositoryUnitTests.test_task_policy_exists_returns_false_when_service_error
9) AttivitaPipelineRepositoryUnitTests.test_start_attivita_task_run_returns_result
10) AttivitaPipelineRepositoryUnitTests.test_complete_attivita_task_run_calls_fn
11) AttivitaPipelineRepositoryUnitTests.test_fail_attivita_task_run_calls_fn_with_error_params
12) AttivitaPipelineRepositoryUnitTests.test_list_sorgenti_abilitate_returns_list
13) AttivitaPipelineRepositoryUnitTests.test_get_attivita_branch_summary_returns_dict
14) AttivitaPipelineRepositoryUnitTests.test_get_lotto_attivita_info_returns_dict
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.attivita_pipeline_repository import (
    AttivitaPipelineRepository,
    AttivitaSorgenteBranchPolicy,
    AttivitaTaskRunResult,
)


class AttivitaPipelineRepositoryUnitTests(TestCase):
    # Scopo: Verifica il caso test_list_attivita_pipeline_steps_maps_rows.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_list_attivita_pipeline_steps_maps_rows(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            ("ACQUISISCI_PREVENTIVI", "Acquisizione preventivi", 1),
            ("NORMALIZZA", "Normalizzazione", 2),
        ]
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        steps = repo.list_attivita_pipeline_steps(utility_id=1, sorgente_tipo_id=2)

        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].codice_step, "ACQUISISCI_PREVENTIVI")
        self.assertEqual(steps[0].descrizione, "Acquisizione preventivi")
        self.assertEqual(steps[0].ordine, 1)
        self.assertEqual(steps[1].codice_step, "NORMALIZZA")
        self.assertEqual(steps[1].ordine, 2)

    # Scopo: Verifica il caso test_get_attivita_step_processes_returns_jsonb_list.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_get_attivita_step_processes_returns_jsonb_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ([{"task": "acquisisci_preventivi", "params": {}}],)
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        result = repo.get_attivita_step_processes(
            "ACQUISISCI_PREVENTIVI",
            utility_id=None,
            sorgente_tipo_id=2,
            rollback=False,
        )

        self.assertEqual(result, [{"task": "acquisisci_preventivi", "params": {}}])

    # Scopo: Verifica il caso test_get_attivita_step_processes_decodes_jsonb_string.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_get_attivita_step_processes_decodes_jsonb_string(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ('[{"task":"normalizza_attivita"}]',)
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        result = repo.get_attivita_step_processes(
            "NORMALIZZA",
            utility_id=None,
            sorgente_tipo_id=None,
            rollback=False,
        )

        self.assertEqual(result, [{"task": "normalizza_attivita"}])

    # Scopo: Verifica il caso test_get_attivita_step_processes_returns_empty_when_no_row.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_get_attivita_step_processes_returns_empty_when_no_row(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = None
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        result = repo.get_attivita_step_processes(
            "STEP_INESISTENTE",
            utility_id=None,
            sorgente_tipo_id=None,
            rollback=False,
        )

        self.assertEqual(result, [])

    # Scopo: Verifica il caso test_get_attivita_pipeline_id_for_step_returns_id.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_get_attivita_pipeline_id_for_step_returns_id(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (42,)
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        result = repo.get_attivita_pipeline_id_for_step(
            "ACQUISISCI_PREVENTIVI",
            utility_id=1,
            sorgente_tipo_id=2,
        )

        self.assertEqual(result, 42)

    # Scopo: Verifica il caso test_get_attivita_pipeline_id_for_step_returns_none.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_get_attivita_pipeline_id_for_step_returns_none(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (None,)
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        result = repo.get_attivita_pipeline_id_for_step(
            "STEP_SENZA_PIPELINE",
            utility_id=None,
            sorgente_tipo_id=None,
        )

        self.assertIsNone(result)

    # Scopo: Verifica il caso test_task_policy_exists_returns_true.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_task_policy_exists_returns_true(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        # fn_get_attivita_pipeline_task_policy ritorna riga valida
        cursor.fetchone.return_value = (True, "RESUME_BRANCH", "BRANCH", [], True, {})
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        result = repo.task_policy_exists(pipeline_id=1, task_code="noop", branch_code="DEFAULT")

        self.assertTrue(result)

    # Scopo: Verifica il caso test_task_policy_exists_returns_false_when_service_error.
    def test_task_policy_exists_returns_false_when_service_error(self):
        repo = AttivitaPipelineRepository()
        # Sovrascrive get_attivita_task_policy per simulare eccezione DB
        def _raise(*args, **kwargs):
            raise ServiceError(
                code="E_ATTIVITA_PIPELINE",
                message="Policy non trovata.",
                detail="test",
            )

        repo.get_attivita_task_policy = _raise
        result = repo.task_policy_exists(pipeline_id=1, task_code="noop")
        self.assertFalse(result)

    # Scopo: Verifica il caso test_start_attivita_task_run_returns_result.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_start_attivita_task_run_returns_result(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (77, 1)
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        result = repo.start_attivita_task_run(
            lotto_id=10,
            pipeline_id=1,
            task_code="noop",
            branch_code="DEFAULT",
            sorgente_tipo_id=2,
            fase="Fase test",
            block_scope="BRANCH",
            depends_on=[],
            meta={"rollback": False},
        )

        self.assertIsInstance(result, AttivitaTaskRunResult)
        self.assertEqual(result.task_run_id, 77)
        self.assertEqual(result.tentativo, 1)

    # Scopo: Verifica il caso test_complete_attivita_task_run_calls_fn.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_complete_attivita_task_run_calls_fn(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        repo.complete_attivita_task_run(task_run_id=77)

        cursor.execute.assert_called_once()
        call_sql = cursor.execute.call_args[0][0]
        self.assertIn("fn_complete_attivita_lotto_task_run", call_sql)
        self.assertIn("77", str(cursor.execute.call_args[0][1]))

    # Scopo: Verifica il caso test_fail_attivita_task_run_calls_fn_with_error_params.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_fail_attivita_task_run_calls_fn_with_error_params(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        repo.fail_attivita_task_run(
            task_run_id=77,
            error_code="E_ATTIVITA_TASK",
            error_message="Errore test",
        )

        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0][1]
        self.assertEqual(call_args[0], 77)
        self.assertEqual(call_args[1], "E_ATTIVITA_TASK")
        self.assertEqual(call_args[2], "Errore test")

    # Scopo: Verifica il caso test_list_sorgenti_abilitate_returns_list.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_list_sorgenti_abilitate_returns_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            (1, "DEFAULT", True, "PULL", "BRANCH", 1, {}),
            (2, "PREVENTIVI", True, "PULL", "BRANCH", 2, {}),
        ]
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        result = repo.list_sorgenti_abilitate()

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], AttivitaSorgenteBranchPolicy)
        self.assertEqual(result[0].sorgente_tipo_id, 1)
        self.assertEqual(result[0].branch_code, "DEFAULT")
        self.assertEqual(result[0].block_scope, "BRANCH")
        self.assertEqual(result[0].priorita, 1)
        self.assertEqual(result[1].sorgente_tipo_id, 2)
        self.assertEqual(result[1].branch_code, "PREVENTIVI")
        execute_sql = cursor.execute.call_args[0][0]
        self.assertIn("fn_list_attivita_sorgenti_abilitate", execute_sql)

    # Scopo: Verifica il caso test_get_attivita_branch_summary_returns_dict.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_get_attivita_branch_summary_returns_dict(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            ("DEFAULT", "COMPLETATO", 3),
            ("PREVENTIVI", "ERRORE", 1),
        ]
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        result = repo.get_attivita_branch_summary(lotto_id=10)

        self.assertEqual(result, {"DEFAULT": {"COMPLETATO": 3}, "PREVENTIVI": {"ERRORE": 1}})
        execute_sql = cursor.execute.call_args[0][0]
        self.assertIn("fn_get_attivita_branch_summary", execute_sql)
        self.assertEqual(cursor.execute.call_args[0][1], [10])

    # Scopo: Verifica il caso test_get_lotto_attivita_info_returns_dict.
    @patch("apps.vendite.db.attivita_pipeline_repository.connection.cursor")
    def test_get_lotto_attivita_info_returns_dict(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ("COMPLETATO", "APERTO", False)
        mocked_cursor_factory.return_value = cursor

        repo = AttivitaPipelineRepository()
        info = repo.get_lotto_attivita_info(lotto_id=10)

        self.assertEqual(info, {"stato_lotto": "COMPLETATO", "stato_operativo": "APERTO", "is_in_esecuzione": False})
        execute_sql = cursor.execute.call_args[0][0]
        self.assertIn("fn_get_attivita_lotto_info", execute_sql)
        # I metodi delegati usano get_lotto_attivita_info
        self.assertEqual(repo.get_lotto_attivita_stato(10), "COMPLETATO")
        self.assertEqual(repo.get_lotto_attivita_full_stato(10), {"stato_lotto": "COMPLETATO", "stato_operativo": "APERTO"})
        self.assertFalse(repo.is_lotto_attivita_in_esecuzione(10))
