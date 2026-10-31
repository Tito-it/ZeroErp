# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il presidio di avvio fra timeout di gunicorn e soglia di ripresa
#        delle Idempotency-Key (`soglia_idempotenza`, BE-5). La soglia si
#        finge: qui si prova la regola, non la lettura dal database (la
#        chiamata vera a `dbops.fn_idempotency_soglia_secondi` la prova
#        `tests/db/test_idempotency_prenota_db.py`; le forme ammesse della
#        soglia il pgTAP `script/test-intero-positivo-da-testo-v1`).
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) VerificaSogliaTests.test_timeout_sotto_soglia_col_margine_passa
2) VerificaSogliaTests.test_margine_mancante_rifiuta
3) VerificaSogliaTests.test_timeout_zero_rifiuta_senza_leggere_la_soglia
4) VerificaSogliaTests.test_worker_non_sync_rifiuta
5) ComandoPresidiAvvioTests.test_modalita_forte_spenta_non_legge_niente
6) ComandoPresidiAvvioTests.test_passa_timeout_e_classe_risolta
7) ComandoPresidiAvvioTests.test_rifiuto_e_un_errore_del_comando
8) GunicornConfTests.test_il_controllo_gira_in_un_figlio
9) GunicornConfTests.test_il_figlio_che_rifiuta_ferma_il_master
10) GunicornConfTests.test_il_master_non_carica_django
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from gunicorn.workers.gthread import ThreadWorker
from gunicorn.workers.sync import SyncWorker

from apps.core.services.soglia_idempotenza import (
    MARGINE_SECONDI,
    SogliaIdempotenzaNonSicura,
    verifica_soglia_contro_timeout,
)

_SOGLIA = "apps.core.services.soglia_idempotenza.IdempotencyStore.soglia_ripresa_secondi"


class VerificaSogliaTests(TestCase):
    def test_timeout_sotto_soglia_col_margine_passa(self) -> None:
        with patch(_SOGLIA, return_value=60 + MARGINE_SECONDI):
            verifica_soglia_contro_timeout(timeout_secondi=60, worker_class=SyncWorker)

    def test_margine_mancante_rifiuta(self) -> None:
        with patch(_SOGLIA, return_value=60 + MARGINE_SECONDI - 1):
            with self.assertRaises(SogliaIdempotenzaNonSicura):
                verifica_soglia_contro_timeout(timeout_secondi=60, worker_class=SyncWorker)

    # ⭐ 0 per gunicorn e' «nessun timeout»: nessun tetto da confrontare.
    def test_timeout_zero_rifiuta_senza_leggere_la_soglia(self) -> None:
        with patch(_SOGLIA) as soglia:
            with self.assertRaises(SogliaIdempotenzaNonSicura):
                verifica_soglia_contro_timeout(timeout_secondi=0, worker_class=SyncWorker)
        soglia.assert_not_called()

    def test_worker_non_sync_rifiuta(self) -> None:
        with patch(_SOGLIA, return_value=10_000):
            with self.assertRaises(SogliaIdempotenzaNonSicura):
                verifica_soglia_contro_timeout(timeout_secondi=60, worker_class=ThreadWorker)


_VERIFICA = "apps.core.services.soglia_idempotenza.verifica_soglia_contro_timeout"
_ATTIVA_FUSO = "apps.core.management.comando_aziendale.attiva_fuso_aziendale"


# Il comando che `gunicorn.conf.py` lancia nel processo figlio (§15.17.3).
class ComandoPresidiAvvioTests(TestCase):
    @override_settings(API_STRONG_IDEMPOTENCY_ENABLED=False)
    def test_modalita_forte_spenta_non_legge_niente(self) -> None:
        # ⚠️ «Niente» comprende il fuso aziendale, che `ComandoAziendale`
        #    leggerebbe dal DB prima di `handle`.
        with patch(_VERIFICA) as verifica, patch(_ATTIVA_FUSO) as fuso:
            call_command("verifica_presidi_avvio", "--timeout", "60",
                         "--worker-class", "gunicorn.workers.sync.SyncWorker")
        verifica.assert_not_called()
        fuso.assert_not_called()

    # ⚠️ La classe arriva come percorso puntato e si confronta RISOLTA.
    @override_settings(API_STRONG_IDEMPOTENCY_ENABLED=True)
    def test_passa_timeout_e_classe_risolta(self) -> None:
        with patch(_VERIFICA) as verifica:
            call_command("verifica_presidi_avvio", "--timeout", "60",
                         "--worker-class", "gunicorn.workers.sync.SyncWorker")
        verifica.assert_called_once_with(timeout_secondi=60, worker_class=SyncWorker)

    @override_settings(API_STRONG_IDEMPOTENCY_ENABLED=True)
    def test_rifiuto_e_un_errore_del_comando(self) -> None:
        with patch(_VERIFICA, side_effect=SogliaIdempotenzaNonSicura("timeout troppo alto")):
            with self.assertRaisesRegex(CommandError, "timeout troppo alto"):
                call_command("verifica_presidi_avvio", "--timeout", "60",
                             "--worker-class", "gunicorn.workers.sync.SyncWorker")


# Scopo: carica `backend/gunicorn.conf.py` come lo carica gunicorn (dal file:
#        il nome non e' un modulo importabile).
def _gunicorn_conf() -> ModuleType:
    percorso = Path(__file__).resolve().parents[4] / "gunicorn.conf.py"
    spec = importlib.util.spec_from_file_location("_gunicorn_conf_di_prova", percorso)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _server(timeout: int = 60) -> SimpleNamespace:
    return SimpleNamespace(cfg=SimpleNamespace(timeout=timeout, worker_class=SyncWorker))


class GunicornConfTests(TestCase):
    def test_il_controllo_gira_in_un_figlio(self) -> None:
        conf = _gunicorn_conf()
        esito = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch.object(conf.subprocess, "run", return_value=esito) as run:
            conf.on_reload(_server(45))
        argomenti = run.call_args.args[0]
        self.assertEqual(argomenti[0], sys.executable)
        self.assertTrue(argomenti[1].endswith("manage.py"))
        self.assertEqual(argomenti[2:], [
            "verifica_presidi_avvio", "--timeout", "45",
            "--worker-class", "gunicorn.workers.sync.SyncWorker",
        ])

    def test_il_figlio_che_rifiuta_ferma_il_master(self) -> None:
        conf = _gunicorn_conf()
        esito = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="CommandError: timeout troppo alto",
        )
        with patch.object(conf.subprocess, "run", return_value=esito):
            with self.assertRaisesRegex(RuntimeError, "timeout troppo alto"):
                conf.on_starting(_server())

    # ⛔ Il difetto che la correzione toglie: un `django.setup()` nel master
    #    faceva ereditare ai worker di un HUP i moduli vecchi. Presidio sulla
    #    forma: il file non nomina Django.
    def test_il_master_non_carica_django(self) -> None:
        testo = (Path(__file__).resolve().parents[4] / "gunicorn.conf.py").read_text()
        codice = "\n".join(r for r in testo.splitlines() if not r.lstrip().startswith("#"))
        self.assertNotIn("django", codice)
        self.assertNotIn("apps.", codice)
