# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command — l'`ExecCondition=` delle sveglie CALENDARIALI
#        (`dovuto` in `backend/deploy/sveglie.json`): dice a systemd se il
#        lavoro della sveglia e' dovuto ADESSO, nel fuso dell'AZIENDA.
#
#          run-command.sh e_dovuto zeroerp-digest-presidi-giornaliero
#
#        Il timer si sveglia ogni ora; questo comando risponde:
#          exit 0   -> dovuto: systemd esegue l'`ExecStart` (il `comando`);
#          exit 1   -> non ancora (il periodo aziendale non e' cominciato) o
#                      gia' fatto (una corsa riuscita della corsia dall'inizio
#                      del periodo): systemd salta, SENZA segnare un errore;
#          exit 255 -> guasto (DB irraggiungibile, fuso illeggibile, sveglia
#                      sconosciuta): systemd segna l'unit FALLITA.
#        ⛔ Il 255 non e' un dettaglio: systemd tratta 1-254 come «salta» e
#           basta, quindi un guasto che uscisse 1 — l'uscita di default di
#           un'eccezione Python — farebbe sparire il lavoro in silenzio.
#
#        ⭐ PERCHE' UN COMANDO A PARTE e non un controllo nel comando del
#        lavoro (decisione T-9 di Tid, strada a): il `comando` della sveglia e'
#        anche la riga di «Esegui ora», e il pulsante deve eseguire sempre — il
#        digest rilanciato alle 15:00 dopo quello delle 07:00 deve partire.
#        Brief: work-done/brief-be-db-fe-un-solo-fuso-aziendale.md (B-8, T-4, T-9).
# ------------------------------------------------------------

from __future__ import annotations

import logging
import sys
from typing import Any, NoReturn

from django.core.management.base import CommandParser
from django.utils import timezone

from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.management.comando_aziendale import ComandoAziendale
from apps.core.services.fuso_aziendale import fuso_aziendale
from apps.core.services.sveglie import carica_sveglie, inizio_periodo_dovuto

logger = logging.getLogger(__name__)

USCITA_DOVUTO = 0
USCITA_NON_DOVUTO = 1
USCITA_GUASTO = 255


class Command(ComandoAziendale):
    help = (
        "ExecCondition delle sveglie calendariali: exit 0 se il lavoro e' dovuto "
        "adesso (fuso dell'azienda), 1 se non ancora o gia' fatto, 255 se guasto."
    )

    # Scopo: un solo argomento, la unit della sveglia (come in sveglie.json).
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("unit", help="la unit systemd della sveglia (sveglie.json)")

    # Scopo: ogni guasto — anche quelli che nascono PRIMA di `handle`, come la
    #        lettura del fuso in `execute` — esce 255, non 1. Passa com'e' solo
    #        l'uscita DECISA da `handle` (`_esci`).
    # ⚠️ Non basta lasciar passare ogni `SystemExit`: Django converte un
    #    `CommandError` (anche il fallimento dei system check) in `sys.exit(1)`
    #    e argparse esce 2 su un argomento sbagliato — per systemd sarebbero
    #    entrambi un «salta» silenzioso.
    def run_from_argv(self, argv: list[str]) -> None:
        self._esito: int | None = None
        try:
            super().run_from_argv(argv)
        except SystemExit as exc:
            if self._esito is not None and exc.code == self._esito:
                raise
            logger.error("e_dovuto: uscita %r non decisa dal comando, l'unit va segnata fallita", exc.code)
            sys.exit(USCITA_GUASTO)
        except BaseException:
            logger.exception("e_dovuto: guasto, l'unit va segnata fallita")
            sys.exit(USCITA_GUASTO)
        logger.error("e_dovuto: il comando e' finito senza decidere, l'unit va segnata fallita")
        sys.exit(USCITA_GUASTO)

    # Scopo: l'uscita decisa, ricordata perche' `run_from_argv` la distingua
    #        dalle uscite che Django e argparse producono da se'.
    def _esci(self, codice: int) -> NoReturn:
        self._esito = codice
        sys.exit(codice)

    # Scopo: decide e ESCE col codice che systemd legge.
    def handle(self, *args: Any, **options: Any) -> None:
        unit = options["unit"]
        sveglia = next((s for s in carica_sveglie() if s.unit == unit), None)
        if sveglia is None:
            raise LookupError(f"sveglia sconosciuta: {unit!r} (non e' in sveglie.json)")
        if sveglia.dovuto is None:
            # Una sveglia non calendariale lavora a ogni sveglia.
            self._esci(USCITA_DOVUTO)
        inizio = inizio_periodo_dovuto(sveglia.dovuto, timezone.now(), fuso_aziendale())
        if inizio is None:
            self.stdout.write(f"{unit}: non ancora dovuto (fuso dell'azienda)")
            self._esci(USCITA_NON_DOVUTO)
        repo = MaintenanceRepository()
        # `basta_una_corsa`: una corsa chiusa, anche fallita, fa il periodo
        # (l'esito negativo e' il risultato, non un lavoro da ritentare).
        gia_fatto = (
            repo.corsa_chiusa_dal if sveglia.dovuto.basta_una_corsa else repo.corsa_riuscita_dal
        )
        if gia_fatto(sveglia.dovuto.jobname, inizio):
            self.stdout.write(f"{unit}: gia' fatto dal {inizio.isoformat()}")
            self._esci(USCITA_NON_DOVUTO)
        self.stdout.write(f"{unit}: dovuto dal {inizio.isoformat()}")
        self._esci(USCITA_DOVUTO)
