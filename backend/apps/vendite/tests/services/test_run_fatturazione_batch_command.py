# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test management command run_fatturazione_batch (driver F3).
# Indice test:
#   1) immediata → GIORNALIERO + meta fatturazione_immediata=True, un lotto per coppia
#   2) differita → MASSIVO + meta fatturazione_immediata=False
#   3) dry-run → solo discovery/conteggio, nessun run pipeline, NESSUNA registrazione job
#   4) best-effort → una coppia in errore non blocca le altre
#   5) canale di SISTEMA (RLS Path A): il batch gira nel gateway system_process_context
#   6) registrazione run-level: il run reale è avvolto in registered_job + meta riepilogo
#   7) skip anti-overlap: lock occupato (acquired=False) → corpo NON eseguito
# ------------------------------------------------------------

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from io import StringIO
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.core.management import call_command

from apps.core.services.service_errors import ServiceError
# Fixture lane condiviso (regola del 2): una sede sola per la forma di
# list_emittibili_lane.
from apps.vendite.tests._helpers.lane_fixture import lane as _lane

_CMD = "apps.vendite.management.commands.run_fatturazione_batch"
# Core estratto (C-1): repository e pipeline vivono nel service condiviso.
_SVC = "apps.vendite.services.fatturazione_driver_service"



# Scopo: helper che costruisce un patch di registered_job con un handle controllabile
#        (acquired) usabile come context manager.
def _registered_job_cm(*, acquired: bool = True):
    handle = MagicMock()
    handle.acquired = acquired

    @contextmanager
    def _cm(*_args, **_kwargs):
        yield handle

    return _cm, handle


class RunFatturazioneBatchCommandTests(TestCase):
    # Scopo: corsia immediata → GIORNALIERO + filtro True, un run per coppia, con
    #        tipo_doc_fiscale_id e competenza presi DALLA LANE.
    def test_immediata_runs_per_coppia_with_giornaliero_and_filter(self):
        cm, _h = _registered_job_cm()
        with patch(f"{_SVC}.CommesseRepository") as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run, \
             patch(f"{_CMD}.system_process_context"), \
             patch(f"{_CMD}.registered_job", cm):
            RepoCls.return_value.list_emittibili_lane.return_value = [
                _lane(1, tipo_doc=3, utility=9, comp=date(2026, 6, 1)),
                _lane(2, tipo_doc=7, utility=4, comp=date(2026, 5, 1)),
            ]
            mock_run.return_value = {"lotto_id": 100, "motivo_stop": "COMPLETATO", "step_eseguiti": 3}
            out = StringIO()
            call_command("run_fatturazione_batch", "--modalita", "immediata",
                         "--competenza", "2026-06-15", stdout=out)

        self.assertEqual(mock_run.call_count, 2)
        for call in mock_run.call_args_list:
            self.assertEqual(call.kwargs["tipo_lotto"], "GIORNALIERO")
            self.assertEqual(call.kwargs["meta"], {"fatturazione_immediata": True})
        # discovery col bound competenza (1° del mese), non la data grezza --competenza
        self.assertEqual(
            RepoCls.return_value.list_emittibili_lane.call_args.kwargs["competenza_mese"],
            date(2026, 6, 1),
        )
        # ogni lotto creato con (emittente, tipo_doc, utility, competenza) della propria lane
        terne = {
            (c.kwargs["emittente_soggetto_ruolo_id"],
             c.kwargs["tipo_doc_fiscale_id"],
             c.kwargs["utility_id"],
             c.kwargs["competenza_mese"])
            for c in mock_run.call_args_list
        }
        self.assertEqual(terne, {(1, 3, 9, date(2026, 6, 1)), (2, 7, 4, date(2026, 5, 1))})

    # Scopo: corsia differita → MASSIVO + filtro False.
    def test_differita_uses_massivo_and_false_filter(self):
        cm, _h = _registered_job_cm()
        with patch(f"{_SVC}.CommesseRepository") as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run, \
             patch(f"{_CMD}.system_process_context"), \
             patch(f"{_CMD}.registered_job", cm):
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(9)]
            mock_run.return_value = {"lotto_id": 1, "motivo_stop": "COMPLETATO", "step_eseguiti": 4}
            call_command("run_fatturazione_batch", "--modalita", "differita", stdout=StringIO())

        self.assertEqual(mock_run.call_count, 1)
        self.assertEqual(mock_run.call_args.kwargs["tipo_lotto"], "MASSIVO")
        self.assertEqual(mock_run.call_args.kwargs["meta"], {"fatturazione_immediata": False})

    # Scopo: dry-run → solo discovery/conteggio, nessun run pipeline, nessuna registrazione.
    def test_dry_run_only_discovers_and_skips_registration(self):
        with patch(f"{_SVC}.CommesseRepository") as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run, \
             patch(f"{_CMD}.system_process_context"), \
             patch(f"{_CMD}.registered_job") as mock_reg:
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(1, tot=2)]
            out = StringIO()
            call_command("run_fatturazione_batch", "--modalita", "immediata",
                         "--dry-run", stdout=out)

        mock_run.assert_not_called()
        mock_reg.assert_not_called()  # dry-run NON registra il job
        self.assertIn("DRY-RUN", out.getvalue())
        self.assertIn("utility=9", out.getvalue())
        self.assertIn("2 righe candidate", out.getvalue())

    # Scopo: best-effort → un emittente in errore non blocca gli altri.
    def test_best_effort_on_error(self):
        cm, _h = _registered_job_cm()
        with patch(f"{_SVC}.CommesseRepository") as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run, \
             patch(f"{_CMD}.system_process_context"), \
             patch(f"{_CMD}.registered_job", cm):
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(1), _lane(2)]
            mock_run.side_effect = [
                ServiceError(code="E_PIPELINE", message="boom", detail="x"),
                {"lotto_id": 2, "motivo_stop": "COMPLETATO", "step_eseguiti": 3},
            ]
            err = StringIO()
            call_command("run_fatturazione_batch", "--modalita", "differita",
                         stdout=StringIO(), stderr=err)

        self.assertEqual(mock_run.call_count, 2)
        self.assertIn("ERRORE", err.getvalue())

    # Scopo: il batch headless gira DENTRO il gateway di sistema (RLS Path A).
    def test_runs_inside_system_process_context(self):
        from apps.core.services.auth_constants import AUDIT_ACTOR_BATCH_FATTURAZIONE
        from apps.vendite.management.commands.run_fatturazione_batch import (
            SYSTEM_FATTURAZIONE_DB_ALIAS,
        )
        cm, _h = _registered_job_cm()
        with patch(f"{_SVC}.CommesseRepository") as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done"), \
             patch(f"{_CMD}.registered_job", cm), \
             patch(f"{_CMD}.system_process_context") as mock_gateway:
            RepoCls.return_value.list_emittibili_lane.return_value = []
            call_command("run_fatturazione_batch", "--modalita", "differita", stdout=StringIO())

        mock_gateway.assert_called_once_with(
            alias=SYSTEM_FATTURAZIONE_DB_ALIAS,
            actor=AUDIT_ACTOR_BATCH_FATTURAZIONE,
        )

    # Scopo: il run reale è registrato (registered_job) con job_id per-corsia + origine
    #        CRON, e il riepilogo viene scritto come meta.
    def test_registers_run_with_meta(self):
        from apps.core.services.job_run import ORIGINE_CRON
        captured = {}

        @contextmanager
        def _cm(job_id, **kwargs):
            handle = MagicMock()
            handle.acquired = True
            captured["job_id"] = job_id
            captured["kwargs"] = kwargs
            captured["handle"] = handle
            yield handle

        with patch(f"{_SVC}.CommesseRepository") as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run, \
             patch(f"{_CMD}.system_process_context"), \
             patch(f"{_CMD}.registered_job", _cm):
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(7)]
            mock_run.return_value = {"lotto_id": 5, "motivo_stop": "COMPLETATO", "step_eseguiti": 2}
            call_command("run_fatturazione_batch", "--modalita", "immediata", stdout=StringIO())

        self.assertEqual(captured["job_id"], "run_fatturazione_batch:immediata")
        self.assertEqual(captured["kwargs"].get("origine"), ORIGINE_CRON)
        self.assertEqual(captured["kwargs"].get("lock_key"), "run_fatturazione_batch:immediata")
        # meta riepilogo scritto sul handle.
        captured["handle"].set_meta.assert_called_once()
        meta = captured["handle"].set_meta.call_args[0][0]
        self.assertEqual(meta["lane"], 1)
        self.assertEqual(meta["per_motivo"], {"COMPLETATO": 1})

    # Scopo: lock occupato (acquired=False) → il corpo NON viene eseguito (skip).
    def test_skip_when_lock_busy(self):
        cm, _h = _registered_job_cm(acquired=False)
        with patch(f"{_SVC}.CommesseRepository") as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run, \
             patch(f"{_CMD}.system_process_context"), \
             patch(f"{_CMD}.registered_job", cm):
            out = StringIO()
            call_command("run_fatturazione_batch", "--modalita", "immediata", stdout=out)

        mock_run.assert_not_called()
        RepoCls.return_value.list_emittibili_lane.assert_not_called()
        self.assertIn("skip", out.getvalue())
