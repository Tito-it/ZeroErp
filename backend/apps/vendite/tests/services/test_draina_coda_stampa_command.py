# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test management command `draina_coda_stampa` (worker drainer, C-2b).
#        Chiamante sottile: verifica registered_job (attore + lock anti-overlap
#        + meta), passaggio parametri al core, skip su lock busy.
#
# ⭐ Riscritti il 2026-09-05. Il test 1 verificava che il command girasse DENTRO
#    il canale `BYPASSRLS`: adesso verifica il contrario — che NON ci sia nessun
#    canale di sistema, perché il worker gira con l'identità dell'utente tecnico
#    di ogni emittente (`draina_coda_stampa_per_roster`). Il test non è stato
#    tolto e sostituito con niente: è stato **girato**, perché la cosa da
#    presidiare è cambiata di segno.
#
# Indice test:
#   1) ⛔ nessun canale di sistema: il gateway BYPASSRLS non esiste più qui
#   2) registers_run_with_meta — registered_job attore/job_id/lock + set_meta
#   3) passa_parametri_al_core — --limit/--soglia/--stale inoltrati
#   4) skip_when_lock_busy — acquired=False → core NON eseguito
# ------------------------------------------------------------

from __future__ import annotations

from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from django.core.management import call_command

from apps.core.tests.job_run_fakes import fake_registered_job

_CMD = "apps.vendite.management.commands.draina_coda_stampa"
_SVC_FN = f"{_CMD}.draina_coda_stampa_per_roster"

_SUMMARY = {
    "recuperate": 0, "claimate": 2, "fatto": 2, "errore": 0,
    "riprovabili": 0, "soglia_tentativi": 5, "limit": 500,
    "emittenti_serviti": 2, "emittenti_falliti": [], "emittenti_non_serviti": [],
    "per_emittente": [],
}


class DrainaCodaStampaCommandTests(TestCase):

    # 1. ⛔ NIENTE canale di sistema. È il cuore del cantiere: finché il worker
    #    apriva una connessione `BYPASSRLS`, «un emittente alla volta» era una
    #    frase e non un fatto.
    def test_nessun_canale_di_sistema(self):
        import apps.vendite.management.commands.draina_coda_stampa as modulo

        cm, _h, _catturato = fake_registered_job()
        with patch(_SVC_FN, return_value=_SUMMARY), \
             patch(f"{_CMD}.registered_job", cm):
            call_command("draina_coda_stampa", stdout=StringIO())

        # ⭐ Si guarda il MODULO, non una chiamata: un `system_process_context`
        #    importato e non ancora usato sarebbe il primo passo per rimetterlo.
        self.assertFalse(hasattr(modulo, "system_process_context"))
        self.assertFalse(hasattr(modulo, "SYSTEM_FATTURAZIONE_DB_ALIAS"))

    # 1-bis. ⭐ Il giro DICE quali emittenti non ha servito. Senza questa riga a
    #    video, «nessuna stampa in coda» e «tre aziende senza utente tecnico»
    #    si leggono uguali — ed è il guasto silenzioso della D-9.
    def test_emittenti_non_serviti_finiscono_a_video(self):
        cm, _h, _catturato = fake_registered_job()
        summary = {**_SUMMARY, "claimate": 0,
                   "emittenti_non_serviti": ["ACME", "BETA"]}
        with patch(_SVC_FN, return_value=summary), \
             patch(f"{_CMD}.registered_job", cm):
            err = StringIO()
            call_command("draina_coda_stampa", stdout=StringIO(), stderr=err)

        testo = err.getvalue()
        self.assertIn("ACME", testo)
        self.assertIn("BETA", testo)
        self.assertIn("senza utente tecnico", testo)

    # 2. Il run è registrato (job_id/lock_key + origine CRON) e il riepilogo
    #    viene scritto come meta.
    def test_registers_run_with_meta(self):
        from apps.core.services.job_run import ORIGINE_CRON
        # ⭐ Stessa fabbrica condivisa: `captured` porta job_id e kwargs.
        cm, handle, captured = fake_registered_job()
        with patch(_SVC_FN, return_value=_SUMMARY), \
             patch(f"{_CMD}.registered_job", cm):
            call_command("draina_coda_stampa", stdout=StringIO())

        self.assertEqual(captured["job_id"], "draina_coda_stampa")
        self.assertEqual(captured["kwargs"].get("origine"), ORIGINE_CRON)
        self.assertEqual(captured["kwargs"].get("lock_key"), "draina_coda_stampa")
        # ⭐ L'ATTORE: senza, la riga di run resterebbe anonima.
        self.assertEqual(
            captured["kwargs"].get("processo_codice"), "draina_coda_stampa",
        )
        handle.set_meta.assert_called_once_with(_SUMMARY)
        handle.set_rows_affected.assert_called_once_with(2)

    # 3. I parametri CLI passati sovrascrivono i default del core.
    def test_passa_parametri_al_core(self):
        cm, _h, _catturato = fake_registered_job()
        with patch(_SVC_FN, return_value=_SUMMARY) as mock_core, \
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
        cm, _h, _catturato = fake_registered_job(acquired=False)
        with patch(_SVC_FN) as mock_core, \
             patch(f"{_CMD}.registered_job", cm):
            out = StringIO()
            call_command("draina_coda_stampa", stdout=out)

        mock_core.assert_not_called()
        self.assertIn("skip", out.getvalue())
