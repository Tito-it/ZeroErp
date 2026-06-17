# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test management command run_fatturazione_batch (driver F3).
# Indice test:
#   1) immediata → GIORNALIERO + meta fatturazione_immediata=True, un lotto per emittente
#   2) differita → MASSIVO + meta fatturazione_immediata=False
#   3) dry-run → solo discovery/conteggio, nessun run pipeline
#   4) best-effort → un emittente in errore non blocca gli altri
#   5) canale di SISTEMA (RLS Path A): il batch gira nel gateway system_process_context
#      con alias system_fatturazione + attore d'audit BATCH_FATTURAZIONE
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from django.core.management import call_command

from apps.core.services.service_errors import ServiceError

_CMD = "apps.vendite.management.commands.run_fatturazione_batch"


class RunFatturazioneBatchCommandTests(TestCase):
    # Scopo: corsia immediata → GIORNALIERO + filtro True, un run per emittente.
    def test_immediata_runs_per_emittente_with_giornaliero_and_filter(self):
        with patch(f"{_CMD}.CommesseRepository") as RepoCls, \
             patch(f"{_CMD}.run_lotto_pipeline_until_done") as mock_run, \
             patch(f"{_CMD}.system_process_context"):
            RepoCls.return_value.list_emittibili_emittenti.return_value = [1, 2]
            mock_run.return_value = {"lotto_id": 100, "motivo_stop": "COMPLETATO", "step_eseguiti": 3}
            out = StringIO()
            call_command("run_fatturazione_batch", "--modalita", "immediata",
                         "--competenza", "2026-06-15", stdout=out)

        self.assertEqual(mock_run.call_count, 2)
        for call in mock_run.call_args_list:
            self.assertEqual(call.kwargs["tipo_lotto"], "GIORNALIERO")
            self.assertEqual(call.kwargs["meta"], {"fatturazione_immediata": True})
            self.assertEqual(call.kwargs["competenza_mese"], date(2026, 6, 1))
        emittenti = {c.kwargs["emittente_soggetto_ruolo_id"] for c in mock_run.call_args_list}
        self.assertEqual(emittenti, {1, 2})

    # Scopo: corsia differita → MASSIVO + filtro False.
    def test_differita_uses_massivo_and_false_filter(self):
        with patch(f"{_CMD}.CommesseRepository") as RepoCls, \
             patch(f"{_CMD}.run_lotto_pipeline_until_done") as mock_run, \
             patch(f"{_CMD}.system_process_context"):
            RepoCls.return_value.list_emittibili_emittenti.return_value = [9]
            mock_run.return_value = {"lotto_id": 1, "motivo_stop": "COMPLETATO", "step_eseguiti": 4}
            call_command("run_fatturazione_batch", "--modalita", "differita", stdout=StringIO())

        self.assertEqual(mock_run.call_count, 1)
        self.assertEqual(mock_run.call_args.kwargs["tipo_lotto"], "MASSIVO")
        self.assertEqual(mock_run.call_args.kwargs["meta"], {"fatturazione_immediata": False})

    # Scopo: dry-run → solo discovery/conteggio, nessun run pipeline.
    def test_dry_run_only_discovers(self):
        with patch(f"{_CMD}.CommesseRepository") as RepoCls, \
             patch(f"{_CMD}.run_lotto_pipeline_until_done") as mock_run, \
             patch(f"{_CMD}.system_process_context"):
            RepoCls.return_value.list_emittibili_emittenti.return_value = [1]
            RepoCls.return_value.list_commesse_emittibili.return_value = [10, 20]
            out = StringIO()
            call_command("run_fatturazione_batch", "--modalita", "immediata",
                         "--dry-run", stdout=out)

        mock_run.assert_not_called()
        self.assertIn("DRY-RUN", out.getvalue())
        self.assertIn("2 commesse", out.getvalue())

    # Scopo: best-effort → un emittente in errore non blocca gli altri.
    def test_best_effort_on_error(self):
        with patch(f"{_CMD}.CommesseRepository") as RepoCls, \
             patch(f"{_CMD}.run_lotto_pipeline_until_done") as mock_run, \
             patch(f"{_CMD}.system_process_context"):
            RepoCls.return_value.list_emittibili_emittenti.return_value = [1, 2]
            mock_run.side_effect = [
                ServiceError(code="E_PIPELINE", message="boom", detail="x"),
                {"lotto_id": 2, "motivo_stop": "COMPLETATO", "step_eseguiti": 3},
            ]
            err = StringIO()
            # Non deve sollevare: best-effort per-emittente.
            call_command("run_fatturazione_batch", "--modalita", "differita",
                         stdout=StringIO(), stderr=err)

        self.assertEqual(mock_run.call_count, 2)
        self.assertIn("ERRORE", err.getvalue())

    # Scopo: il batch headless gira DENTRO il gateway di sistema (RLS Path A),
    #        con l'alias del canale fatturazione e l'attore d'audit corretto.
    def test_runs_inside_system_process_context(self):
        from apps.core.services.auth_constants import AUDIT_ACTOR_BATCH_FATTURAZIONE
        from apps.vendite.management.commands.run_fatturazione_batch import (
            SYSTEM_FATTURAZIONE_DB_ALIAS,
        )

        with patch(f"{_CMD}.CommesseRepository") as RepoCls, \
             patch(f"{_CMD}.run_lotto_pipeline_until_done"), \
             patch(f"{_CMD}.system_process_context") as mock_gateway:
            RepoCls.return_value.list_emittibili_emittenti.return_value = []
            call_command("run_fatturazione_batch", "--modalita", "differita", stdout=StringIO())

        mock_gateway.assert_called_once_with(
            alias=SYSTEM_FATTURAZIONE_DB_ALIAS,
            actor=AUDIT_ACTOR_BATCH_FATTURAZIONE,
        )
