# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command per disattivazione batch auth_user
#        con finestra temporale scaduta. Wrapper Django per
#        anagrafiche.fn_sync_auth_user_expired() con invalidazione
#        cache permessi per gli utenti coinvolti.
# Note: Alternativa a pgAgent job sync_auth_user_expired_daily.
#       Utilizzabile da cron/systemd.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.anagrafiche.db.anagrafiche_repository import AnagraficheRepository
from apps.core.services.job_run import ORIGINE_CRON, registered_job
from apps.core.services.permissions_cache import invalidate_user
from apps.core.services.processi import PROCESSO_SYNC_AUTH_USER_ACTIVE

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Disattiva auth_user per risorse umane con finestra temporale scaduta. "
        "Wrapper per anagrafiche.fn_sync_auth_user_expired() con invalidazione "
        "cache permessi."
    )

    # Scopo: Registra argomenti CLI del command.
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo report: mostra gli utenti che sarebbero disattivati senza applicare modifiche.",
        )

    # Scopo: Registra il run e delega al corpo. ⭐ Dal 2026-09-05 questo command
    #        DICE CHI E': prima non si registrava affatto, quindi qualunque
    #        presidio costruito su `job_run_log` gli era cieco sopra.
    # ⛔ Il DRY-RUN resta fuori dalla registrazione: e' un report, non
    #    un'esecuzione operativa.
    # ⚠️ Classe AMMINISTRAZIONE: tocca dati che non appartengono a un emittente
    #    (`auth_user`, `risorse_umane`), quindi NON ha un utente tecnico e non
    #    itera per azienda. L'attore basta — e' esattamente la distinzione della
    #    D-8 dell'analisi.
    def handle(self, *args: Any, **options: Any) -> None:
        if options["dry_run"]:
            self._esegui(options)
            return
        with registered_job(
            PROCESSO_SYNC_AUTH_USER_ACTIVE,
            processo_codice=PROCESSO_SYNC_AUTH_USER_ACTIVE,
            origine=ORIGINE_CRON,
        ) as job:
            esito = self._esegui(options)
            job.set_meta(esito)
            job.set_rows_affected(esito.get("disattivati", 0))

    # Scopo: Esegue la sync batch degli utenti scaduti e ritorna il riepilogo.
    # Flusso: raccoglie gli auth_user_id coinvolti, chiama la funzione SQL
    # di sync, poi invalida la cache permessi per ciascun utente modificato.
    def _esegui(self, options: Any) -> dict:
        dry_run: bool = options["dry_run"]
        repository = AnagraficheRepository()

        try:
            # Fase 1: individuazione utenti con finestra scaduta
            affected_ids = repository.list_expired_auth_user_ids()

            if not affected_ids:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Nessun utente con finestra temporale scaduta."
                    )
                )
                return {"disattivati": 0, "cache_invalidata": 0}

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"[DRY-RUN] {len(affected_ids)} utenti sarebbero disattivati: "
                        f"auth_user_id = {affected_ids}"
                    )
                )
                return {"dry_run": True, "candidati": len(affected_ids)}

            # Fase 2: esecuzione sync SQL
            count = repository.call_sync_auth_user_expired()

            # Fase 3: invalidazione cache permessi
            invalidated = 0
            for user_id in affected_ids:
                invalidate_user(user_id)
                invalidated += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Sync completata: {count} utenti disattivati, "
                    f"cache invalidata per {invalidated} utenti."
                )
            )

            logger.info(
                "sync_auth_user_active: disattivati=%d, cache_invalidata=%d, "
                "auth_user_ids=%s",
                count,
                invalidated,
                affected_ids,
            )
            return {"disattivati": count, "cache_invalidata": invalidated}

        except Exception as exc:
            logger.exception("Errore in sync_auth_user_active")
            raise CommandError(
                f"Errore durante la sync: {exc}"
            ) from exc
