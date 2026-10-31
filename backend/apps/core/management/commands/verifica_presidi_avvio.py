# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command — i presidi di avvio del server web, per
#        `gunicorn.conf.py`, che lo lancia in un processo FIGLIO usa e getta
#        all'avvio e a ogni `kill -HUP`. Esce con errore (e il motivo su
#        stderr) se la configurazione non e' sicura: il master non parte.
#
#        USO (lo chiama gunicorn, a mano solo per prova):
#          ./manage-env.sh verifica_presidi_avvio --timeout 60 \
#              --worker-class gunicorn.workers.sync.SyncWorker
#
# Note: ⭐ Perche' un processo figlio (brief-modello-documento-vendita
#       §15.17.3, ok di Tid 2026-10-31). Fino ad allora il controllo chiamava
#       `django.setup()` nel master: i worker nati da un `kill -HUP` ereditavano
#       i moduli gia' caricati, e il codice nuovo non entrava (serviva un
#       `systemctl restart`). Qui Django si carica e muore col figlio.
#       ⚠️ Valori EFFETTIVI: timeout e classe del worker li passa il master
#       dalla sua `cfg`, non si rileggono dall'ambiente.
# ------------------------------------------------------------

from __future__ import annotations

from importlib import import_module
from typing import Any

from django.conf import settings
from django.core.management.base import CommandError, CommandParser

from apps.core.management.comando_aziendale import ComandoAziendale


class Command(ComandoAziendale):
    help = "Presidi di avvio del server web (lo lancia gunicorn.conf.py)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--timeout", type=int, required=True)
        parser.add_argument(
            "--worker-class", required=True,
            help="Percorso puntato della classe del worker (modulo.Classe).",
        )

    # ⭐ Vale solo con la modalita' forte accesa: spenta, il comando non tocca
    #    il DB. ⚠️ Il ramo sta in `execute` e non in `handle`: `ComandoAziendale`
    #    attiva il fuso (che si legge dal DB) prima di `handle`, e un DB che non
    #    risponde fermerebbe l'avvio di gunicorn anche a modalita' spenta.
    def execute(self, *args: Any, **options: Any) -> str | None:
        if not getattr(settings, "API_STRONG_IDEMPOTENCY_ENABLED", False):
            return None
        return super().execute(*args, **options)

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.core.services.soglia_idempotenza import (
            SogliaIdempotenzaNonSicura,
            verifica_soglia_contro_timeout,
        )

        modulo, _, classe = str(options["worker_class"]).rpartition(".")
        worker_class = getattr(import_module(modulo), classe)
        try:
            verifica_soglia_contro_timeout(
                timeout_secondi=int(options["timeout"]), worker_class=worker_class,
            )
        except SogliaIdempotenzaNonSicura as exc:
            raise CommandError(str(exc)) from exc
