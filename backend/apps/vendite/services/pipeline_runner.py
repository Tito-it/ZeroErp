# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestrazione esecuzione pipeline vendite.
# ------------------------------------------------------------


from dataclasses import dataclass, replace
from datetime import date
from collections.abc import Callable
from uuid import uuid4
from typing import Any

from django.db import transaction

from apps.core.services.db_error_fields import bersagli_envelope
from apps.core.services.diagnostica_best_effort import diagnostica_best_effort
from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services.lotto_segnalazioni_service import LottoSegnalazioniService
from apps.vendite.types import LottoPipelineMeta, PipelineStepLogMeta
from apps.vendite.services.pipeline_error_logger import PipelineErrorLogger
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor

# Orchestratore applicativo della pipeline lotto vendite.

@dataclass(frozen=True)
class LottoPipelineParams:
    lotto_id: int | None = None
    competenza_mese: date | None = None
    tipo_doc_fiscale_id: int | None = None
    utility_id: int | None = None
    billing_account_id: int | None = None
    emittente_soggetto_ruolo_id: int | None = None
    lock_batch_id: str | None = None
    meta: LottoPipelineMeta | None = None
    dry_run: bool = False
    tipo_lotto: str = "MASSIVO"
    # C-1 (gate fiscale D-1): id stato_doc_fiscale a cui FERMARSI in
    # run_lotto_until_done (raggiunto lo stato, la catena si arresta con
    # motivo FERMATO_A_STATO). None = fino in fondo (comportamento storico).
    # Confronto Python puro: la risoluzione codice->id sta nel chiamante.
    fino_a_stato_doc_fiscale_id: int | None = None
    # EMISSIONE MIRATA (brief emissione mirata, D-3): chiavi dei gruppi
    # fatturabili da lavorare. Persistite sul lotto alla creazione — NON sono
    # un parametro che viaggia fino agli step. None = nessuna restrizione.
    gruppi: tuple[str, ...] | None = None


# Scopo: Il `meta` della riga di `vendite.fatture_log` che racconta un
#        fallimento per-fattura.
#
# ⚠️ La chiave `bersagli` si mette SOLO se c'e' qualcosa da dire — mai a `null`.
#    E' la stessa disciplina che il team DB ha scritto nel pilota: una chiave
#    presente e inutilizzabile non vuol dire «nessun bersaglio», vuol dire
#    «bersaglio rotto», ed e' un difetto segnalato su un ramo che funziona.
def _meta_errore_fattura(
    context: dict[str, Any], exc: ServiceError
) -> LottoPipelineMeta:
    meta: LottoPipelineMeta = {
        "task": context.get("task"),
        "detail": exc.detail,
    }
    bersagli = bersagli_envelope(exc.targets)
    if bersagli:
        meta["bersagli"] = bersagli
    return meta


class LottoPipelineRunner:
    """Orchestratore Django della pipeline lotto vendite."""

    # Scopo: Inizializza la istanza.
    def __init__(
        self,
        repository: VenditePipelineRepository | None = None,
        step_executor: PipelineStepExecutor | None = None,
        error_logger: PipelineErrorLogger | None = None,
        lotto_segnalazioni_service: LottoSegnalazioniService | None = None,
    ) -> None:
        self.repository = repository or VenditePipelineRepository()
        self.step_executor = step_executor or PipelineStepExecutor(self.repository)
        self.error_logger = error_logger or PipelineErrorLogger(self.repository)
        self.lotto_segnalazioni_service = (
            lotto_segnalazioni_service or LottoSegnalazioniService(self.repository)
        )

    # Scopo: Registra errore di lotto su log dominio e forza stato lotto a ERRORE in transazione atomica.
    def _mark_lotto_error(
        self,
        *,
        lotto_id: int,
        code: str,
        tipo_lotto: str,
        detail: str | None,
    ) -> None:
        # Mantiene stato lotto coerente e traccia errore con codice uniforme.
        #
        # ⛔ QUI DENTRO CI SONO SOLO LE TRE SCRITTURE DELLA MARCATURA. Il diario
        #    e' un passo A PARTE, e indipendente: vedi `_mark_lotto_error_safely`.
        with transaction.atomic():
            self.error_logger.log_error(
                scope="LOTTO",
                severity="C",
                code=code,
                message=f"Errore pipeline: {code}",
                detail=detail,
                lotto_id=lotto_id,
                context={"tipo_lotto": tipo_lotto},
                function_name="vendite.run_lotto_pipeline",
            )
            self.repository.set_lotto_job_stato(lotto_id, "ERRORE", "Errore pipeline")
            self.repository.log_lotto_esito_fatture(lotto_id)


    # Scopo: Adatta il telaio condiviso `diagnostica_best_effort` fissando il
    #        `function_name` di questo runner, cosi' i call site restano corti.
    #
    # ⭐ IL TELAIO NON VIVE PIU' QUI: e' salito in
    #    `apps/core/services/diagnostica_best_effort.py` quando
    #    `commesse_service` ha avuto lo stesso bisogno sul ramo push (consegna
    #    BE-7). Era nato qui il 2026-08-21 alla terza copia dello stesso
    #    `try/except/log_error_only` — marcatore di errore del LOTTO,
    #    marcatura della FATTURA fallita, riscrittura del TASK RUN — e un
    #    telaio che vive dentro uno dei suoi utenti si copia al primo utente
    #    che sta altrove.
    #
    # ⚠️ Ingoia QUALUNQUE eccezione di proposito: qui si sta gia' gestendo un
    #    fallimento, e il secondo non ha diritto di prendere il posto del primo.
    def _diagnostica_best_effort(
        self, azione: Callable[[], None], *, contesto: dict[str, Any]
    ) -> None:
        diagnostica_best_effort(
            azione,
            contesto=contesto,
            function_name="vendite.run_lotto_pipeline",
        )

    def _mark_lotto_error_safely(
        self,
        *,
        lotto_id: int,
        code: str,
        tipo_lotto: str,
        detail: str | None,
        correlation_id: str | None = None,
    ) -> None:
        # Il mark errore non deve mai mascherare l'eccezione principale.
        #
        # ⛔ DUE PASSI INDIPENDENTI, e non uno solo: il fallimento del primo non
        #    deve impedire il secondo.
        #
        # 🔴 IL DIFETTO CHE HA IMPOSTO QUESTA FORMA, misurato su un giro vero il
        #    2026-08-23 (lotto 6260). La pipeline era fallita per un motivo di
        #    dominio legittimo — una nota di credito non numerabile perche' la
        #    fattura che rettifica non ha ancora un numero. Poi:
        #
        #      set_lotto_job_stato(6260, 'ERRORE')
        #        -> ⛔ «Transizione non ammessa: COMPLETATO -> ERRORE»
        #
        #    Il lotto era gia' COMPLETATO da una corsa precedente, e il guard di
        #    dominio rifiuta quella transizione. L'eccezione usciva da
        #    `_mark_lotto_error` **prima** di arrivare al diario, quindi
        #    `PIPELINE_ERROR` non veniva mai scritto: in `event_log` **zero
        #    righe**, e dell'unico giro andato storto non restava traccia nel
        #    registro fatto apposta per raccontarlo.
        #
        # ⭐ E' lo SPECCHIO del difetto corretto poco prima (il diario dentro
        #    l'`atomic` della marcatura, che rollava indietro lo stato del
        #    lotto). Li' la marcatura moriva per colpa del diario; qui il diario
        #    moriva per colpa della marcatura. La regola che li chiude entrambi
        #    e' una sola, ed e' la **D-12**: *il diario registra il fatto, e
        #    l'unica cosa che lo ferma e' non sapere di chi e' la riga*. Il fatto
        #    era accaduto; che un'altra scrittura non sia passata non lo cancella.
        #
        # ⚠️ L'ORDINE resta questo — prima si prova a mettere in salvo lo stato,
        #    poi lo si racconta — ma adesso e' una preferenza, non una
        #    dipendenza.
        self._diagnostica_best_effort(
            lambda: self._mark_lotto_error(
                lotto_id=lotto_id,
                code=code,
                tipo_lotto=tipo_lotto,
                detail=detail,
            ),
            contesto={"lotto_id": lotto_id, "tipo_lotto": tipo_lotto, "detail": detail},
        )
        self._diagnostica_best_effort(
            lambda: self.repository.log_event(
                entity_type="LOTTO",
                entity_id=lotto_id,
                event_code="PIPELINE_ERROR",
                severity="ERROR",
                correlation_id=correlation_id,
                payload={"code": code, "detail": detail, "tipo_lotto": tipo_lotto},
            ),
            contesto={"lotto_id": lotto_id, "evento": "PIPELINE_ERROR"},
        )

    # Scopo: Attacca il fallimento ALLA RIGA della fattura che l'ha causato —
    #        `stato_esecuzione='ERRORE'` + il messaggio in `vendite.fatture_log`.
    #
    # ⭐ PERCHE' QUI E NON DOVE L'ERRORE NASCE (rilievo di Tid, 2026-08-21). Il
    #    giro per-fattura e' FAIL-FAST: rilancia, e la transazione dello step
    #    viene annullata. Una riga di log scritta li' dentro sparirebbe insieme
    #    all'errore che descrive — ed e' esattamente cio' che succedeva: il
    #    toast diceva il motivo e poi il motivo non esisteva piu' da nessuna
    #    parte. Questo handler sta FUORI dall'`atomic` dello step, come
    #    `_mark_lotto_error_safely`: quello che scrive resta.
    #
    #    E' la stessa forma dei gestionali a lotti: la testata segnala che nel
    #    dettaglio c'e' un errore grave, la riga dice quale.
    #
    # ⚠️ Best-effort come il gemello sul lotto: se non riesce a scrivere non
    #    deve MAI mascherare l'eccezione vera, che e' l'unica cosa che
    #    l'operatore sta aspettando.
    # ⚠️ `fattura_id` arriva dal `context` del ServiceError, dove
    #    `_run_per_fattura_task` lo mette gia' per il diario: nessun canale
    #    nuovo da tenere allineato. Se manca — errore di lotto, non di riga —
    #    non c'e' niente da attaccare e si esce in silenzio.
    def _persist_fattura_error_safely(
        self, *, lotto_id: int, exc: ServiceError
    ) -> None:
        context = getattr(exc, "context", None) or {}
        fattura_id = context.get("fattura_id")
        if not isinstance(fattura_id, int):
            return
        self._diagnostica_best_effort(
            lambda: self.repository.marca_fattura_in_errore(
                lotto_id=lotto_id,
                fattura_id=fattura_id,
                code=exc.code,
                messaggio=getattr(exc, "message", None) or str(exc),
                # ⭐ IL BERSAGLIO SI PERSISTE QUI, e questa e' la strada che
                #    conta piu' del toast (2026-08-24). Un giro di fatturazione
                #    puo' partire da solo — worker, batch notturno — e fallire
                #    quando davanti allo schermo non c'e' nessuno: li' non c'e'
                #    nessuna risposta da riempire, e l'unica cosa che resta e'
                #    questa riga. Il §1 del brief lo dice: il lettore che conta
                #    e' «l'operatore cinque minuti dopo, che sta rimediando».
                # ⚠️ Nel `meta`, che e' gia' `jsonb NOT NULL`: nessuna colonna
                #    nuova, e la lista fatture del lotto quel `meta` lo legge
                #    gia' (ne estrae `error_code`).
                # ⚠️ La chiave `bersagli` si mette SOLO se c'e' qualcosa da
                #    dire — mai a `null`. E' la stessa disciplina che il team DB
                #    ha scritto nel pilota: una chiave presente e inutilizzabile
                #    non vuol dire «nessun bersaglio», vuol dire «bersaglio
                #    rotto», ed e' un difetto segnalato su un ramo che funziona.
                meta=_meta_errore_fattura(context, exc),
            ),
            contesto={"lotto_id": lotto_id, "fattura_id": fattura_id},
        )

    # Scopo: RISCRIVE il task run fallito dopo il rollback dello step.
    #
    # 🔴 IL DIARIO DEI TASK REGISTRAVA SOLO I SUCCESSI (rilievo di Tid,
    #    2026-08-21). `fn_fail_lotto_task_run` gira dentro la transazione dello
    #    step, che il fallimento annulla: la riga «questo task e' andato in
    #    errore» spariva insieme al task. Misurato prima del fix: **zero
    #    ERRORE** su 184 run (128 COMPLETATO, 56 ANNULLATO) — e i fallimenti
    #    c'erano.
    #
    #    Qui siamo FUORI dall'`atomic` dello step, quindi quello che si scrive
    #    resta. Si rifa' la coppia `start` + `fail`: `fn_start_lotto_task_run`
    #    e' la sola che sa calcolare il `tentativo`, e ricrearlo a mano
    #    significherebbe copiarne la regola in un secondo posto.
    #
    # ⚠️ Best-effort come gli altri due gemelli: un diario che non si scrive non
    #    deve MAI mascherare l'errore vero.
    # ⚠️ Le coordinate arrivano dall'eccezione (`zeroerp_task_run_fallito`), che
    #    le porta solo quando il tracing per quel task e' attivo: dove non c'e'
    #    policy non c'e' diario, e non va inventato qui.
    def _persist_task_run_error_safely(self, exc: BaseException) -> None:
        coord = getattr(exc, "zeroerp_task_run_fallito", None)
        if not isinstance(coord, dict):
            return
        def _riscrivi() -> None:
            run = self.repository.start_lotto_task_run(
                lotto_id=coord["lotto_id"],
                pipeline_id=coord["pipeline_id"],
                stato_doc_fiscale_id=coord["stato_doc_fiscale_id"],
                task_code=coord["task_code"],
                fase=coord["fase"],
                meta={"rollback": False},
                # ⚠️ Il filo arriva dall'eccezione, non da qui: siamo fuori
                #    dalla transazione dello step e il giro non e' piu' nello
                #    scope. Senza, il tentativo FALLITO sarebbe l'unico del giro
                #    senza `correlation_id` — cioe' proprio quello che si va a
                #    cercare.
                correlation_id=coord.get("correlation_id"),
            )
            self.repository.fail_lotto_task_run(
                run.task_run_id,
                coord["error_code"],
                coord["error_message"],
            )

        self._diagnostica_best_effort(
            _riscrivi,
            contesto={
                "lotto_id": coord.get("lotto_id"),
                "task_code": coord.get("task_code"),
            },
        )

    # Scopo: Normalizza lotto_id (0/None = "nuovo lotto", crea) → None oppure id reale.
    @staticmethod
    def _normalize_lotto_id(lotto_id: int | None) -> int | None:
        return None if lotto_id in (0, None) else lotto_id

    # Scopo: Determina da quale step (singolo) ripartire. Tre casi:
    #  - deve rifare lo step CORRENTE: rerun in errore OPPURE lotto riportato a
    #    bozza e non ancora rifatto (vedi `deve_rifare_step_corrente`);
    #  - successo su lotto ESISTENTE (lotto_id passato dal driver): avanza allo step
    #    SUCCESSIVO a quello gia` eseguito — abilita la progressione multi-step, prima
    #    assente nel ramo di successo (steps[:1] prendeva sempre il primo step);
    #  - primo run / lotto appena creato / stato non in catalogo: dal primo step.
    @staticmethod
    def _resolve_steps_for_run(
        *,
        steps: list[Any],
        is_existing_lotto_request: bool,
        deve_rifare_step_corrente: bool,
        lotto_stato_doc_corrente: int | None,
    ) -> list[Any]:
        if lotto_stato_doc_corrente is None:
            return steps
        step_index_by_stato = {
            step.stato_doc_fiscale_id: index for index, step in enumerate(steps)
        }
        current_index = step_index_by_stato.get(lotto_stato_doc_corrente)
        if current_index is None:
            return steps
        if deve_rifare_step_corrente:
            # Resume sullo step corrente; evita transizioni retroattive non ammesse.
            # Due cause, stesso comportamento: lo step e` fallito (rerun in
            # errore) oppure e` RIUSCITO ma il suo risultato non andava bene e il
            # lotto e` stato riportato a bozza. Nel secondo caso marcare il lotto
            # ERRORE per ottenere lo stesso effetto sarebbe una bugia visibile:
            # comparirebbe fra i falliti nei cruscotti (brief DB→BE §3).
            return steps[current_index:]
        if is_existing_lotto_request:
            # Successo su lotto esistente: prosegui dallo step successivo (driver multi-step).
            # Se era l'ultimo step, la lista resta vuota: nessun passo da eseguire.
            return steps[current_index + 1:]
        # Lotto appena creato (lotto_id non passato): parti dal primo step del catalogo.
        return steps

    # Scopo: Valuta se eseguire rollback automatico dello step in rerun, escludendo rollback distruttivi.
    def _should_execute_auto_step_rollback(
        self,
        *,
        step: Any,
        effective_tipo_lotto: str,
        lotto_context: Any,
        is_massivo_error_rerun: bool,
        auto_step_rollback_enabled: bool,
        rerun_reset_step_ids: set[int],
    ) -> bool:
        if not (
            is_massivo_error_rerun
            and auto_step_rollback_enabled
            and step.stato_doc_fiscale_id in rerun_reset_step_ids
        ):
            return False
        rollback_processes = self.repository.get_step_processes(
            step.stato_doc_fiscale_id,
            tipo_lotto=effective_tipo_lotto,
            utility_id=lotto_context.utility_id,
            tipo_doc_fiscale_id=lotto_context.tipo_doc_fiscale_id,
            rollback=True,
        )
        if not rollback_processes:
            return False
        # Evita rollback distruttivi in auto-run.
        return all(
            str(process.get("task", "")).strip() != "reset_lotto_draft"
            for process in rollback_processes
        )

    # Scopo: Gestisce un singolo step pipeline aggiornando stato lotto, log di fase e sincronizzazione esito fatture
    def _execute_pipeline_step(
        self,
        *,
        lotto_id: int,
        step: Any,
        effective_tipo_lotto: str,
        dry_run: bool,
        correlation_id: str | None = None,
    ) -> None:
        # Traccia avanzamento step coerente con il flusso SQL originale.
        self.repository.set_lotto_job_stato(
            lotto_id,
            "IN_ESECUZIONE",
            f"Esecuzione step: {step.descrizione or step.stato_doc_fiscale_id}",
        )
        self.repository.update_lotto_stato_doc(lotto_id, step.stato_doc_fiscale_id)

        step_meta: PipelineStepLogMeta = {
            "ordine": step.ordine,
            "dry_run": dry_run,
        }
        self.repository.log_pipeline_fase(
            lotto_id=lotto_id,
            stato_doc_fiscale_id=step.stato_doc_fiscale_id,
            fase=step.descrizione or "Esecuzione step",
            status="I",
            messaggio=None,
            meta=step_meta,
        )

        self.step_executor.execute_step(
            lotto_id=lotto_id,
            stato_doc_fiscale_id=step.stato_doc_fiscale_id,
            tipo_lotto=effective_tipo_lotto,
            rollback=False,
            dry_run=dry_run,
            correlation_id=correlation_id,
        )
        # Allineamento fatture allo stato dello step (parametrico, per-step): la fattura
        # segue il lotto 1→2→8→3, così EMESSA congela l'IVA prima della numerazione in
        # DEFINITIVA (evita il salto 1→8 vietato dalla matrice transizioni). Eseguito DOPO
        # i task dello step (semantica "EMESSA = IVA certificata"); idempotente grazie al
        # guard `IS DISTINCT FROM` in fn_sync_lotto_fatture_stato (step DRAFT → 1→1 no-op).
        # Solo forward (questo metodo non è il path di rollback).
        # ⚠️ INCONDIZIONATO anche in dry-run (fix 2026-07-22): è la COPPIA con
        # `update_lotto_stato_doc` sopra a dover essere indivisibile — se la sync
        # fosse saltata mentre lo stato del lotto avanza, resterebbe esattamente
        # l'incoerenza lotto-avanti/fatture-indietro che il guard DB
        # `E_LOTTO_FATTURE_STATO_INCOERENTE` ora respinge al commit. In dry-run
        # non persiste nulla perché l'intera fase viene rollbackata da
        # `run_pipeline`; in più il dry-run diventa fedele (esercita le stesse
        # scritture, quindi predice gli errori del run vero).
        self.repository.sync_lotto_fatture_stato(
            lotto_id=lotto_id,
            stato_doc_fiscale_id=step.stato_doc_fiscale_id,
        )
        self.repository.log_lotto_esito_fatture(lotto_id)
        # ⚠️ NEL TELAIO (BE-7 / D-15): siamo DENTRO l'`atomic` dello step, e
        #    dal 2026-08-22 questa scrittura PUO' fallire — il giornale rifiuta
        #    una riga di cui non sa dire di chi e'. Senza telaio un difetto del
        #    diario porterebbe giu' lo step che sta descrivendo, cioe' il
        #    lavoro vero. Il savepoint e' cio' che tiene sana la transazione.
        self._diagnostica_best_effort(
            lambda: self.repository.log_event(
                entity_type="LOTTO",
                entity_id=lotto_id,
                event_code="STEP_COMPLETED",
                correlation_id=correlation_id,
                payload={
                    "step_ordine": step.ordine,
                    "step_desc": step.descrizione,
                    "stato_doc_fiscale_id": step.stato_doc_fiscale_id,
                    "dry_run": dry_run,
                },
            ),
            contesto={
                "lotto_id": lotto_id,
                "evento": "STEP_COMPLETED",
                "step_ordine": step.ordine,
            },
        )
        self._process_close_lotto_by_flag(
            lotto_id=lotto_id,
            stato_doc_fiscale_id=step.stato_doc_fiscale_id,
            dry_run=dry_run,
        )

    # Scopo: Processo separato di chiusura lotto guidato da flag config.stati_doc_fiscale.chiude_lotto.
    def _process_close_lotto_by_flag(
        self,
        *,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        dry_run: bool,
    ) -> None:
        if dry_run:
            return
        if not self.repository.is_stato_doc_chiude_lotto(stato_doc_fiscale_id):
            return
        self.repository.close_lotto_operativo(lotto_id)
        self.repository.log_pipeline_fase(
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            fase="Chiusura lotto operativa",
            status="I",
            messaggio="Chiusura lotto eseguita da flag chiude_lotto",
            meta={"process": "close_lotto_by_flag"},
        )

    # Scopo: Risolve o crea il lotto in transazione autonoma, registrando nella
    #        STESSA transazione l'eventuale perimetro mirato (gruppi
    #        fatturabili). Obiettivo: un lotto mirato non deve mai esistere
    #        senza il suo criterio — sarebbe un giro di massa travestito.
    # Il lotto persiste anche se la fase di esecuzione fallisce,
    # consentendo a _mark_lotto_error di trovarlo e marcarlo ERRORE.
    def _resolve_lotto(self, params: LottoPipelineParams) -> tuple[int, bool]:
        """Restituisce (lotto_id, is_existing_lotto_request)."""
        with transaction.atomic():
            normalized_lotto_id = self._normalize_lotto_id(params.lotto_id)
            is_existing_lotto_request = normalized_lotto_id is not None
            lotto_id = self.repository.get_or_create_lotto(
                lotto_id=normalized_lotto_id,
                competenza_mese=params.competenza_mese,
                tipo_doc_fiscale_id=params.tipo_doc_fiscale_id,
                utility_id=params.utility_id,
                billing_account_id=params.billing_account_id,
                emittente_soggetto_ruolo_id=params.emittente_soggetto_ruolo_id,
                lock_batch_id=params.lock_batch_id,
                meta=params.meta,
                tipo_lotto=params.tipo_lotto,
            )
            # Perimetro mirato scritto SOLO alla creazione: su un lotto
            # esistente (rerun / avanza step del LottoDrawer) il criterio e'
            # gia' persistito e va riprodotto, non riscritto — riscriverlo da
            # una chiamata che non porta gruppi lo allargherebbe in silenzio.
            if params.gruppi and not is_existing_lotto_request:
                self.repository.set_lotto_gruppi(lotto_id, params.gruppi)
        return lotto_id, is_existing_lotto_request

    # Scopo: Orchestra l'intero flusso pipeline lotto: risoluzione lotto, step execution, resume/rollback e gestione errori finali.
    # `defer_dry_run_rollback=True` (SOLO driver until_done): il rollback del
    # dry-run non viene marcato qui ma dal driver, che avvolge l'intera catena
    # in un'unica transazione — altrimenti ogni step verrebbe rollbackato
    # singolarmente e lo stato non avanzerebbe mai (catena non simulabile).
    def run_pipeline(
        self,
        params: LottoPipelineParams,
        *,
        defer_dry_run_rollback: bool = False,
    ) -> int:
        lotto_id: int | None = None
        correlation_id: str | None = None
        effective_tipo_lotto = params.tipo_lotto or "MASSIVO"
        try:
            # Fase 1: risoluzione lotto in transazione autonoma.
            # Il lotto persiste anche se la fase di esecuzione fallisce,
            # consentendo a _mark_lotto_error_safely di trovarlo e marcarlo.
            lotto_id, is_existing_lotto_request = self._resolve_lotto(params)

            # ⭐ SI RITIRANO LE PROPRIE BANDIERE PRIMA DI RIPROVARE, e FUORI
            # dalla transazione dello step. Due ragioni, entrambe misurate il
            # 2026-08-21:
            #
            # 🔴 PRIMA del verdetto. Dal 2026-08-21 il BE marca le fatture
            #    fallite (`stato_esecuzione='ERRORE'` + log critico) perché
            #    l'operatore legga il motivo sulla riga — e quelle marcature
            #    entrano nella guardia unificata PRE-1. Se il verdetto le
            #    trovasse ancora alzate dal tentativo precedente, il primo
            #    fallimento chiuderebbe il lotto per sempre: l'operatore
            #    corregge la causa, ripreme «Rendi definitive» e trova «Lotto
            #    bloccato per segnalazioni critiche attive», cioè un messaggio
            #    che parla d'altro. Una porta a senso unico.
            #
            # 🔴 FUORI dalla transazione. Dentro, il ritiro sarebbe annullato
            #    dal rollback del tentativo fallito mentre la marcatura nuova —
            #    che vive fuori apposta — resterebbe: misurato, i log critici
            #    crescevano 1 → 2 → 3 a ogni tentativo, e la scheda
            #    «Segnalazioni» avrebbe mostrato N copie dello stesso errore.
            #    Qui il ritiro è definitivo: vive esattamente una riga per
            #    fattura, quella dell'ULTIMO tentativo.
            #
            # ⚠️ Ritira SOLO ciò che ha scritto il BE (firma `origine` nel meta):
            #    le segnalazioni dei task DB hanno un altro padrone e le ritira
            #    lui quando il suo problema è risolto.
            # 📌 Diverso da `disattiva_segnalazioni_lotto_be` più sotto, che sta
            #    dentro la transazione apposta: quelle bandiere il rollback deve
            #    ripristinarle, perché descrivono uno stato che il fallimento
            #    non ha cambiato.
            if lotto_id is not None:
                self.repository.ritira_marcature_fatture_be(lotto_id)

            # Fase 2: esecuzione pipeline in transazione separata.
            with transaction.atomic():
                # Fonte autoritativa dominio: il tipo persistito sul lotto a DB; params è fallback.
                lotto_tipo_db = self.repository.get_lotto_tipo(lotto_id)
                effective_tipo_lotto = lotto_tipo_db or effective_tipo_lotto
                lotto_stato_corrente = self.repository.get_lotto_job_stato(lotto_id)
                lotto_stato_doc_corrente = self.repository.get_lotto_stato_doc_fiscale_id(lotto_id)
                # Evita falsi positivi sui lotti appena creati (lotto_id=0), che possono
                # risultare transitoriamente in esecuzione nello stesso scope transazionale.
                if is_existing_lotto_request and lotto_stato_corrente == "IN_ESECUZIONE":
                    ErrorManager.raise_error(
                        code="E_PIPELINE_LOTTO_IN_ESECUZIONE",
                        message="Lotto gia` in esecuzione.",
                        detail=f"Rilancio non consentito su lotto in esecuzione: {lotto_id}",
                        context={
                            "lotto_id": lotto_id,
                            "tipo_lotto": effective_tipo_lotto,
                        },
                        function_name="vendite.run_lotto_pipeline",
                        log_to_db=True,
                    )
                # Regola dominio: "lotto in errore" e` deciso dallo stato_lotto persistito,
                # non dalla sola severita` dei log di esito fatture (C/W/I).
                is_massivo_error_rerun = (
                    effective_tipo_lotto == "MASSIVO"
                    and self.repository.is_lotto_in_errore(lotto_id)
                )
                # Fase 6 — ritorno a bozza. Il lotto e` stato riportato a DRAFT
                # da un'azione dell'operatore e deve RIFARE lo step, non
                # avanzare: senza questa lettura cadrebbe nel ramo «lotto
                # esistente» e ripartirebbe da EMESSA, saltando proprio la
                # rigenerazione delle righe per cui era stato riaperto.
                # ⚠️ Tenuto DISTINTO da `is_massivo_error_rerun` invece che
                # fuso in un flag solo: quello governa anche il rollback
                # automatico dello step (`_should_execute_auto_step_rollback`),
                # che qui NON va eseguito — le fatture le ha gia` cancellate la
                # funzione DB, e un rollback in piu` lavorerebbe sul vuoto.
                is_lotto_riaperto = self.repository.is_lotto_riaperto(lotto_id)
                deve_rifare_step_corrente = is_massivo_error_rerun or is_lotto_riaperto
                draft_id = self.repository.get_stato_doc_fiscale_id("DRAFT")
                emessa_id = self.repository.get_stato_doc_fiscale_id("EMESSA")
                rerun_reset_step_ids = {
                    step_id for step_id in (draft_id, emessa_id) if step_id is not None
                }
                meta: dict[str, Any] = params.meta or {}
                auto_step_rollback_enabled = bool(meta.get("auto_step_rollback"))

                lotto_context = self.repository.get_lotto_context(lotto_id)
                ErrorManager.require(
                    lotto_context is not None,
                    code="E_PIPELINE_LOTTO_NOT_FOUND",
                    message="Lotto pipeline non trovato.",
                    detail=f"Lotto non trovato: {lotto_id}",
                    context={"lotto_id": lotto_id},
                    function_name="vendite.run_lotto_pipeline",
                    log_to_db=True,
                )
                assert lotto_context is not None

                steps = self.repository.list_pipeline_steps(
                    effective_tipo_lotto,
                    utility_id=lotto_context.utility_id,
                    tipo_doc_fiscale_id=lotto_context.tipo_doc_fiscale_id,
                )
                steps = self._resolve_steps_for_run(
                    steps=steps,
                    is_existing_lotto_request=is_existing_lotto_request,
                    deve_rifare_step_corrente=deve_rifare_step_corrente,
                    lotto_stato_doc_corrente=lotto_stato_doc_corrente,
                )
                # Modalita` operativa: un run esegue un solo step pipeline (il prossimo disponibile).
                steps = steps[:1]
                # Blocco avanzamento (D-Q p.1): con criticita` attive il lotto
                # NON AVANZA allo step successivo, ma il RILANCIO dello STESSO
                # step resta ammesso — e` la via d'uscita definita da Tid
                # (correggo l'anagrafica → rieseguo lo step → il task ritira le
                # proprie segnalazioni al successo). Prima questo gate rifiutava
                # qualunque esecuzione: la correzione era impossibile per
                # costruzione e l'unica uscita reale era rifare il lotto.
                selected_step = steps[0] if steps else None
                is_rilancio_stesso_step = (
                    selected_step is not None
                    and lotto_stato_doc_corrente is not None
                    and selected_step.stato_doc_fiscale_id == lotto_stato_doc_corrente
                )
                lotto_signal_status = self.lotto_segnalazioni_service.evaluate_lotto_status(lotto_id)
                if lotto_signal_status.blocks_next_step and not is_rilancio_stesso_step:
                    ErrorManager.raise_error(
                        code="E_PIPELINE_LOTTO_CRITICAL",
                        message="Lotto bloccato per segnalazioni critiche attive.",
                        detail=(
                            "Correggere le segnalazioni critical prima di proseguire: "
                            f"lotto_id={lotto_id}"
                            f", critical_count={lotto_signal_status.critical_count}"
                            f", stato_esecuzione_errore_count={lotto_signal_status.fatture_stato_esecuzione_errore_count}"
                        ),
                        context={
                            "lotto_id": lotto_id,
                            "critical_count": lotto_signal_status.critical_count,
                            "warning_count": lotto_signal_status.warning_count,
                            "attention_count": lotto_signal_status.attention_count,
                            "stato_esecuzione_errore_count": lotto_signal_status.fatture_stato_esecuzione_errore_count,
                            "summary": lotto_signal_status.summary,
                        },
                        function_name="vendite.run_lotto_pipeline",
                        log_to_db=True,
                    )
                # D-Q p.2 — «chi alza la bandiera la abbassa»: prima di eseguire
                # lo step si ritirano le segnalazioni di LOTTO alzate dal BE
                # (errori pipeline del runner + fotografie esito derivate dai
                # log fatture). Siamo DENTRO la transazione dello step: se lo
                # step fallisce, il rollback ripristina le bandiere — il ritiro
                # e` quindi effettivo SOLO al successo, senza logica in piu`.
                # A fine step `log_lotto_esito_fatture` scrive comunque la
                # fotografia fresca: se le fatture sono ancora rotte, il blocco
                # si ricostruisce da solo dallo stato corrente — mai da quello
                # vecchio. I log per-fattura non si toccano: quelli li ritira il
                # task DB che li ha scritti, quando il problema e` risolto.
                if steps:
                    self.repository.disattiva_segnalazioni_lotto_be(lotto_id)
                self.repository.set_lotto_job_stato(lotto_id, "IN_ESECUZIONE", "Avvio pipeline")
                # ⭐ L'IDENTITA' DEL GIRO NASCE QUI, ED E' NUOVA A OGNI CORSA
                #    (consegna BE-2, decisione D-7).
                #
                # 🔴 Prima valeva `lotto_context.lock_batch_id`, e non
                #    identificava un giro: quel campo nasce col LOTTO
                #    (`COALESCE(p_lock_batch_id, uuidv7())`) e **non cambia
                #    mai**. Diceva «di che lotto», che `entity_id` diceva gia' —
                #    e due corse dello stesso lotto erano indistinguibili
                #    proprio sulla domanda per cui il campo esiste. Non e' una
                #    deduzione: lo asserisce il test 6 di
                #    `test-fn-list-lotto-segnalazioni-job`, ed e' il motivo per
                #    cui l'ancora del «job corrente» e' l'`event_time`.
                #
                # ⚠️ Perche' non il `tx_id`: un giro attraversa PIU'
                #    transazioni, una per step. Il `tx_id` cuce cio' che accade
                #    nella stessa transazione, che e' un'altra domanda — servono
                #    entrambi. E perche' non l'id del `task_run`: quello e'
                #    per-task, non per-giro.
                #
                # ⭐ Da qui scende su tutte e tre le sedi: gli eventi del giro,
                #    i suoi `task_runs` (via lo step executor) e — sul ramo push
                #    — la riga di `commesse_push_log`.
                correlation_id = str(uuid4())
                # ⚠️ Nel telaio (BE-7): dentro l'`atomic` del giro. Un evento
                #    d'avvio rifiutato non deve impedire l'avvio.
                self._diagnostica_best_effort(
                    lambda: self.repository.log_event(
                        entity_type="LOTTO",
                        entity_id=lotto_id,
                        event_code="PIPELINE_STARTED",
                        correlation_id=correlation_id,
                        payload={
                            "tipo_lotto": effective_tipo_lotto,
                            "dry_run": params.dry_run,
                        },
                    ),
                    contesto={"lotto_id": lotto_id, "evento": "PIPELINE_STARTED"},
                )

                for step in steps:
                    if self._should_execute_auto_step_rollback(
                        step=step,
                        effective_tipo_lotto=effective_tipo_lotto,
                        lotto_context=lotto_context,
                        is_massivo_error_rerun=is_massivo_error_rerun,
                        auto_step_rollback_enabled=auto_step_rollback_enabled,
                        rerun_reset_step_ids=rerun_reset_step_ids,
                    ):
                        self.step_executor.execute_step(
                            lotto_id=lotto_id,
                            stato_doc_fiscale_id=step.stato_doc_fiscale_id,
                            tipo_lotto=effective_tipo_lotto,
                            rollback=True,
                            dry_run=params.dry_run,
                            # Il rollback automatico fa parte DI QUESTO giro:
                            # senza il filo, i suoi tentativi sarebbero gli
                            # unici della corsa a non ritrovarsi.
                            correlation_id=correlation_id,
                        )

                    self._execute_pipeline_step(
                        lotto_id=lotto_id,
                        step=step,
                        effective_tipo_lotto=effective_tipo_lotto,
                        dry_run=params.dry_run,
                        correlation_id=correlation_id,
                    )

                # Fase 6 — «chi accende il segnale lo spegne», ma SOLO se il
                # rifacimento ha davvero rifatto qualcosa.
                #
                # ⚠️ La condizione non e` «lo step e` stato eseguito» ma «il
                # lotto ha di nuovo fatture», e la differenza non e` teorica:
                # un lotto riaperto puo` attraversare lo step senza produrre
                # nulla — misurato il 2026-08-03 sul lotto 1279, dove i quattro
                # task dello step DRAFT sono stati saltati (`execution_mode =
                # SKIP`, perche` i loro `task_runs` del giro precedente sono
                # ancora COMPLETATO e attivi). Spegnere il segnale li` lo
                # spegnerebbe su un giro a vuoto: il lotto resterebbe vuoto E
                # senza segnale, e il rilancio successivo passerebbe allo step
                # dopo su un documento che non esiste — cioe` il «non fa nulla»
                # che ha fatto scoprire il difetto.
                #
                # Tenendo il segnale acceso finche` le fatture non ci sono, il
                # problema resta VISIBILE e il lotto continua a chiedere il
                # proprio rifacimento, invece di sembrare a posto.
                # (La causa dello SKIP va sanata a monte, sui `task_runs`: non
                # si aggira qui, o avremmo due posti che decidono se un task va
                # rifatto.)
                #
                # Sta DENTRO la transazione dello step: se lo step solleva, il
                # rollback ripristina `riaperto_il` — stesso principio del
                # ritiro segnalazioni qui sopra.
                if steps and is_lotto_riaperto and self.repository.list_fatture_by_lotto(
                    lotto_id, limit=1,
                ):
                    self.repository.azzera_riaperto_il(lotto_id)

                # D-Q: lo step si e` completato (le fatture sane hanno il loro
                # lavoro), ma se restano fatture in errore il lotto va marcato
                # ERRORE — e` cio` che rende il prossimo run un RILANCIO dello
                # stesso step (`is_massivo_error_rerun` → steps[current:]) invece
                # di un avanzamento, che il gate sopra bloccherebbe. Nessuna
                # eccezione: sollevare qui farebbe rollback anche del lavoro
                # delle fatture sane e della loro marcatura.
                stato_finale = (
                    self.lotto_segnalazioni_service.evaluate_lotto_status(lotto_id)
                    if steps else None
                )
                step_con_errori = stato_finale is not None and stato_finale.is_error
                if step_con_errori:
                    assert stato_finale is not None
                    self.repository.set_lotto_job_stato(
                        lotto_id,
                        "ERRORE",
                        "Step completato con fatture in errore: correggere e rilanciare lo step",
                    )
                else:
                    self.repository.set_lotto_job_stato(lotto_id, "COMPLETATO", "Pipeline completata")
                # ⚠️ Nel telaio (BE-7): dentro l'`atomic` del giro.
                self._diagnostica_best_effort(
                    lambda: self.repository.log_event(
                        entity_type="LOTTO",
                        entity_id=lotto_id,
                        event_code="PIPELINE_COMPLETED",
                        correlation_id=correlation_id,
                        payload={
                            "tipo_lotto": effective_tipo_lotto,
                            "con_errori": step_con_errori,
                            **(
                                {
                                    "critical_count": stato_finale.critical_count,
                                    "stato_esecuzione_errore_count": (
                                        stato_finale.fatture_stato_esecuzione_errore_count
                                    ),
                                }
                                if step_con_errori and stato_finale is not None
                                else {}
                            ),
                        },
                    ),
                    contesto={"lotto_id": lotto_id, "evento": "PIPELINE_COMPLETED"},
                )
                # DRY-RUN = NESSUNA PERSISTENZA (fix 2026-07-22, segnalazione team DB).
                # Prima lo stato fiscale del lotto veniva avanzato in modo
                # INCONDIZIONATO mentre la sync delle fatture era sotto
                # `if not dry_run`: un dry-run lasciava il lotto avanti e le
                # fatture indietro — è la genesi dei lotti 106/107 (lotto EMESSA,
                # fatture DRAFT), emersa un mese dopo come `transizione 1→8`.
                # Rollback dell'INTERA fase invece di condizionare ogni singola
                # scrittura: non dipende dal ricordarsi di farlo a ogni nuova
                # scrittura aggiunta qui in futuro.
                # ⚠️ Deve restare l'ULTIMA istruzione del blocco: dentro un
                # atomic marcato per rollback Django vieta ulteriori query
                # (TransactionManagementError).
                # Con `defer_dry_run_rollback` il rollback e' di proprieta' del
                # driver until_done (transazione unica sull'intera catena).
                if params.dry_run and not defer_dry_run_rollback:
                    transaction.set_rollback(True)
                return lotto_id
        except ServiceError as exc:
            if lotto_id is not None:
                self._mark_lotto_error_safely(
                    lotto_id=lotto_id,
                    code=exc.code,
                    tipo_lotto=effective_tipo_lotto,
                    detail=exc.detail or str(exc),
                    correlation_id=correlation_id,
                )
                # La testata dice CHE c'e' un errore grave nel dettaglio; questa
                # riga dice QUALE documento, e perche'.
                self._persist_fattura_error_safely(lotto_id=lotto_id, exc=exc)
            # E il diario dei task registra anche i falliti, non solo i riusciti.
            self._persist_task_run_error_safely(exc)
            raise
        except Exception as exc:
            if lotto_id is not None:
                self._mark_lotto_error_safely(
                    lotto_id=lotto_id,
                    code="E_PIPELINE",
                    tipo_lotto=effective_tipo_lotto,
                    detail=str(exc),
                    correlation_id=correlation_id,
                )
            # Anche il ramo NON di dominio: un guasto tecnico e' comunque un
            # task che e' fallito, e il diario deve saperlo.
            self._persist_task_run_error_safely(exc)
            ErrorManager.raise_error(
                code="E_PIPELINE",
                message="Errore nella pipeline di fatturazione.",
                detail=str(exc),
                context={"lotto_id": lotto_id, "tipo_lotto": effective_tipo_lotto},
                function_name="vendite.run_lotto_pipeline",
                # Se il lotto è già creato l'errore è già persistito da _mark_lotto_error.
                log_to_db=lotto_id is None,
                cause=exc,
            )
            raise  # unreachable: raise_error alza sempre; aiuta il type checker

    # Guard anti-loop del driver "until done": i cataloghi reali hanno pochi step,
    # un valore alto intercetta solo bug (es. step che non avanzano).
    _MAX_STEP_ITERATIONS = 50

    # Scopo: Driver F2 — esegue run_pipeline (uno step per chiamata) finché la catena
    #        del lotto è conclusa. Condizioni di stop:
    #          - step di CHIUSURA raggiunto (config.stati_doc_fiscale.chiude_lotto):
    #            con la scelta D3 (chiude_lotto su DEFINITIVA) la catena si ferma alla
    #            numerazione, PRIMA di INVIATA/SDI (fuori scope) — comportamento voluto;
    #          - nessun avanzamento residuo (ultimo step già eseguito);
    #          - blocco per segnalazioni critical (E_PIPELINE_LOTTO_CRITICAL);
    #          - errore step.
    #        Riusa run_pipeline (nessuna logica di stato duplicata) e NON chiude il lotto
    #        direttamente (lo fa già _process_close_lotto_by_flag dentro run_pipeline) →
    #        niente doppia chiusura. Sui motivi di stop noti non solleva: ritorna un
    #        esito strutturato (l'endpoint/management command lo interpreta).
    #
    #        DRY-RUN (fix 2026-07-22): l'intera catena viene simulata dentro
    #        UN'UNICA transazione marcata per rollback alla fine. Il rollback
    #        per-step di run_pipeline qui e' DIFFERITO (`defer_dry_run_rollback`):
    #        se ogni step rollbackasse da solo, lo stato del lotto non
    #        avanzerebbe mai e il driver uscirebbe alla prima iterazione con un
    #        «COMPLETATO» bugiardo (0 step simulati). Cosi' invece il dry-run
    #        percorre davvero tutta la catena — predice gli errori del run vero —
    #        senza persistere nulla (nemmeno il lotto creato in Fase 1, la cui
    #        transazione autonoma diventa savepoint di questa).
    def run_lotto_until_done(self, params: LottoPipelineParams) -> dict[str, Any]:
        if params.dry_run:
            with transaction.atomic():
                esito = self._drive_lotto_until_done(params)
                # ⚠️ ULTIMA istruzione del blocco (come in run_pipeline): dopo
                # il set_rollback Django vieta ulteriori query.
                transaction.set_rollback(True)
            return esito
        return self._drive_lotto_until_done(params)

    # Scopo: Corpo del driver until_done (loop step + esito strutturato).
    #        Separato da run_lotto_until_done perche' il chiamante decide il
    #        perimetro transazionale (dry-run = transazione unica rollbackata).
    def _drive_lotto_until_done(self, params: LottoPipelineParams) -> dict[str, Any]:
        lotto_id = self._normalize_lotto_id(params.lotto_id)
        step_eseguiti = 0
        last_stato_doc: int | None = None
        motivo_stop = "COMPLETATO"
        # Errore di dominio che ha fermato la catena (motivo_stop ERRORE/
        # BLOCCATO_CRITICITA): serve al chiamante per dire all'operatore PERCHE'
        # un lotto non e' avanzato. Senza, l'esito e' un "ERRORE" muto e la
        # diagnosi richiede di rieseguire a mano lo step (smoke C-9, 2026-07-22:
        # dietro l'ERRORE c'era una transizione di stato fattura vietata).
        errore: dict[str, Any] | None = None
        iterazioni = 0
        while True:
            iterazioni += 1
            if iterazioni > self._MAX_STEP_ITERATIONS:
                motivo_stop = "GUARD_MAX_ITER"
                ErrorManager.log_error_only(
                    code="E_PIPELINE_DRIVER_MAX_ITER",
                    context={"lotto_id": lotto_id, "iterazioni": iterazioni},
                    area="backend",
                    function_name="vendite.run_lotto_until_done",
                )
                break
            # Stato PRIMA del run: confronto before/after per rilevare l'avanzamento
            # reale (un lotto esistente già all'ultimo step esegue 0 step → before==after).
            before_stato_doc = (
                self.repository.get_lotto_stato_doc_fiscale_id(lotto_id)
                if lotto_id else None
            )
            # D-Q: un lotto in errore rilancia lo STESSO step (stato_doc non
            # cambia). Serve ricordarlo per distinguere, a parità di
            # before==after, il rilancio RIUSCITO (continua: ora si può
            # avanzare) dalla catena esaurita (stop).
            era_in_errore = (
                self.repository.is_lotto_in_errore(lotto_id) if lotto_id else False
            )
            run_params = params if lotto_id is None else replace(params, lotto_id=lotto_id)
            try:
                # Il rollback del dry-run e' gestito a livello driver (transazione
                # unica in run_lotto_until_done), mai per singolo step.
                lotto_id = self.run_pipeline(run_params, defer_dry_run_rollback=True)
            except ServiceError as exc:
                motivo_stop = (
                    "BLOCCATO_CRITICITA"
                    if exc.code == "E_PIPELINE_LOTTO_CRITICAL"
                    else "ERRORE"
                )
                # Conserva l'errore parlante prima di degradare a esito
                # strutturato (il `detail` porta il messaggio del DB: guard di
                # transizione, vincoli, ecc.).
                #
                # 🔴 QUESTO E' UN QUINTO PUNTO DI APPIATTIMENTO, e per il
                #    bersaglio e' IL punto (2026-08-24). Gli endpoint del runner
                #    rispondono **200 anche quando la catena si ferma**: il
                #    fallimento e' un campo del payload, non uno status — perche'
                #    la catena puo' aver eseguito qualche step prima di fermarsi
                #    e quel lavoro va raccontato. Conseguenza: `useApiHandler`
                #    lato frontend vede un 200 e NON legge l'envelope d'errore,
                #    quindi tutto cio' che non entra in questo dizionario a video
                #    non arriva.
                #    ⭐ I nomi sono gli STESSI dell'envelope (`hint`, `fields`,
                #    `targets`) di proposito: a video il gesto lo disegna un
                #    consumatore solo, e due nomi diversi per la stessa cosa
                #    sarebbero due strade da tenere allineate a mano.
                errore = {
                    "code": exc.code,
                    "message": getattr(exc, "message", None) or str(exc),
                    "detail": getattr(exc, "detail", None),
                    # La SOLUZIONE a catalogo: cosa puo' fare l'operatore adesso.
                    "hint": exc.hint,
                    "fields": list(exc.fields) if exc.fields else None,
                    # ⭐ IL BERSAGLIO: su quale cosa. Sul 937 e' la fattura da
                    #    numerare prima — cioe' l'unica informazione che dice
                    #    all'operatore DOVE andare.
                    # ⚠️ Stessa conversione dell'envelope, e dallo STESSO posto:
                    #    il consumatore a video e' uno solo, e due forme
                    #    sarebbero due strade da tenere allineate a mano.
                    "targets": bersagli_envelope(exc.targets),
                }
                if lotto_id is None:
                    # Primo run su lotto nuovo fallito: nessun id da riportare → propaga.
                    raise
                break
            after_stato_doc = self.repository.get_lotto_stato_doc_fiscale_id(lotto_id)
            # D-Q: se il run si e` chiuso senza eccezione ma il lotto e` in
            # ERRORE (step completato con fatture difettose), fermarsi qui con
            # motivo parlante: iterare ancora rieseguirebbe lo stesso step su
            # dati identici. Motivo riusato (BLOCCATO_CRITICITA): i consumer lo
            # gestiscono gia`, e la semantica e` la stessa — criticita` attive.
            if self.repository.is_lotto_in_errore(lotto_id):
                if after_stato_doc != before_stato_doc:
                    step_eseguiti += 1
                    last_stato_doc = after_stato_doc
                motivo_stop = "BLOCCATO_CRITICITA"
                errore = {
                    "code": "E_PIPELINE_LOTTO_CRITICAL",
                    "message": (
                        "Step completato con fatture in errore: correggere e "
                        "rilanciare lo step."
                    ),
                    "detail": None,
                }
                break
            if after_stato_doc == before_stato_doc:
                if era_in_errore:
                    # Rilancio dello stesso step RIUSCITO (lotto uscito
                    # dall'errore, stato_doc invariato per costruzione): la
                    # catena ora puo` avanzare — si continua, non si esce con un
                    # finto COMPLETATO a meta` strada.
                    step_eseguiti += 1
                    last_stato_doc = after_stato_doc
                    continue
                # Nessun avanzamento: catena esaurita (nessuno step eseguito).
                motivo_stop = "COMPLETATO"
                break
            step_eseguiti += 1
            last_stato_doc = after_stato_doc
            # Fermata voluta (C-1, gate fiscale D-1): raggiunto lo stato
            # richiesto la catena si arresta QUI — la numerazione (DEFINITIVA)
            # e' un processo separato avviato da umano.
            if (
                params.fino_a_stato_doc_fiscale_id is not None
                and after_stato_doc == params.fino_a_stato_doc_fiscale_id
            ):
                motivo_stop = "FERMATO_A_STATO"
                break
            if after_stato_doc is not None and self.repository.is_stato_doc_chiude_lotto(
                after_stato_doc
            ):
                # Step di chiusura raggiunto: catena conclusa (non proseguire oltre).
                motivo_stop = "COMPLETATO"
                break
        stato_lotto = self.repository.get_lotto_job_stato(lotto_id) if lotto_id else None
        return {
            "lotto_id": lotto_id,
            "stato_lotto": stato_lotto,
            "stato_doc_fiscale_id": last_stato_doc,
            "step_eseguiti": step_eseguiti,
            "motivo_stop": motivo_stop,
            # None quando la catena non si e' fermata per errore.
            "errore": errore,
        }
