# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test management command `draina_coda_stampa` (worker drainer, C-2b).
#        Chiamante sottile: verifica canale di sistema, registered_job (lock
#        anti-overlap + meta), passaggio parametri al core, skip su lock busy.
#
# Indice test:
#   1) runs_inside_system_process_context — canale sistema con actor worker
#   2) registers_run_with_meta — registered_job job_id/lock + set_meta
#   3) passa_parametri_al_core — --limit/--soglia/--stale inoltrati
#   4) skip_when_lock_busy — acquired=False → core NON eseguito
# ------------------------------------------------------------

from __future__ import annotations

from contextlib import contextmanager
from io import StringIO
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.core.management import call_command

_CMD = "apps.vendite.management.commands.draina_coda_stampa"
_SVC_FN = f"{_CMD}.draina_coda_stampa"

_SUMMARY = {
    "recuperate": 0, "claimate": 2, "fatto": 2, "errore": 0,
    "riprovabili": 0, "soglia_tentativi": 5, "limit": 500,
}


def _registered_job_cm(*, acquired: bool = True):
    handle = MagicMock()
    handle.acquired = acquired

    @contextmanager
    def _cm(*_args, **_kwargs):
        yield handle

    return _cm, handle


class DrainaCodaStampaCommandTests(TestCase):

    # 1. Il worker gira DENTRO il gateway di sistema con l'actor dedicato.
    def test_runs_inside_system_process_context(self):
        from apps.core.services.auth_constants import AUDIT_ACTOR_WORKER_STAMPA
        from apps.vendite.management.commands.draina_coda_stampa import (
            SYSTEM_FATTURAZIONE_DB_ALIAS,
        )
        cm, _h = _registered_job_cm()
        with patch(_SVC_FN, return_value=_SUMMARY), \
             patch(f"{_CMD}.registered_job", cm), \
             patch(f"{_CMD}.system_process_context") as mock_gateway:
            call_command("draina_coda_stampa", stdout=StringIO())

        mock_gateway.assert_called_once_with(
            alias=SYSTEM_FATTURAZIONE_DB_ALIAS,
            actor=AUDIT_ACTOR_WORKER_STAMPA,
        )

    # 2. Il run è registrato (job_id/lock_key + origine CRON) e il riepilogo
    #    viene scritto come meta.
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

        with patch(_SVC_FN, return_value=_SUMMARY), \
             patch(f"{_CMD}.system_process_context"), \
             patch(f"{_CMD}.registered_job", _cm):
            call_command("draina_coda_stampa", stdout=StringIO())

        self.assertEqual(captured["job_id"], "draina_coda_stampa")
        self.assertEqual(captured["kwargs"].get("origine"), ORIGINE_CRON)
        self.assertEqual(captured["kwargs"].get("lock_key"), "draina_coda_stampa")
        captured["handle"].set_meta.assert_called_once_with(_SUMMARY)
        captured["handle"].set_rows_affected.assert_called_once_with(2)

    # 3. I parametri CLI passati sovrascrivono i default del core.
    def test_passa_parametri_al_core(self):
        cm, _h = _registered_job_cm()
        with patch(_SVC_FN, return_value=_SUMMARY) as mock_core, \
             patch(f"{_CMD}.system_process_context"), \
             patch(f"{_CMD}.registered_job", cm):
            call_command(
                "draina_coda_stampa",
                "--limit", "50", "--soglia-tentativi", "3", "--stale-minuti", "0",
                stdout=StringIO(),
            )

        kwargs = mock_core.call_args.kwargs
        self.assertEqual(kwargs["limit"], 50)
        self.assertEqual(kwargs["soglia_tentativi"], 3)
        self.assertEqual(kwargs["stale_minuti"], 0)

    # 4. Lock occupato (acquired=False) → il core NON viene eseguito (skip).
    def test_skip_when_lock_busy(self):
        cm, _h = _registered_job_cm(acquired=False)
        with patch(_SVC_FN) as mock_core, \
             patch(f"{_CMD}.system_process_context"), \
             patch(f"{_CMD}.registered_job", cm):
            out = StringIO()
            call_command("draina_coda_stampa", stdout=out)

        mock_core.assert_not_called()
        self.assertIn("skip", out.getvalue())
