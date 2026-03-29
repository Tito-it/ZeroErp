# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command per processare email in coda
#        (stato PENDING o RETRY con tentativi < max_tentativi).
#        Eseguibile come cron job (pgAgent o crontab).
# ------------------------------------------------------------

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.db import connection

from apps.core.db.email_repository import EmailRepository
from apps.core.services.email_service import EmailDispatchService

logger = logging.getLogger("zeroerp.email")


class Command(BaseCommand):
    help = "Processa email in coda (PENDING/RETRY). Eseguibile come cron job."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Mostra quante email verrebbero processate senza inviarle.",
        )
        parser.add_argument(
            "--limit", type=int, default=50,
            help="Numero massimo di email da processare (default 50).",
        )

    # Scopo: Processa email in coda PENDING/RETRY, con retry automatico
    #        per i FAILED con tentativi < max_tentativi.
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        # Seleziona email da processare
        sql = """
            SELECT id, destinatario, oggetto, stato, tentativi, max_tentativi,
                   email_account_id
              FROM config.email_log
             WHERE (stato = 'PENDING'
                    OR (stato IN ('FAILED', 'RETRY')
                        AND tentativi < max_tentativi
                        AND (prossimo_tentativo IS NULL OR prossimo_tentativo <= now())))
             ORDER BY data_insert
             LIMIT %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [limit])
            cols = [c.name for c in cursor.description]
            rows = [dict(zip(cols, r)) for r in cursor.fetchall()]

        count = len(rows)
        if dry_run:
            self.stdout.write(f"[DRY-RUN] {count} email in coda da processare.")
            for r in rows:
                self.stdout.write(f"  id={r['id']} stato={r['stato']} dest={r['destinatario']} tentativi={r['tentativi']}/{r['max_tentativi']}")
            return

        if count == 0:
            self.stdout.write("Nessuna email in coda.")
            return

        self.stdout.write(f"Processando {count} email...")
        repo = EmailRepository()
        dispatch = EmailDispatchService()

        sent = 0
        failed = 0
        for row in rows:
            # Risolvi account: usa quello specifico del log, con fallback a SISTEMA
            account_id = row.get("email_account_id")
            if account_id:
                account = repo.get_account_with_password(account_id)
            else:
                account = repo.resolve_account()
            if not account:
                repo.update_log_stato(row["id"], "FAILED", errore="Nessun account SMTP configurato")
                failed += 1
                continue

            # Recupera corpo dal log
            log_detail = repo.get_log(row["id"])
            if not log_detail:
                failed += 1
                continue

            # Invio via _send_smtp (gestisce log stato internamente)
            success = dispatch._send_smtp(
                account,
                row["destinatario"],
                log_detail.get("destinatari_cc"),
                row["oggetto"],
                log_detail.get("corpo_inviato_html", ""),
                log_detail.get("corpo_inviato_testo"),
                row["id"],
            )
            if success:
                sent += 1
            else:
                failed += 1

        self.stdout.write(self.style.SUCCESS(f"Completato: {sent} inviate, {failed} fallite."))
