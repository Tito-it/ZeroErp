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
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.anagrafiche.services.notify_listener import (
    DEFAULT_POLL_INTERVAL,
    CambioRepartoListener,
)

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
    def handle(self, *args: Any, **options: Any) -> None:
        poll_interval: float = options["poll_interval"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Avvio listener cambio_reparto (poll_interval={poll_interval}s)..."
            )
        )

        try:
            listener = CambioRepartoListener(poll_interval=poll_interval)
            listener.run()
        except Exception as exc:
            logger.exception("Errore nel listener cambio_reparto")
            raise CommandError(
                f"Errore nel listener: {exc}"
            ) from exc

        self.stdout.write(self.style.SUCCESS("Listener terminato."))
