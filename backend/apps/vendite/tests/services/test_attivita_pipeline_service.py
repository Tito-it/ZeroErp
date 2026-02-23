# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service facade pipeline attivita fatturabili.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) AttivitaPipelineServiceUnitTests.test_pr_run_attivita_pipeline_calls_runner
2) AttivitaPipelineServiceUnitTests.test_fn_get_attivita_pipeline_status_returns_dto
3) AttivitaPipelineServiceUnitTests.test_fn_get_attivita_pipeline_status_raises_when_lotto_not_found
4) AttivitaPipelineServiceUnitTests.test_fn_get_attivita_pipeline_status_raises_on_invalid_lotto_id
5) AttivitaPipelineServiceUnitTests.test_fn_get_attivita_task_runs_returns_dto
6) AttivitaPipelineServiceUnitTests.test_fn_get_attivita_task_runs_validates_limit
"""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.attivita_pipeline_service import (
    _compute_branch_summary,
    fn_get_attivita_pipeline_status,
    fn_get_attivita_task_runs,
    pr_run_attivita_pipeline,
)


def _make_task_run(branch_code: str, task_stato: str) -> dict:
    return {
        "id": 1,
        "lotto_attivita_id": 10,
        "pipeline_id": None,
        "sorgente_tipo_id": 1,
        "branch_code": branch_code,
        "task_code": "acquisisci_preventivi",
        "fase": "Acquisizione",
        "tentativo": 1,
        "task_stato": task_stato,
        "block_scope": "BRANCH",
        "depends_on": [],
        "started_at": None,
        "ended_at": None,
        "error_code": None,
        "error_message": None,
        "meta": {},
    }


class AttivitaPipelineServiceUnitTests(SimpleTestCase):

    # Scopo: Verifica che pr_run_attivita_pipeline deleghi al runner e ritorni lotto_id.
    def test_pr_run_attivita_pipeline_calls_runner(self):
        mock_runner = MagicMock()
        mock_runner.run_pipeline.return_value = 42

        with patch(
            "apps.vendite.services.attivita_pipeline_service.AttivitaPipelineRunner",
            return_value=mock_runner,
        ):
            result = pr_run_attivita_pipeline(
                lotto_id=None,
                competenza_mese=None,
                utility_id=5,
                dry_run=True,
            )

        self.assertEqual(result, 42)
        mock_runner.run_pipeline.assert_called_once()
        call_params = mock_runner.run_pipeline.call_args[0][0]
        self.assertEqual(call_params.utility_id, 5)
        self.assertTrue(call_params.dry_run)

    # Scopo: Verifica che fn_get_attivita_pipeline_status ritorni DTO completo con branch_summary.
    def test_fn_get_attivita_pipeline_status_returns_dto(self):
        mock_repo = MagicMock()
        mock_repo.get_lotto_attivita_full_stato.return_value = {
            "stato_lotto": "COMPLETATO",
            "stato_operativo": "APERTO",
        }
        mock_repo.list_attivita_task_runs.return_value = [
            _make_task_run("DEFAULT", "COMPLETATO"),
            _make_task_run("DEFAULT", "COMPLETATO"),
            _make_task_run("PREVENTIVI", "ERRORE"),
        ]

        with patch(
            "apps.vendite.services.attivita_pipeline_service.AttivitaPipelineRepository",
            return_value=mock_repo,
        ):
            result = fn_get_attivita_pipeline_status(lotto_id=10)

        self.assertEqual(result["lotto_id"], 10)
        self.assertEqual(result["stato_lotto"], "COMPLETATO")
        self.assertEqual(result["stato_operativo"], "APERTO")
        self.assertEqual(result["branch_summary"]["DEFAULT"]["COMPLETATO"], 2)
        self.assertEqual(result["branch_summary"]["PREVENTIVI"]["ERRORE"], 1)

    # Scopo: Verifica che fn_get_attivita_pipeline_status sollevi E_ATTIVITA_LOTTO_NOT_FOUND se lotto manca.
    def test_fn_get_attivita_pipeline_status_raises_when_lotto_not_found(self):
        mock_repo = MagicMock()
        mock_repo.get_lotto_attivita_full_stato.return_value = None

        with patch(
            "apps.vendite.services.attivita_pipeline_service.AttivitaPipelineRepository",
            return_value=mock_repo,
        ):
            with self.assertRaises(ServiceError) as exc:
                fn_get_attivita_pipeline_status(lotto_id=999)

        self.assertEqual(exc.exception.code, "E_ATTIVITA_LOTTO_NOT_FOUND")

    # Scopo: Verifica che fn_get_attivita_pipeline_status sollevi E_ATTIVITA_VALIDATION per lotto_id=0.
    def test_fn_get_attivita_pipeline_status_raises_on_invalid_lotto_id(self):
        with self.assertRaises(ServiceError) as exc:
            fn_get_attivita_pipeline_status(lotto_id=0)

        self.assertEqual(exc.exception.code, "E_ATTIVITA_VALIDATION")

    # Scopo: Verifica che fn_get_attivita_task_runs ritorni DTO con count e task_runs.
    def test_fn_get_attivita_task_runs_returns_dto(self):
        runs = [
            _make_task_run("DEFAULT", "COMPLETATO"),
            _make_task_run("DEFAULT", "COMPLETATO"),
        ]
        mock_repo = MagicMock()
        mock_repo.list_attivita_task_runs.return_value = runs

        with patch(
            "apps.vendite.services.attivita_pipeline_service.AttivitaPipelineRepository",
            return_value=mock_repo,
        ):
            result = fn_get_attivita_task_runs(lotto_id=10, limit=50)

        self.assertEqual(result["lotto_id"], 10)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["task_runs"], runs)
        mock_repo.list_attivita_task_runs.assert_called_once_with(
            10, branch_code=None, limit=50
        )

    # Scopo: Verifica che fn_get_attivita_task_runs sollevi E_ATTIVITA_VALIDATION per limit fuori range.
    def test_fn_get_attivita_task_runs_validates_limit(self):
        with self.assertRaises(ServiceError) as exc:
            fn_get_attivita_task_runs(lotto_id=10, limit=600)

        self.assertEqual(exc.exception.code, "E_ATTIVITA_VALIDATION")
