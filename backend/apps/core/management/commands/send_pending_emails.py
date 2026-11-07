# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command per processare le email in coda.
#        ⭐ CHE COSA SIA «in coda» NON LO DECIDE QUESTO FILE: lo dice
#        `config.vw_email_in_coda`, una volta sola, nel database (brief
#        `brief-db-quattro-processi-senza-presidio.md` §10.1 D3, 2026-09-11).
#        Sono in coda le `PENDING`, sempre, e le `RETRY`/`FAILED` con
#        `tentativi < max_tentativi` il cui `prossimo_tentativo` e' gia' dovuto
#        o mai fissato — ma questa frase e' una DESCRIZIONE della vista, non il
#        predicato: il predicato e' la vista, e la legge anche il presidio
#        `dbops.vw_email_da_guardare`, che ci mette sopra la soglia di un'ora.
#        ⛔ Fino al 2026-09-11 la `WHERE` stava qui, e il presidio proposto la
#        ricopiava «PENDING o RETRY» omettendo i `FAILED` ripescabili: due sedi
#        dello stesso predicato, gia' divergenti prima di nascere. Ed era la
#        seconda volta — la riga sopra diceva «PENDING o RETRY» mentre il
#        codice ripescava i `FAILED`, e da quel commento ne era nato un altro
#        sbagliato in `email_service`. *Un commento non e' una fonte; e nemmeno
#        una `SELECT` ricopiata lo e'.* Adesso la sede e' una.
#        Svegliato da un timer systemd (`zeroerp-send-pending-emails.timer`),
#        non da crontab — vedi `backend/deploy/sveglie.json`.
# ------------------------------------------------------------

from __future__ import annotations

import logging

from apps.core.management.comando_aziendale import ComandoAziendale
from django.db import connection

from apps.core.db._helpers import rows_to_list
from apps.core.db.email_repository import EmailRepository
from apps.core.services.giro_per_azienda import giro_per_azienda
from apps.core.services.email_service import EmailDispatchService
from apps.core.services.job_run import (
    ORIGINE_CRON,
    chiudi_se_elementi_non_completati,
    registered_job,
)
from apps.core.services.processi import PROCESSO_SEND_PENDING_EMAILS

logger = logging.getLogger("zeroerp.email")


class Command(ComandoAziendale):
    help = (
        "Processa la coda email: PENDING sempre, piu' FAILED e RETRY finche' "
        "restano tentativi. Svegliato da un timer systemd."
    )

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
            # ⭐ Un badge fallito non lascia righe in `config.email_log`: le sue
            #    email restano in coda senza che nessuno le abbia provate. Le
            #    email fallite una per una no, quelle le vede il loro presidio (D9).
            chiudi_se_elementi_non_completati(
                job, [b["emittente_codice"] for b in esito.get("badge_falliti", [])],
                cosa="aziende con il giro delle email non eseguito",
            )

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
        # ⭐ Il giro (roster, identita', isolamento, non serviti) e' il BB
        #    `giro_per_azienda` (regola del 2, 2026-11-07).
        # ⛔ UN'AZIENDA CHE FALLISCE NON PORTA VIA LE ALTRE: bastava un badge con
        #    l'identita' spenta (`E_CODA_IDENTITA_NON_ATTIVA`) per fermare
        #    l'INTERO giro — zero email spedite, reset password compresi. Lo
        #    garantisce il BB.
        giro = giro_per_azienda(
            PROCESSO_SEND_PENDING_EMAILS,
            lambda _badge: self._esegui_giro(options),
            evento="send_pending_emails",
            on_badge=self._scrivi_badge_fallito,
        )

        if giro.roster_vuoto:
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
        for badge, parziale in giro.serviti:
            for chiave in totali:
                totali[chiave] += parziale.get(chiave, 0)
            per_emittente.append({
                "emittente_codice": badge["emittente_codice"], **parziale,
            })
        if giro.non_serviti:
            # ⭐ Il numero che rompe il silenzio, come per la fatturazione: senza
            #    badge quell'azienda non viene servita, e il giro chiuderebbe
            #    «FATTO» avendola saltata.
            self.stderr.write(self.style.WARNING(
                "⚠️  Aziende senza utente tecnico, non servite: "
                + ", ".join(giro.non_serviti)
            ))
        return {
            **totali,
            "per_emittente": per_emittente,
            # ⭐ Due assenze DIVERSE, e tenerle separate e' il punto: «non ha un
            #    badge» si ripara creando l'utente tecnico, «il badge non ha
            #    funzionato» si ripara guardando l'errore. Un elenco solo
            #    manderebbe a fare la cosa sbagliata.
            "badge_falliti": giro.falliti,
            "emittenti_non_serviti": giro.non_serviti,
        }

    # Scopo: la riga di console di un'azienda il cui giro non e' partito
    #        (callback del BB; i riusciti non scrivono niente qui).
    def _scrivi_badge_fallito(self, badge, _esito, errore) -> None:
        if errore is not None:
            self.stderr.write(self.style.ERROR(
                f"⛔ {badge['emittente_codice']}: giro non eseguito — {errore}"
            ))

    # Scopo: Processa la coda email — le righe che `config.vw_email_in_coda`
    #        dice essere ancora in coda (vedi header: il predicato e' la vista).
    #        ⚠️ `SIMULATA` NON e' in coda: e' terminale di proposito (la mail e'
    #        stata mostrata, non spedita, e ritentarla non la farebbe partire) —
    #        lo esclude la vista, non questo file.
    #        Ritorna il riepilogo
    #        del giro (vuoto sul dry-run, che non e' un'esecuzione).
    # ⚠️ Gira DENTRO l'identita' impostata dal chiamante: qui non si apre nessun
    #    contesto, o sarebbero due sedi a deciderlo. E la vista e'
    #    `security_invoker`: si legge col perimetro di quell'identita', esattamente
    #    come la tabella sotto — il cambio di sede non cambia cio' che si vede.
    def _esegui_giro(self, options) -> dict:
        dry_run = options["dry_run"]
        limit = options["limit"]

        # Seleziona email da processare
        # ⛔ Nessuna `WHERE` sullo stato: e' la vista a dire chi e' in coda.
        #    Aggiungerne una qui sarebbe la seconda sede, quella che si dimentica.
        sql = """
            SELECT id, destinatario, oggetto, stato, tentativi, max_tentativi,
                   email_account_id,
                   -- ⚠️ Serve a scegliere la PORTA con cui si scrive l'esito:
                   --    una riga `SISTEMA` non si aggiorna con un UPDATE
                   --    diretto (policy RLS), passa da `fn_chiudi_email_sistema`.
                   ambito
              FROM config.vw_email_in_coda
             ORDER BY data_insert
             LIMIT %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [limit])
            rows = rows_to_list(cursor)

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
