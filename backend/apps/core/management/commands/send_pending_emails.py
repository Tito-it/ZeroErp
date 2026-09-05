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
from apps.core.services.job_run import ORIGINE_CRON, registered_job
from apps.core.services.processi import PROCESSO_SEND_PENDING_EMAILS

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

    # Scopo: Registra il run e delega al corpo. ⭐ Dal 2026-09-05 questo command
    #        DICE CHI E' (`processo_codice`): prima non si registrava affatto, e
    #        un presidio costruito su `job_run_log` gli era cieco sopra.
    # ⛔ Il DRY-RUN resta FUORI dalla registrazione: non e' un'esecuzione
    #    operativa (stessa regola gia' applicata da `run_fatturazione_batch`).
    # ⚠️ NIENTE `lock_key`: questo command non ne aveva uno prima, e aggiungerlo
    #    ora cambierebbe il comportamento di un processo in esercizio dentro un
    #    cantiere che parla di identita', non di concorrenza.
    # 🔴 QUESTO PROCESSO E' DI DOMINIO E NON HA UN PERIMETRO. `config.email_outbox`
    #    non porta l'emittente, quindi non si puo' lavorare «un'azienda alla
    #    volta»: gli si da' l'ATTORE e basta. Il resto sta nel debito R-7 /
    #    richiesta DB-3 (brief-db-processi-automatici-residui-be) — dichiarato,
    #    non dimenticato.
    def handle(self, *args, **options):
        if options["dry_run"]:
            self._esegui(options)
            return
        with registered_job(
            PROCESSO_SEND_PENDING_EMAILS,
            processo_codice=PROCESSO_SEND_PENDING_EMAILS,
            origine=ORIGINE_CRON,
        ) as job:
            esito = self._esegui(options)
            job.set_meta(esito)
            job.set_rows_affected(esito.get("processate", 0))

    # Scopo: Processa email in coda PENDING/RETRY, con retry automatico
    #        per i FAILED con tentativi < max_tentativi. Ritorna il riepilogo
    #        del giro (vuoto sul dry-run, che non e' un'esecuzione).
    def _esegui(self, options) -> dict:
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
            return {"dry_run": True, "in_coda": count}

        if count == 0:
            self.stdout.write("Nessuna email in coda.")
            return {"processate": 0, "inviate": 0, "fallite": 0}

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

            # Invio via metodo pubblico retry_log_entry
            success = dispatch.retry_log_entry(row["id"], account, log_detail)
            if success:
                sent += 1
            else:
                failed += 1

        self.stdout.write(self.style.SUCCESS(f"Completato: {sent} inviate, {failed} fallite."))
        return {"processate": count, "inviate": sent, "fallite": failed}
