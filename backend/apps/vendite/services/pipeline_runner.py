# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestrazione esecuzione pipeline vendite.
# ------------------------------------------------------------


from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from django.db import transaction

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
        correlation_id: str | None = None,
    ) -> None:
        # Mantiene stato lotto coerente e traccia errore con codice uniforme.
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
            self.repository.log_event(
                domain="PIPELINE",
                entity_type="LOTTO",
                entity_id=lotto_id,
                event_code="PIPELINE_ERROR",
                severity="ERROR",
                correlation_id=correlation_id,
                payload={"code": code, "detail": detail, "tipo_lotto": tipo_lotto},
            )

    # Scopo: Prova a marcare il lotto in errore senza mascherare l'eccezione principale.
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
        try:
            self._mark_lotto_error(
                lotto_id=lotto_id,
                code=code,
                tipo_lotto=tipo_lotto,
                detail=detail,
                correlation_id=correlation_id,
            )
        except Exception as mark_exc:
            ErrorManager.log_error_only(
                code="E_PIPELINE_MARK_ERROR",
                context={
                    "lotto_id": lotto_id,
                    "tipo_lotto": tipo_lotto,
                    "detail": detail,
                    "mark_error": str(mark_exc),
                },
                area="backend",
                function_name="vendite.run_lotto_pipeline",
            )

    # Scopo: Normalizza lotto_id (0/None = "nuovo lotto", crea) → None oppure id reale.
    @staticmethod
    def _normalize_lotto_id(lotto_id: int | None) -> int | None:
        return None if lotto_id in (0, None) else lotto_id

    # Scopo: Determina da quale step (singolo) ripartire. Tre casi:
    #  - rerun MASSIVO in errore: ri-esegue dallo step CORRENTE (invariato);
    #  - successo su lotto ESISTENTE (lotto_id passato dal driver): avanza allo step
    #    SUCCESSIVO a quello gia` eseguito — abilita la progressione multi-step, prima
    #    assente nel ramo di successo (steps[:1] prendeva sempre il primo step);
    #  - primo run / lotto appena creato / stato non in catalogo: dal primo step.
    @staticmethod
    def _resolve_steps_for_run(
        *,
        steps: list[Any],
        is_existing_lotto_request: bool,
        is_massivo_error_rerun: bool,
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
        if is_massivo_error_rerun:
            # Resume su step corrente in errore; evita transizioni retroattive non ammesse.
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
        )
        # Allineamento fatture allo stato dello step (parametrico, per-step): la fattura
        # segue il lotto 1→2→8→3, così EMESSA congela l'IVA prima della numerazione in
        # DEFINITIVA (evita il salto 1→8 vietato dalla matrice transizioni). Eseguito DOPO
        # i task dello step (semantica "EMESSA = IVA certificata"); idempotente grazie al
        # guard `IS DISTINCT FROM` in fn_sync_lotto_fatture_stato (step DRAFT → 1→1 no-op).
        # Solo forward (questo metodo non è il path di rollback) e mai in dry-run.
        if not dry_run:
            self.repository.sync_lotto_fatture_stato(
                lotto_id=lotto_id,
                stato_doc_fiscale_id=step.stato_doc_fiscale_id,
            )
        self.repository.log_lotto_esito_fatture(lotto_id)
        self.repository.log_event(
            domain="PIPELINE",
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

    # Scopo: Risolve o crea il lotto in transazione autonoma.
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
        return lotto_id, is_existing_lotto_request

    # Scopo: Orchestra l'intero flusso pipeline lotto: risoluzione lotto, step execution, resume/rollback e gestione errori finali.
    def run_pipeline(self, params: LottoPipelineParams) -> int:
        lotto_id: int | None = None
        correlation_id: str | None = None
        effective_tipo_lotto = params.tipo_lotto or "MASSIVO"
        try:
            # Fase 1: risoluzione lotto in transazione autonoma.
            # Il lotto persiste anche se la fase di esecuzione fallisce,
            # consentendo a _mark_lotto_error_safely di trovarlo e marcarlo.
            lotto_id, is_existing_lotto_request = self._resolve_lotto(params)

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
                    is_massivo_error_rerun=is_massivo_error_rerun,
                    lotto_stato_doc_corrente=lotto_stato_doc_corrente,
                )
                # Modalita` operativa: un run esegue un solo step pipeline (il prossimo disponibile).
                steps = steps[:1]
                # Blocco avanzamento: con almeno una criticita` attiva il lotto richiede correzioni.
                lotto_signal_status = self.lotto_segnalazioni_service.evaluate_lotto_status(lotto_id)
                if lotto_signal_status.blocks_next_step:
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
                self.repository.set_lotto_job_stato(lotto_id, "IN_ESECUZIONE", "Avvio pipeline")
                correlation_id = (
                    str(lotto_context.lock_batch_id)
                    if getattr(lotto_context, "lock_batch_id", None)
                    else None
                )
                self.repository.log_event(
                    domain="PIPELINE",
                    entity_type="LOTTO",
                    entity_id=lotto_id,
                    event_code="PIPELINE_STARTED",
                    correlation_id=correlation_id,
                    payload={
                        "tipo_lotto": effective_tipo_lotto,
                        "dry_run": params.dry_run,
                    },
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
                        )

                    self._execute_pipeline_step(
                        lotto_id=lotto_id,
                        step=step,
                        effective_tipo_lotto=effective_tipo_lotto,
                        dry_run=params.dry_run,
                        correlation_id=correlation_id,
                    )

                self.repository.set_lotto_job_stato(lotto_id, "COMPLETATO", "Pipeline completata")
                self.repository.log_event(
                    domain="PIPELINE",
                    entity_type="LOTTO",
                    entity_id=lotto_id,
                    event_code="PIPELINE_COMPLETED",
                    correlation_id=correlation_id,
                    payload={"tipo_lotto": effective_tipo_lotto},
                )
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
    def run_lotto_until_done(self, params: LottoPipelineParams) -> dict[str, Any]:
        lotto_id = self._normalize_lotto_id(params.lotto_id)
        step_eseguiti = 0
        last_stato_doc: int | None = None
        motivo_stop = "COMPLETATO"
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
            run_params = params if lotto_id is None else replace(params, lotto_id=lotto_id)
            try:
                lotto_id = self.run_pipeline(run_params)
            except ServiceError as exc:
                motivo_stop = (
                    "BLOCCATO_CRITICITA"
                    if exc.code == "E_PIPELINE_LOTTO_CRITICAL"
                    else "ERRORE"
                )
                if lotto_id is None:
                    # Primo run su lotto nuovo fallito: nessun id da riportare → propaga.
                    raise
                break
            after_stato_doc = self.repository.get_lotto_stato_doc_fiscale_id(lotto_id)
            if after_stato_doc == before_stato_doc:
                # Nessun avanzamento: catena esaurita (nessuno step eseguito).
                motivo_stop = "COMPLETATO"
                break
            step_eseguiti += 1
            last_stato_doc = after_stato_doc
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
        }
