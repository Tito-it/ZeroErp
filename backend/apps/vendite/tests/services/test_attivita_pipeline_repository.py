# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari repository pipeline attivita fatturabili.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) AttivitaPipelineRepositoryUnitTests.test_start_attivita_task_run_returns_result
2) AttivitaPipelineRepositoryUnitTests.test_complete_attivita_task_run_calls_fn
3) AttivitaPipelineRepositoryUnitTests.test_fail_attivita_task_run_calls_fn_with_error_params
4) AttivitaPipelineRepositoryUnitTests.test_get_attivita_branch_summary_returns_dict
5) AttivitaPipelineRepositoryUnitTests.test_get_lotto_attivita_info_returns_dict
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.vendite.db.attivita_pipeline_repository import (
    AttivitaPipelineRepository,
    AttivitaTaskRunResult,
)


class AttivitaPipelineRepositoryUnitTests(TestCase):
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
