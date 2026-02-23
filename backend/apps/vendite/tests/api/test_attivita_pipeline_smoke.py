# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test multi-branch pipeline attivita fatturabili (BE-3.3).
# ------------------------------------------------------------

"""
Indice test eseguiti:
S1) AttivitaPipelineSmokeTests.test_smoke_multi_branch_preventivi_ordini_ok
S2) AttivitaPipelineSmokeTests.test_smoke_errore_branch_non_blocca_secondo
S3) AttivitaPipelineSmokeTests.test_smoke_nessuna_regressione_lotto_pipeline_api
"""

import json
from contextlib import nullcontext
from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase, override_settings

from apps.vendite.db.attivita_pipeline_repository import (
    AttivitaPipelineStep,
    AttivitaSorgenteBranchPolicy,
)
from apps.vendite.services.attivita_pipeline_runner import (
    AttivitaPipelineParams,
    AttivitaPipelineRunner,
)
from apps.vendite.services.attivita_pipeline_step_executor import _AttivitaBranchBlockError


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


class AttivitaPipelineSmokeTests(SimpleTestCase):
    """Smoke: verifica stack runner→executor(mock) con branch PREVENTIVI + ORDINI."""

    class _RepoMock:
        def __init__(self):
            self.last_stato = None
            self.stato_history = []

        def get_or_create_lotto_attivita(self, **kwargs):
            return 10

        def is_lotto_attivita_in_esecuzione(self, lotto_id):
            return False

        def list_sorgenti_abilitate(self, utility_id=None):
            return [
                _make_sorgente(3, "PREVENTIVI"),
                _make_sorgente(4, "ORDINI"),
            ]

        def set_lotto_attivita_stato(self, lotto_id, stato_lotto, note=None):
            self.last_stato = stato_lotto
            self.stato_history.append(stato_lotto)

        def list_attivita_pipeline_steps(self, utility_id=None, sorgente_tipo_id=None):
            return [AttivitaPipelineStep(codice_step="STEP_1", descrizione="Acquisizione", ordine=1)]

    class _StepExecutorMock:
        def __init__(self, side_effect_fn=None):
            self.calls = []
            self.side_effect_fn = side_effect_fn

        def execute_step(self, *, lotto_id, codice_step, sorgente, dry_run):
            self.calls.append({
                "lotto_id": lotto_id,
                "codice_step": codice_step,
                "branch_code": sorgente.branch_code,
            })
            if self.side_effect_fn is not None:
                self.side_effect_fn(sorgente)

    # Scopo: Verifica smoke S1 — entrambi i branch PREVENTIVI e ORDINI completano ok.
    def test_smoke_multi_branch_preventivi_ordini_ok(self):
        repo = self._RepoMock()
        step_executor = self._StepExecutorMock()
        runner = AttivitaPipelineRunner(repository=repo, step_executor=step_executor)

        with patch(
            "apps.vendite.services.attivita_pipeline_runner.transaction.atomic",
            return_value=nullcontext(),
        ):
            result = runner.run_pipeline(AttivitaPipelineParams(dry_run=False))

        self.assertEqual(result, 10)
        self.assertEqual(repo.last_stato, "COMPLETATO")
        executed_branches = [c["branch_code"] for c in step_executor.calls]
        self.assertIn("PREVENTIVI", executed_branches)
        self.assertIn("ORDINI", executed_branches)
        self.assertEqual(len(step_executor.calls), 2)

    # Scopo: Verifica smoke S2 — errore BRANCH in PREVENTIVI non blocca ORDINI.
    def test_smoke_errore_branch_non_blocca_secondo(self):
        repo = self._RepoMock()

        def _fail_preventivi(sorgente):
            if sorgente.branch_code == "PREVENTIVI":
                raise _AttivitaBranchBlockError("errore branch PREVENTIVI")

        step_executor = self._StepExecutorMock(side_effect_fn=_fail_preventivi)
        runner = AttivitaPipelineRunner(repository=repo, step_executor=step_executor)

        with patch(
            "apps.vendite.services.attivita_pipeline_runner.transaction.atomic",
            return_value=nullcontext(),
        ):
            result = runner.run_pipeline(AttivitaPipelineParams(dry_run=False))

        # Lotto completa (BRANCH non è globale)
        self.assertEqual(result, 10)
        self.assertEqual(repo.last_stato, "COMPLETATO")
        # Entrambi i branch sono stati tentati
        executed_branches = [c["branch_code"] for c in step_executor.calls]
        self.assertIn("PREVENTIVI", executed_branches)
        self.assertIn("ORDINI", executed_branches)

    # Scopo: Verifica smoke S3 — nessuna regressione sull'endpoint pipeline lotto.
    @override_settings(API_STRONG_IDEMPOTENCY_ENABLED=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_smoke_nessuna_regressione_lotto_pipeline_api(self, mocked_lotto_service, _mock_auth):
        mocked_lotto_service.return_value = 55
        client = Client()
        response = client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"tipo_lotto": "MASSIVO", "dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "smoke-lotto-regression-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["lotto_id"], 55)
        mocked_lotto_service.assert_called_once()
