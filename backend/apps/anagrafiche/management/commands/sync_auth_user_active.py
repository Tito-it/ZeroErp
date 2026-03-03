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
from apps.core.services.permissions_cache import invalidate_user

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

    # Scopo: Esegue la sync batch degli utenti scaduti.
    # Flusso: raccoglie gli auth_user_id coinvolti, chiama la funzione SQL
    # di sync, poi invalida la cache permessi per ciascun utente modificato.
    def handle(self, *args: Any, **options: Any) -> None:
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
                return

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"[DRY-RUN] {len(affected_ids)} utenti sarebbero disattivati: "
                        f"auth_user_id = {affected_ids}"
                    )
                )
                return

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

        except Exception as exc:
            logger.exception("Errore in sync_auth_user_active")
            raise CommandError(
                f"Errore durante la sync: {exc}"
            ) from exc
