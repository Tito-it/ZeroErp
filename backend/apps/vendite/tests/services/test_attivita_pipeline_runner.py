# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari runner pipeline attivita fatturabili.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) AttivitaPipelineRunnerUnitTests.test_run_pipeline_completes_when_all_branches_ok
2) AttivitaPipelineRunnerUnitTests.test_run_pipeline_branch_error_does_not_block_other_branches
3) AttivitaPipelineRunnerUnitTests.test_run_pipeline_global_error_stops_all_branches
4) AttivitaPipelineRunnerUnitTests.test_run_pipeline_rejects_lotto_in_esecuzione
5) AttivitaPipelineRunnerUnitTests.test_run_pipeline_raises_when_no_sorgenti_abilitate
6) AttivitaPipelineRunnerUnitTests.test_run_pipeline_filtra_per_sorgente_tipo_id
"""

from contextlib import nullcontext
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.attivita_pipeline_repository import (
    AttivitaPipelineStep,
    AttivitaSorgenteBranchPolicy,
)
from apps.vendite.services.attivita_pipeline_runner import (
    AttivitaPipelineParams,
    AttivitaPipelineRunner,
)
from apps.vendite.services.attivita_pipeline_step_executor import (
    _AttivitaBranchBlockError,
    _AttivitaGlobalBlockError,
)


def _make_sorgente(sorgente_tipo_id: int, branch_code: str) -> AttivitaSorgenteBranchPolicy:
    return AttivitaSorgenteBranchPolicy(
        sorgente_tipo_id=sorgente_tipo_id,
        branch_code=branch_code,
        abilitata=True,
        acquisizione_mode="PULL",
        block_scope="BRANCH",
        priorita=sorgente_tipo_id,
        meta={},
    )


class AttivitaPipelineRunnerUnitTests(SimpleTestCase):
    class _RepoMock:
        def __init__(self):
            self.last_stato = None
            self.stato_history = []
            self._in_esecuzione = False

        def get_or_create_lotto_attivita(self, **kwargs):
            return 10

        def is_lotto_attivita_in_esecuzione(self, lotto_id):
            return self._in_esecuzione

        def list_sorgenti_abilitate(self, utility_id=None):
            return [
                _make_sorgente(1, "DEFAULT"),
                _make_sorgente(2, "PREVENTIVI"),
            ]

        def set_lotto_attivita_stato(self, lotto_id, stato_lotto, note=None):
            self.last_stato = stato_lotto
            self.stato_history.append(stato_lotto)

        def list_attivita_pipeline_steps(self, utility_id=None, sorgente_tipo_id=None):
            return [AttivitaPipelineStep(codice_step="STEP_1", descrizione="Step 1", ordine=1)]

    class _StepExecutorMock:
        def __init__(self, side_effect=None):
            self.called = False
            self.calls = []
            self.side_effect = side_effect

        def execute_step(self, *, lotto_id, codice_step, sorgente, dry_run):
            self.called = True
            self.calls.append({
                "lotto_id": lotto_id,
                "codice_step": codice_step,
                "sorgente_tipo_id": sorgente.sorgente_tipo_id,
            })
            if self.side_effect is not None:
                raise self.side_effect

    # Scopo: Verifica che pipeline completi quando tutte le sorgenti/branch riescono.
    def test_run_pipeline_completes_when_all_branches_ok(self):
        repo = self._RepoMock()
        step_executor = self._StepExecutorMock()
        runner = AttivitaPipelineRunner(repository=repo, step_executor=step_executor)

        with patch("apps.vendite.services.attivita_pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(AttivitaPipelineParams(dry_run=True))

        self.assertEqual(result, 10)
        self.assertEqual(repo.last_stato, "COMPLETATO")
        self.assertTrue(step_executor.called)
        # 2 sorgenti × 1 step ciascuna = 2 chiamate execute_step
        self.assertEqual(len(step_executor.calls), 2)

    # Scopo: Verifica che branch A in errore (BRANCH) non blocchi branch B.
    def test_run_pipeline_branch_error_does_not_block_other_branches(self):
        repo = self._RepoMock()
        call_count = [0]

        class _FailFirstBranchExecutor(self._StepExecutorMock):
            def execute_step(inner_self, *, lotto_id, codice_step, sorgente, dry_run):
                call_count[0] += 1
                inner_self.calls.append({"sorgente_tipo_id": sorgente.sorgente_tipo_id})
                if sorgente.sorgente_tipo_id == 1:
                    raise _AttivitaBranchBlockError("branch 1 fallito")

        step_executor = _FailFirstBranchExecutor()
        runner = AttivitaPipelineRunner(repository=repo, step_executor=step_executor)

        with patch("apps.vendite.services.attivita_pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(AttivitaPipelineParams(dry_run=False))

        # Branch A fallisce ma Branch B deve proseguire
        self.assertEqual(result, 10)
        self.assertEqual(repo.last_stato, "COMPLETATO")
        self.assertEqual(call_count[0], 2)  # entrambe le sorgenti tentate

    # Scopo: Verifica che errore GLOBAL fermi tutti i branch e marchi lotto ERRORE.
    def test_run_pipeline_global_error_stops_all_branches(self):
        repo = self._RepoMock()
        call_count = [0]

        class _GlobalBlockExecutor(self._StepExecutorMock):
            def execute_step(inner_self, *, lotto_id, codice_step, sorgente, dry_run):
                call_count[0] += 1
                if sorgente.sorgente_tipo_id == 1:
                    raise _AttivitaGlobalBlockError("errore globale")

        step_executor = _GlobalBlockExecutor()
        runner = AttivitaPipelineRunner(repository=repo, step_executor=step_executor)

        with patch("apps.vendite.services.attivita_pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(AttivitaPipelineParams(dry_run=False))

        # Lotto in ERRORE; branch 2 NON eseguito
        self.assertEqual(result, 10)
        self.assertEqual(repo.last_stato, "ERRORE")
        self.assertEqual(call_count[0], 1)  # solo la prima sorgente toccata

    # Scopo: Verifica che runner blocchi se lotto gia` in esecuzione.
    def test_run_pipeline_rejects_lotto_in_esecuzione(self):
        repo = self._RepoMock()
        repo._in_esecuzione = True
        step_executor = self._StepExecutorMock()
        runner = AttivitaPipelineRunner(repository=repo, step_executor=step_executor)

        with patch("apps.vendite.services.attivita_pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(AttivitaPipelineParams(lotto_id=10, dry_run=True))

        self.assertEqual(exc.exception.code, "E_ATTIVITA_PIPELINE")
        self.assertFalse(step_executor.called)

    # Scopo: Verifica che runner sollevi errore se nessuna sorgente abilitata.
    def test_run_pipeline_raises_when_no_sorgenti_abilitate(self):
        repo = self._RepoMock()
        repo.list_sorgenti_abilitate = lambda **kwargs: []
        step_executor = self._StepExecutorMock()
        runner = AttivitaPipelineRunner(repository=repo, step_executor=step_executor)

        with patch("apps.vendite.services.attivita_pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(AttivitaPipelineParams(dry_run=False))

        self.assertEqual(exc.exception.code, "E_ATTIVITA_PIPELINE")
        self.assertFalse(step_executor.called)

    # Scopo: Verifica che filtro per sorgente_tipo_id esegua solo il branch specificato.
    def test_run_pipeline_filtra_per_sorgente_tipo_id(self):
        repo = self._RepoMock()
        step_executor = self._StepExecutorMock()
        runner = AttivitaPipelineRunner(repository=repo, step_executor=step_executor)

        with patch("apps.vendite.services.attivita_pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(
                AttivitaPipelineParams(sorgente_tipo_id=2, dry_run=True)
            )

        self.assertEqual(result, 10)
        # Solo sorgente 2 deve essere stata eseguita
        executed_sorgenti = [c["sorgente_tipo_id"] for c in step_executor.calls]
        self.assertEqual(executed_sorgenti, [2])
