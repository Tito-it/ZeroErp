# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command del DIGEST DEI PRESIDI — porta davanti a una persona
#        cio' che le viste di presidio di `dbops` dicono, e che finora non
#        leggeva nessuno.
# Note: ⭐ NASCE DA UN FATTO. Il 2026-09-09 il job `CHIUSURA_SCADENZE` risultava
#        fallito quattro notti consecutive: le righe stavano in
#        `dbops.vw_coda_lavori_da_guardare` — una vista che porta nel nome cio'
#        che serviva — e sono rimaste li'. Il presidio aveva funzionato
#        perfettamente: *guardare non era di nessuno*.
#
#        ⛔ IL COMMAND NON SA QUALI VISTE ESISTONO. Chiede al catalogo «cosa
#        guardo a questa cadenza» e mette in fila la risposta: un elenco qui
#        sarebbe la seconda sorgente di verita' che il cantiere esiste per non
#        avere, e diverge il giorno in cui nasce la vista successiva.
#
#        ⭐ SI PUO' LANCIARE A MANO DA SUBITO (`--secco`): un digest che si puo'
#        guardare quando si vuole e' gia' meglio di niente, e non aspetta ne'
#        una sveglia ne' un destinatario.
#
#        ⚠️ Senza destinatario configurato il digest si calcola LO STESSO e lo
#        dichiara — in coda al proprio esito e nel `meta` del run. Un invio che
#        non parte in silenzio sarebbe la prima cosa da non fare qui.
#
#        Brief: work-done/brief-db-un-destinatario-per-i-presidi.md §5, §8.2.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.conf import settings
from apps.core.management.comando_aziendale import ComandoAziendale

from apps.core.db.presidi_repository import CADENZA_GIORNALIERA
from apps.core.services.job_run import ORIGINE_CRON, registered_job
from apps.core.services.presidi_digest import (
    CADENZE_DEL_DIGEST,
    Digest,
    accoda_email_presidi,
    calcola_digest,
    componi_messaggio,
    jobname_corsia,
    separa_destinatari,
)
from apps.core.services.processi import PROCESSO_DIGEST_PRESIDI

# ⛔ Nessun `logger` in questo modulo, ed e' voluto: cio' che questo command ha
#    da dire va su stdout/stderr (lo raccoglie il journal dell'unit) e nel `meta`
#    del run. Un logger dichiarato e mai usato sembra un canale e non lo e' — ed
#    e' proprio da un `logger.info` che il precedente
#    `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL` non e' stato visto da nessuno.

# Le cadenze come si scrivono sulla riga di comando.
# ⭐ SI DERIVANO da quelle del digest, che a loro volta si derivano dal
#    vocabolario del catalogo: qui si normalizza soltanto il maiuscolo. Un
#    elenco scritto a mano resterebbe indietro alla prima cadenza nuova, e
#    quella cadenza non sarebbe lanciabile — con l'aria di non esistere.
_CADENZE_CLI = {cadenza.lower(): cadenza for cadenza in CADENZE_DEL_DIGEST}

# ⭐ `separa_destinatari` NON STA PIU' QUI (2026-09-11): la legge anche
#    l'handler `notifica_digest_muto`, che avvisa la stessa persona quando il
#    digest tace. Alla seconda occorrenza il pezzo e' salito nel service
#    (`presidi_digest.separa_destinatari`) — e questo command la importa.

# I tre esiti dell'invio, e sono TRE di proposito: «non c'era niente da dire» e
# «non c'e' nessuno a cui dirlo» sono opposti, e appiattirli su «non inviato»
# nasconderebbe proprio la configurazione che manca.
INVIO_NON_RICHIESTO = "NON_RICHIESTO"
INVIO_NON_CONFIGURATO = "NON_CONFIGURATO"
INVIO_ACCODATO = "ACCODATO"


class Command(ComandoAziendale):
    help = (
        "Digest dei presidi: legge dbops.presidi, conta le righe che chiedono "
        "un intervento e le manda al destinatario configurato."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--cadenza",
            choices=sorted(_CADENZE_CLI),
            # ⚠️ Legato alla costante e non scritto: il default e' una scelta
            #    (gli allarmi si guardano ogni giorno), ma il suo NOME viene dal
            #    catalogo.
            default=CADENZA_GIORNALIERA.lower(),
            help=(
                "Quale gruppo di presidi guardare. Il catalogo dice per ognuno "
                "ogni quanto va guardato (dbops.presidi.cadenza)."
            ),
        )
        parser.add_argument(
            "--secco", action="store_true",
            help="Calcola e stampa il digest senza inviarlo e senza registrare il run.",
        )

    # Scopo: Registra il run e delega al corpo.
    # ⛔ IL `--secco` RESTA FUORI DALLA REGISTRAZIONE: non e' un'esecuzione
    #    operativa, ed e' la stessa regola gia' applicata da `run_fatturazione_batch`
    #    e da `send_pending_emails`. Un run registrato per ogni sbirciata
    #    sposterebbe in avanti «l'ultima corsa» del processo — cioe' renderebbe
    #    verde il battito proprio mentre il timer e' fermo.
    # ⚠️ `job_name` porta la CORSIA (`digest_presidi:settimanale`) e
    #    `processo_codice` no: e' la stessa forma di `run_fatturazione_batch`, e
    #    serve al battito per dire quando ha girato ciascuna delle due.
    def handle(self, *args: Any, **options: Any) -> None:
        cadenza = _CADENZE_CLI[options["cadenza"]]

        if options["secco"]:
            digest = calcola_digest(cadenza)
            oggetto, testo, _html = componi_messaggio(digest)
            self.stdout.write(oggetto)
            self.stdout.write("")
            self.stdout.write(testo)
            self.stdout.write("")
            # ⭐ Chi lancia `--secco` di solito si sta chiedendo «perche' non
            #    ricevo niente?»: dire «da inviare: si» e tacere sul
            #    destinatario risponderebbe a meta'.
            destinatario, copie = separa_destinatari(
                settings.PRESIDI_DIGEST_DESTINATARIO,
            )
            a_chi = (
                f"{destinatario}" + (f" (+{len(copie)} in copia)" if copie else "")
                if destinatario
                else "NESSUNO — ZEROERP_PRESIDI_DIGEST_DESTINATARIO non "
                     "configurato in backend/.env.systemd"
            )
            self.stdout.write(
                f"[SECCO] nessun invio, nessun run registrato. "
                f"Da inviare: {'si' if digest.da_inviare else 'no'}. "
                f"Destinatario: {a_chi}."
            )
            return

        with registered_job(
            # ⚠️ Il nome della corsia lo compone il modulo del digest, che e'
            #    anche chi lo RITROVA nel battito: scritto qui sarebbe la stessa
            #    forma in due sedi, e la seconda non si accorge del cambio.
            jobname_corsia(cadenza),
            processo_codice=PROCESSO_DIGEST_PRESIDI,
            origine=ORIGINE_CRON,
            stepname=cadenza,
        ) as job:
            digest = calcola_digest(cadenza)
            # ⚠️ Il messaggio si compone UNA volta e si passa: comporlo due
            #    volte non e' solo lavoro doppio — sono due composizioni che
            #    possono divergere, e a video ne finisce una sola.
            messaggio = componi_messaggio(digest)
            esito = digest.riepilogo()
            esito["inviato"] = self._invia(digest, messaggio)
            job.set_meta(esito)
            # ⚠️ `rows_affected` porta le righe IN ALLARME, non i presidi: e' il
            #    numero che dice quanto lavoro c'e', ed e' quello che si legge
            #    scorrendo il giornale dei run.
            job.set_rows_affected(sum(v.conteggio for v in digest.allarmi))
            job.set_message(
                f"{esito['allarmi']} allarmi, {esito['registri']} registri, "
                f"{esito['non_letti']} non letti — invio {esito['inviato']}"
            )
            self._racconta(messaggio, esito)

    # Scopo: Invia il digest, se c'e' motivo di inviarlo e se c'e' un
    #        destinatario. Ritorna quale dei tre esiti si e' verificato.
    #
    # ⭐ Il «come si scrive alla persona dei presidi» sta in
    #    `presidi_digest.accoda_email_presidi` (dal 2026-09-11), che e' anche
    #    quello dell'handler del guardiano: qui resta solo la decisione — se
    #    c'e' motivo di inviare, e come chiamare l'esito.
    def _invia(self, digest: Digest, messaggio: tuple[str, str, str]) -> str:
        if not digest.da_inviare:
            return INVIO_NON_RICHIESTO

        oggetto, testo, corpo_html = messaggio
        accodata = accoda_email_presidi(
            oggetto=oggetto,
            testo=testo,
            corpo_html=corpo_html,
            # ⭐ Il contesto viaggia con la riga: chi legge il giornale delle
            #    email deve poter dire QUALE giro l'ha prodotta senza aprirla.
            contesto_json={
                "processo": PROCESSO_DIGEST_PRESIDI,
                "cadenza": digest.cadenza,
                **digest.riepilogo(),
            },
        )
        return INVIO_ACCODATO if accodata is not None else INVIO_NON_CONFIGURATO

    # Scopo: Racconta il giro a chi lo sta guardando (o al giornale di systemd).
    # ⛔ IL «NON CONFIGURATO» NON E' UN `logger.info`, ed e' il difetto gia'
    #    pagato da `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL`: quel
    #    destinatario non e' mai stato configurato, l'email non e' MAI partita, e
    #    l'unica traccia era una riga di log che nessuno leggeva. Qui esce su
    #    stderr E resta nel `meta` del run, dove chi guarda le corse lo vede
    #    senza cercarlo.
    def _racconta(self, messaggio: tuple[str, str, str], esito: dict[str, Any]) -> None:
        _oggetto, testo, _html = messaggio
        self.stdout.write(testo)
        if esito["inviato"] == INVIO_ACCODATO:
            self.stdout.write(self.style.SUCCESS("Digest accodato per l'invio."))
            return
        if esito["inviato"] == INVIO_NON_RICHIESTO:
            self.stdout.write(
                "Nessun invio: niente da segnalare a questa cadenza."
            )
            return
        self.stderr.write(self.style.WARNING(
            "⚠️  Digest calcolato, NESSUN DESTINATARIO CONFIGURATO: non e' stato "
            "inviato. Valorizzare ZEROERP_PRESIDI_DIGEST_DESTINATARIO in "
            "backend/.env.systemd (per-host, non versionato)."
        ))
