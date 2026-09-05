# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command long-running per avvio del listener
#        LISTEN/NOTIFY sul canale 'cambio_reparto'.
#        Invalida la cache permessi quando un utente cambia reparto.
# Note: Pensato per essere eseguito come processo dedicato
#        (systemd, supervisor, o in foreground durante lo sviluppo).
# ------------------------------------------------------------

from __future__ import annotations

import logging
import os
import socket
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.anagrafiche.services.notify_listener import (
    DEFAULT_POLL_INTERVAL,
    CambioRepartoListener,
)
from apps.core.services.job_run import ORIGINE_CRON, registered_job
from apps.core.services.processi import PROCESSO_LISTEN_CAMBIO_REPARTO

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Avvia il listener LISTEN/NOTIFY per il canale 'cambio_reparto'. "
        "Invalida la cache permessi quando un utente cambia reparto. "
        "Processo long-running: terminare con SIGINT (Ctrl+C) o SIGTERM."
    )

    # Scopo: Registra argomenti CLI del command.
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=DEFAULT_POLL_INTERVAL,
            help=(
                f"Intervallo di polling in secondi per le notifiche "
                f"(default: {DEFAULT_POLL_INTERVAL})."
            ),
        )

    # Scopo: Avvia il listener. Blocca fino a SIGINT/SIGTERM.
    #
    # ⭐ RUN DI AVVIO, non run lungo quanto il processo (decisione di Tid,
    #   2026-09-05). La riga si apre e si chiude SUBITO, prima di entrare nel
    #   ciclo: dice «questo listener e' partito, qui, alle ore X».
    # ⛔ Le due forme scartate rispondono male alla stessa domanda. Un run che
    #   dura quanto il processo resta «aperto» per settimane — e su una morte
    #   improvvisa resta aperto per sempre, quindi il giornale non distingue
    #   «sta lavorando» da «e' morto». Un run per riconnessione parla solo
    #   quando c'e' un singhiozzo: in un mese tranquillo «funziona benissimo» e
    #   «non e' mai partito» si scrivono allo stesso modo, cioe' non si
    #   scrivono.
    # ⚠️ E il run di avvio NON risponde a «e' vivo adesso?». Non e' una
    #   mancanza: e' una domanda DIVERSA, e nel progetto ha gia' la sua sede —
    #   `MaintenanceRepository.job_liveness` (ultimo run entro soglia,
    #   confrontato col clock del DB), quella che accende il pallino del badge
    #   code in topbar. Il battito periodico di un listener e' un cantiere suo e
    #   si aggancia li', invece di inventare un secondo meccanismo qui.
    def handle(self, *args: Any, **options: Any) -> None:
        poll_interval: float = options["poll_interval"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Avvio listener cambio_reparto (poll_interval={poll_interval}s)..."
            )
        )

        # ⚠️ Il `with` si CHIUDE prima del ciclo: e' esattamente il punto.
        with registered_job(
            PROCESSO_LISTEN_CAMBIO_REPARTO,
            processo_codice=PROCESSO_LISTEN_CAMBIO_REPARTO,
            origine=ORIGINE_CRON,
        ) as job:
            job.set_message("listener avviato")
            job.set_meta({
                "host": socket.gethostname(),
                "pid": os.getpid(),
                "poll_interval": poll_interval,
            })

        try:
            listener = CambioRepartoListener(poll_interval=poll_interval)
            listener.run()
        except Exception as exc:
            logger.exception("Errore nel listener cambio_reparto")
            raise CommandError(
                f"Errore nel listener: {exc}"
            ) from exc

        self.stdout.write(self.style.SUCCESS("Listener terminato."))
