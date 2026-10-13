# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del command `smoke_notturno` (giro notturno degli smoke): il
#        riassunto dell'output di smoke-baseline.sh, il rifiuto fuori sviluppo e
#        l'esito della corsa sul giornale. Senza DB: `registered_job` e il
#        sottoprocesso sono sostituiti.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) RiassumiTests.test_legge_conteggi_tempi_regressioni_e_log
2) RiassumiTests.test_output_irriconoscibile_lascia_solo_il_codice
3) ComandoTests.test_senza_permesso_rifiuta_senza_aprire_la_corsa
4) ComandoTests.test_giro_verde_chiude_la_corsa_ok
5) ComandoTests.test_regressioni_chiudono_ko_col_loro_codice
6) ComandoTests.test_errore_dello_script_chiude_ko
7) ComandoTests.test_timeout_chiude_ko
"""
from __future__ import annotations

import subprocess
from contextlib import contextmanager
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.core.management.commands import smoke_notturno as cmd

# Un estratto VERO dell'output di smoke-baseline.sh (giro del 2026-10-13).
_OUTPUT = """smoke baseline — 51 file (timeout 300s ciascuno)

⏱  Tempi — giro 774s, di cui attesa sul freno 447s. I piu' lenti:
     228s  (freno 206s)  smoke-test-core.sh

📄 Output dei non-verdi: /tmp/smoke-baseline-20261013-101500

Non-verdi ora: 12 su 51   |   noti in baseline (perimetro): 8

❌ REGRESSIONI — non erano in baseline:
   smoke-test-core.sh                               LIMITE_RICHIESTE
   smoke-test-listini-v5.sh                         ASSERZIONE

Sono da guardare: tutto il resto era gia' non-verde prima.
"""


class _Corsa:
    def __init__(self) -> None:
        self.acquired = True
        self.meta: dict | None = None
        self.message: str | None = None
        self.rows: int | None = None
        self.uscita_con: BaseException | None = None

    def set_meta(self, meta: dict) -> None:
        self.meta = meta

    def set_message(self, message: str) -> None:
        self.message = message

    def set_rows_affected(self, rows: int) -> None:
        self.rows = rows


class RiassumiTests(SimpleTestCase):

    # 1. Conteggi, tempi, cartella dei log e i nomi delle regressioni.
    def test_legge_conteggi_tempi_regressioni_e_log(self):
        esito = cmd.riassumi(_OUTPUT, 1)
        self.assertEqual(esito["codice_uscita"], 1)
        self.assertEqual((esito["non_verdi"], esito["totale"]), (12, 51))
        self.assertEqual((esito["durata_s"], esito["attesa_freno_s"]), (774, 447))
        self.assertEqual(esito["log_dir"], "/tmp/smoke-baseline-20261013-101500")
        self.assertEqual(esito["regressioni"], ["smoke-test-core.sh", "smoke-test-listini-v5.sh"])
        self.assertEqual(esito["rientrati"], [])

    # 2. Se un giorno l'output cambia forma, il riassunto non inventa: resta il
    #    codice d'uscita, che e' quello che decide l'esito.
    def test_output_irriconoscibile_lascia_solo_il_codice(self):
        esito = cmd.riassumi("qualcos'altro", 2)
        self.assertEqual(esito, {"codice_uscita": 2, "regressioni": [], "rientrati": []})


class ComandoTests(SimpleTestCase):

    def setUp(self):
        self.corsa = _Corsa()
        self.aperture: list[tuple] = []

        @contextmanager
        def finto_registered_job(job_name, **kwargs):
            self.aperture.append((job_name, kwargs))
            try:
                yield self.corsa
            except BaseException as exc:
                self.corsa.uscita_con = exc
                raise

        self.enterContext(mock.patch.object(cmd, "registered_job", finto_registered_job))
        self.enterContext(mock.patch.dict("os.environ", {cmd.ENV_CONSENTITO: "1"}))

    def _lancia(self, codice: int):
        fatto = subprocess.CompletedProcess(args=[], returncode=codice, stdout=_OUTPUT, stderr="")
        with mock.patch.object(cmd, "lancia_con_tetto", return_value=fatto):
            call_command("smoke_notturno")

    # 3. Fuori sviluppo (manca il permesso) il comando non parte e non apre la
    #    corsa: un rifiuto non sporca il giornale.
    def test_senza_permesso_rifiuta_senza_aprire_la_corsa(self):
        with mock.patch.dict("os.environ", {cmd.ENV_CONSENTITO: ""}):
            with self.assertRaises(CommandError):
                call_command("smoke_notturno")
        self.assertEqual(self.aperture, [])

    # 4. Nessuna regressione: la corsa si chiude senza eccezione (ok=true), col
    #    riassunto nel meta, sulla corsia dichiarata nella sveglia.
    def test_giro_verde_chiude_la_corsa_ok(self):
        self._lancia(0)
        self.assertEqual(self.aperture[0][0], cmd.JOB_NAME)
        self.assertEqual(self.aperture[0][1]["processo_codice"], "smoke_notturno")
        self.assertIsNone(self.corsa.uscita_con)
        assert self.corsa.meta is not None
        self.assertEqual(self.corsa.meta["non_verdi"], 12)
        self.assertEqual(self.corsa.rows, 12)

    # 5. Regressioni: la corsa esce con `SMOKE_REGRESSIONI` (ok=false), e il
    #    messaggio le nomina.
    def test_regressioni_chiudono_ko_col_loro_codice(self):
        with self.assertRaises(cmd.GiroSmokeFallito) as ctx:
            self._lancia(1)
        self.assertEqual(ctx.exception.code, "SMOKE_REGRESSIONI")
        self.assertIn("smoke-test-listini-v5.sh", str(ctx.exception))
        self.assertIs(self.corsa.uscita_con, ctx.exception)

    # 6. Lo script stesso fallisce (uscita 2): esito negativo col suo codice.
    def test_errore_dello_script_chiude_ko(self):
        with self.assertRaises(cmd.GiroSmokeFallito) as ctx:
            self._lancia(2)
        self.assertEqual(ctx.exception.code, "SMOKE_GIRO_FALLITO")

    # 7. Oltre il limite di tempo: la corsa si chiude comunque, negativa.
    def test_timeout_chiude_ko(self):
        scaduto = subprocess.TimeoutExpired(cmd="bash", timeout=cmd.TIMEOUT_GIRO_S)
        with mock.patch.object(cmd, "lancia_con_tetto", side_effect=scaduto):
            with self.assertRaises(cmd.GiroSmokeFallito) as ctx:
                call_command("smoke_notturno")
        self.assertEqual(ctx.exception.code, "SMOKE_GIRO_FALLITO")
        self.assertIs(self.corsa.uscita_con, ctx.exception)
