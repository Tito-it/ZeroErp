# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command per processare email in coda: `PENDING` sempre,
#        piu' `FAILED` e `RETRY` finche' `tentativi < max_tentativi` e il
#        `prossimo_tentativo` e' scaduto (la SELECT autorevole e' nel corpo).
#        ⚠️ Questa riga diceva «PENDING o RETRY» e OMETTEVA `FAILED`: il
#        2026-09-11 quell'omissione ha portato a scrivere, in `email_service`,
#        un commento che affermava il contrario di cio' che il codice fa —
#        «una riga FAILED non torna in coda». *Un commento non e' una fonte:
#        se descrive un predicato, va riletto contro il predicato.*
#        Svegliato da un timer systemd (`zeroerp-send-pending-emails.timer`),
#        non da crontab — vedi `backend/deploy/sveglie.json`.
# ------------------------------------------------------------

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.db import connection

from apps.core.db.email_repository import EmailRepository
from apps.core.db.processi_repository import ProcessiRepository
from apps.core.services.coda_lavori.context import operator_identity_context
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
    # ⭐ DAL 2026-09-05 IL PROCESSO DICE CHI E' ANCHE AL DATABASE. Prima si
    #    registrava soltanto nel giornale dei run: le GUC `app.current_user_id` e
    #    `app.ruolo_applicativo` le scrive l'autenticazione JWT, e in un command
    #    non ci sono — quindi a database questa connessione era anonima. Adesso
    #    il giro passa dal ROSTER e ogni azienda viene servita dentro l'identita'
    #    del proprio utente tecnico. Brief: brief-db-processi-automatici-residui-be
    #    §1-octies, punto 3.
    def handle(self, *args, **options):
        if options["dry_run"]:
            # ⚠️ IL DRY-RUN NON PASSA DAL ROSTER, ed e' voluto. `config.email_log`
            #    non ha ancora un perimetro: iterando le aziende ogni giro
            #    vedrebbe le STESSE righe, e l'anteprima direbbe «3 email» due
            #    volte facendone sembrare sei. Un'anteprima che non torna e'
            #    peggio di nessuna anteprima.
            # ⇒ Una passata sola, che e' esattamente cio' che la coda contiene.
            #    Quando la colonna emittente arrivera' (punto 4 del team DB),
            #    anche questa diventera' per azienda.
            self.stdout.write(
                "[DRY-RUN] la coda non ha ancora un perimetro per azienda: "
                "quella che segue e' la coda intera."
            )
            self._esegui_giro(options)
            return
        with registered_job(
            PROCESSO_SEND_PENDING_EMAILS,
            processo_codice=PROCESSO_SEND_PENDING_EMAILS,
            origine=ORIGINE_CRON,
        ) as job:
            esito = self._esegui(options)
            job.set_meta(esito)
            job.set_rows_affected(esito.get("processate", 0))

    # Scopo: Il giro completo — un'azienda alla volta, ciascuna con l'identita'
    #        del proprio utente tecnico. Ritorna il riepilogo aggregato.
    #
    # ⚠️ CHE COSA CAMBIA OGGI, E CHE COSA NO. `config.email_log` — la coda che
    #    questo command drena — non porta ancora l'emittente e non ha policy:
    #    quindi l'identita' NON separa ancora il lavoro, e la prima azienda del
    #    roster si porta via tutta la coda mentre le altre non trovano niente.
    #    ⭐ Non e' un difetto di questo ciclo: e' il perimetro che manca nel
    #    DATO, ed e' il punto 4 del team DB. Quando la colonna arriva, questo
    #    codice diventa per-azienda senza cambiare una riga.
    # ⛔ E i numeri per azienda NON vanno letti come un perimetro finche' e'
    #    cosi': dicono chi ha girato, non di chi era il lavoro.
    #
    # 🔴 ROSTER VUOTO: SI SPEDISCE LO STESSO, ad alta voce. Su un database
    #    ricostruito da zero gli utenti tecnici non ci sono (seed
    #    `dati_macchina`): fermarsi trasformerebbe un'identita' mancante nel
    #    silenzio totale delle email — reset password compresi — che e'
    #    esattamente il guasto-per-assenza che questo cantiere esiste per
    #    togliere. ⇒ Si esegue senza identita' e lo si DICE.
    def _esegui(self, options) -> dict:
        processi_repo = ProcessiRepository()
        roster = processi_repo.roster_processo(PROCESSO_SEND_PENDING_EMAILS)

        if not roster:
            self.stderr.write(self.style.WARNING(
                "⚠️  Nessun utente tecnico per send_pending_emails: il giro "
                "parte SENZA identita' a database. Le email vengono spedite "
                "lo stesso; il perimetro no."
            ))
            esito = self._esegui_giro(options)
            esito["senza_identita"] = True
            return esito

        totali = {"processate": 0, "inviate": 0, "fallite": 0}
        per_emittente: list[dict] = []
        # ⛔ UN'AZIENDA CHE FALLISCE NON PORTA VIA LE ALTRE, ed e' la stessa
        #    forma gia' provata in `draina_coda_stampa_per_roster`. Senza,
        #    bastava un badge con l'identita' spenta — `operator_identity_context`
        #    solleva `E_CODA_IDENTITA_NON_ATTIVA` — per fermare l'INTERO giro:
        #    zero email spedite, reset password compresi. Sarebbe stato lo stesso
        #    guasto-per-assenza che il ramo «roster vuoto» qui sopra evita,
        #    lasciato aperto dall'altro lato.
        badge_falliti: list[dict] = []
        for badge in roster:
            try:
                with operator_identity_context(
                    badge["auth_user_id"],
                    username=badge["username"],
                    identita_id=badge["identita_id"],
                    emittente_attivo_id=badge["emittente_fiscale_id"],
                ):
                    parziale = self._esegui_giro(options)
            except Exception as exc:  # noqa: BLE001 — isolamento per azienda voluto
                logger.warning(
                    "send_pending_emails.azienda_fallita emittente=%s badge=%s errore=%s",
                    badge["emittente_codice"], badge["username"], exc, exc_info=True,
                )
                badge_falliti.append({
                    "emittente_codice": badge["emittente_codice"], "errore": str(exc),
                })
                self.stderr.write(self.style.ERROR(
                    f"⛔ {badge['emittente_codice']}: giro non eseguito — {exc}"
                ))
                continue
            for chiave in totali:
                totali[chiave] += parziale.get(chiave, 0)
            per_emittente.append({
                "emittente_codice": badge["emittente_codice"], **parziale,
            })
        scoperti = processi_repo.emittenti_non_serviti(PROCESSO_SEND_PENDING_EMAILS)
        if scoperti:
            # ⭐ Il numero che rompe il silenzio, come per la fatturazione: senza
            #    badge quell'azienda non viene servita, e il giro chiuderebbe
            #    «FATTO» avendola saltata.
            self.stderr.write(self.style.WARNING(
                "⚠️  Aziende senza utente tecnico, non servite: "
                + ", ".join(e["emittente_codice"] for e in scoperti)
            ))
        return {
            **totali,
            "per_emittente": per_emittente,
            # ⭐ Due assenze DIVERSE, e tenerle separate e' il punto: «non ha un
            #    badge» si ripara creando l'utente tecnico, «il badge non ha
            #    funzionato» si ripara guardando l'errore. Un elenco solo
            #    manderebbe a fare la cosa sbagliata.
            "badge_falliti": badge_falliti,
            "emittenti_non_serviti": [e["emittente_codice"] for e in scoperti],
        }

    # Scopo: Processa email in coda PENDING/RETRY, con retry automatico
    #        per i FAILED con tentativi < max_tentativi. Ritorna il riepilogo
    #        del giro (vuoto sul dry-run, che non e' un'esecuzione).
    # ⚠️ Gira DENTRO l'identita' impostata dal chiamante: qui non si apre nessun
    #    contesto, o sarebbero due sedi a deciderlo.
    def _esegui_giro(self, options) -> dict:
        dry_run = options["dry_run"]
        limit = options["limit"]

        # Seleziona email da processare
        sql = """
            SELECT id, destinatario, oggetto, stato, tentativi, max_tentativi,
                   email_account_id,
                   -- ⚠️ Serve a scegliere la PORTA con cui si scrive l'esito:
                   --    una riga `SISTEMA` non si aggiorna con un UPDATE
                   --    diretto (policy RLS), passa da `fn_chiudi_email_sistema`.
                   ambito
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
                repo.update_log_stato(
                    row["id"], "FAILED", ambito=row["ambito"],
                    errore="Nessun account SMTP configurato",
                )
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
