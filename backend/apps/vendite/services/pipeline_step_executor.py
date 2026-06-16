# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Esecuzione step pipeline vendite.
# ------------------------------------------------------------


import logging
from typing import Any

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.core.services.value_normalizer import as_bool
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.pipeline_repository import LottoContext, VenditePipelineRepository
from apps.vendite.services.pipeline_error_logger import PipelineErrorLogger
from apps.vendite.services.fatture_righe_service import FattureRigheService

# Esecutore di singolo step pipeline con mapping task JSON -> azioni applicative.

class PipelineStepExecutor:
    """Controparte Django della funzione SQL vendite.fn_execute_pipeline_step."""

    # Scopo: Inizializza la istanza.
    def __init__(
        self,
        repository: VenditePipelineRepository | None = None,
        fatture_righe_service: FattureRigheService | None = None,
        error_logger: PipelineErrorLogger | None = None,
        commesse_repository: CommesseRepository | None = None,
    ) -> None:
        self.repository = repository or VenditePipelineRepository()
        self.fatture_righe_service = fatture_righe_service or FattureRigheService(self.repository)
        self.error_logger = error_logger or PipelineErrorLogger(self.repository)
        self.commesse_repository = commesse_repository or CommesseRepository()
        self.handler_registry = {
            "select_attivita_default": self._handle_select_attivita_task,
            "generate_fatture_righe_default": self._handle_generate_fatture_righe_task,
            "genera_fondi_source_lotto_default": self._handle_genera_fondi_source_lotto_task,
            "applica_fondi_lotto_default": self._handle_applica_fondi_lotto_task,
            "ricalcola_iva_lotto_default": self._handle_ricalcola_iva_lotto_task,
            "prepare_sdi_payload_lotto_default": self._handle_prepare_sdi_payload_lotto_task,
            "numera_fatture_default": self._handle_numera_fatture_task,
            "close_lotto_default": self._handle_close_lotto_task,
            "reset_lotto_draft_default": self._handle_reset_lotto_draft_task,
            "pull_attivita_da_commessa_default": self._handle_pull_attivita_da_commessa_task,
        }

    # Scopo: Gestisce uno step pipeline validando input, risolvendo processi da configurazione DB e dispatch dei task
    def execute_step(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        tipo_lotto: str,
        *,
        rollback: bool = False,
        dry_run: bool = False,
    ) -> None:
        ErrorManager.require(
            bool(lotto_id and stato_doc_fiscale_id and tipo_lotto and tipo_lotto.strip()),
            code="E_PIPELINE_VALIDATION",
            message="Parametri pipeline non validi.",
            detail="lotto_id, stato_doc_fiscale_id e tipo_lotto sono obbligatori",
            context={
                "lotto_id": lotto_id,
                "stato_doc_fiscale_id": stato_doc_fiscale_id,
                "tipo_lotto": tipo_lotto,
            },
            function_name="vendite.pipeline_step_executor.execute_step",
            log_to_db=True,
        )

        context = self.repository.get_lotto_context(lotto_id)
        ErrorManager.require(
            context is not None and context.competenza_mese is not None,
            code="E_PIPELINE_LOTTO_NOT_FOUND",
            message="Lotto pipeline non trovato.",
            detail=f"Lotto non trovato: {lotto_id}",
            context={"lotto_id": lotto_id},
            function_name="vendite.pipeline_step_executor.execute_step",
            log_to_db=True,
        )
        assert context is not None

        processi = self.repository.get_step_processes(
            stato_doc_fiscale_id,
            tipo_lotto=tipo_lotto,
            utility_id=context.utility_id,
            tipo_doc_fiscale_id=context.tipo_doc_fiscale_id,
            rollback=rollback,
        )
        ErrorManager.require(
            bool(processi),
            code="E_PIPELINE_NOT_FOUND",
            message="Configurazione pipeline non trovata.",
            detail=(
                "Pipeline non trovata o processi vuoti per "
                f"stato_doc_fiscale_id={stato_doc_fiscale_id}, tipo_lotto={tipo_lotto}"
            ),
            context={
                "stato_doc_fiscale_id": stato_doc_fiscale_id,
                "tipo_lotto": tipo_lotto,
                "rollback": rollback,
            },
            function_name="vendite.pipeline_step_executor.execute_step",
            log_to_db=True,
        )

        pipeline_id = self.repository.get_pipeline_id_for_step(
            tipo_lotto,
            stato_doc_fiscale_id,
            utility_id=context.utility_id,
            tipo_doc_fiscale_id=context.tipo_doc_fiscale_id,
        )

        # Esegue in ordine i task definiti nel JSON processi/rollback.
        for process in processi:
            self._run_task(
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                process=process,
                context=context,
                rollback=rollback,
                dry_run=dry_run,
                pipeline_id=pipeline_id,
            )

    # Scopo: Gestisce il task di step con logging fase, risoluzione handler via registry e gestione errori applicativi
    def _run_task(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        process: dict[str, Any],
        context: LottoContext,
        rollback: bool,
        dry_run: bool,
        pipeline_id: int | None = None,
    ) -> None:
        task = str(process.get("task", "")).strip()
        fase = process.get("fase") or "Esecuzione step"
        params = process.get("params") or {}
        fn_name = params.get("fn")
        implementation_key = params.get("implementation_key")

        self.repository.log_pipeline_fase(
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            fase=fase,
            status="I",
            messaggio=None,
            meta={
                "task": task,
                "params": params,
                "rollback": rollback,
                "dry_run": dry_run,
            },
        )

        if task in {"noop", "log_only"}:
            return

        handler_code = self.repository.get_task_handler_code(
            task_code=task,
            implementation_key=implementation_key,
        )

        if dry_run:
            return

        task_handler = self.handler_registry.get(handler_code)
        if task_handler is None:
            self.error_logger.log_error(
                scope="LOTTO",
                severity="C",
                code="E_TASK_IMPLEMENTATION_NOT_FOUND",
                message="Implementazione task pipeline non trovata.",
                detail=f"Implementazione task non trovata: {task} ({handler_code})",
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                context={
                    "task": task,
                    "fase": fase,
                    "implementation_key": implementation_key,
                    "handler_code": handler_code,
                    "rollback": rollback,
                },
                function_name="vendite.pipeline_step_executor._run_task",
            )
            ErrorManager.raise_error(
                code="E_TASK_IMPLEMENTATION_NOT_FOUND",
                message="Implementazione task pipeline non trovata.",
                detail=f"Implementazione task non trovata: {task} ({handler_code})",
                context={
                    "task": task,
                    "fase": fase,
                    "implementation_key": implementation_key,
                    "handler_code": handler_code,
                },
                function_name="vendite.pipeline_step_executor._run_task",
                log_to_db=True,
            )

        # Tracing: risolve modalità esecuzione task e apre run se policy attiva.
        task_run_id: int | None = None
        if pipeline_id is not None and self.repository.task_policy_exists(pipeline_id, task):
            exec_mode = self.repository.resolve_lotto_task_execution_mode(
                lotto_id, pipeline_id, stato_doc_fiscale_id, task
            )
            if exec_mode.execution_mode == "SKIP":
                return
            if exec_mode.execution_mode == "RESET_REQUIRED":
                self.error_logger.log_error(
                    scope="LOTTO",
                    severity="C",
                    code="E_TASK_RESET_REQUIRED",
                    message="Task richiede reset prima dell'esecuzione.",
                    detail=f"Reset richiesto per task {task}, lotto_id={lotto_id}",
                    lotto_id=lotto_id,
                    stato_doc_fiscale_id=stato_doc_fiscale_id,
                    context={
                        "task": task,
                        "pipeline_id": pipeline_id,
                        "last_task_stato": exec_mode.last_task_stato,
                        "last_tentativo": exec_mode.last_tentativo,
                    },
                    function_name="vendite.pipeline_step_executor._run_task",
                )
                ErrorManager.raise_error(
                    code="E_TASK_RESET_REQUIRED",
                    message="Task richiede reset prima dell'esecuzione.",
                    detail=f"Reset richiesto per task {task}, lotto_id={lotto_id}",
                    context={
                        "task": task,
                        "pipeline_id": pipeline_id,
                        "lotto_id": lotto_id,
                    },
                    function_name="vendite.pipeline_step_executor._run_task",
                    log_to_db=True,
                )
            task_run_result = self.repository.start_lotto_task_run(
                lotto_id=lotto_id,
                pipeline_id=pipeline_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                task_code=task,
                fase=fase,
                meta={"rollback": rollback},
            )
            task_run_id = task_run_result.task_run_id

        try:
            task_handler(
                task=task,
                fn_name=fn_name,
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                context=context,
                params=params,
                dry_run=dry_run,
            )
        except Exception as exc:
            self._fail_task_run_safely(task_run_id, exc)
            raise
        if task_run_id is not None:
            self.repository.complete_lotto_task_run(task_run_id)

    # Scopo: Tenta di marcare il task run in errore senza mascherare l'eccezione originale.
    def _fail_task_run_safely(self, task_run_id: int | None, exc: BaseException) -> None:
        if task_run_id is None:
            return
        try:
            error_code = exc.code if isinstance(exc, ServiceError) else "E_TASK"
            self.repository.fail_lotto_task_run(
                task_run_id,
                error_code,
                str(exc),
            )
        except Exception:
            pass  # Mai mascherare l'eccezione originale.

    # Scopo: Valida la funzione legacy `fn` del task contro whitelist consentita per evitare override non ammessi.
    def _validate_task_function_name(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int | None = None,
        stato_doc_fiscale_id: int | None = None,
    ) -> None:
        # `fn` resta un token di compatibilita` SQL nella configurazione processi.
        allowed = self.repository.ALLOWED_TASK_FUNCTIONS.get(task)
        if allowed is None:
            return
        if fn_name and fn_name != allowed:
            if lotto_id is not None:
                self.error_logger.log_error(
                    scope="LOTTO",
                    severity="C",
                    code="E_TASK_NOT_ALLOWED",
                    message="Funzione task non ammessa.",
                    detail=f"Funzione non ammessa per task {task}: {fn_name}",
                    lotto_id=lotto_id,
                    stato_doc_fiscale_id=stato_doc_fiscale_id,
                    context={"task": task, "fn": fn_name, "allowed": allowed},
                    function_name="vendite.pipeline_step_executor._validate_task_function_name",
                )
            ErrorManager.raise_error(
                code="E_TASK_NOT_ALLOWED",
                message="Funzione task non ammessa.",
                detail=f"Funzione non ammessa per task {task}: {fn_name}",
                context={"task": task, "fn": fn_name},
                function_name="vendite.pipeline_step_executor._validate_task_function_name",
                log_to_db=True,
            )

    # Scopo: Gestisce un'azione per ogni fattura del lotto con logging errori scope FATTURA e fail-fast
    def _run_per_fattura_task(
        self,
        *,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        task: str,
        fattura_ids: list[int],
        action: Any,
    ) -> None:
        # Helper riusabile: esecuzione task per-fattura con logging scope FATTURA.
        for fattura_id in fattura_ids:
            try:
                action(fattura_id)
            except ServiceError as exc:
                self._log_fattura_task_error(
                    task=task,
                    lotto_id=lotto_id,
                    fattura_id=fattura_id,
                    stato_doc_fiscale_id=stato_doc_fiscale_id,
                    code=exc.code,
                    detail=exc.detail or str(exc),
                )
                raise
            except Exception as exc:
                self._log_fattura_task_error(
                    task=task,
                    lotto_id=lotto_id,
                    fattura_id=fattura_id,
                    stato_doc_fiscale_id=stato_doc_fiscale_id,
                    code="E_TASK_FATTURA",
                    detail=str(exc),
                )
                ErrorManager.raise_error(
                    code="E_TASK_FATTURA",
                    message="Errore su singola fattura durante task pipeline.",
                    detail=f"Task {task} fallito su fattura_id={fattura_id}: {exc}",
                    context={
                        "lotto_id": lotto_id,
                        "fattura_id": fattura_id,
                        "stato_doc_fiscale_id": stato_doc_fiscale_id,
                        "task": task,
                    },
                    function_name="vendite.pipeline_step_executor._run_per_fattura_task",
                    log_to_db=True,
                    cause=exc,
                )

    # Scopo: Scrive un errore task a livello fattura con metadati di contesto pipeline.
    def _log_fattura_task_error(
        self,
        *,
        task: str,
        lotto_id: int,
        fattura_id: int,
        stato_doc_fiscale_id: int,
        code: str,
        detail: str,
    ) -> None:
        self.error_logger.log_error(
            scope="FATTURA",
            severity="C",
            code=code,
            message=f"Errore task {task} su fattura {fattura_id}",
            detail=detail,
            lotto_id=lotto_id,
            fattura_id=fattura_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            context={"task": task},
            function_name="vendite.pipeline_step_executor._run_per_fattura_task",
        )

    # Scopo: Applica validazione task e gate dry-run prima di eseguire l'azione reale.
    def _run_validated_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        dry_run: bool,
        action: Any,
    ) -> None:
        self._validate_task_function_name(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
        )
        if dry_run:
            return
        action()

    # Scopo: Seleziona e opzionalmente locka le attivita fatturabili eleggibili per il lotto.
    def _handle_select_attivita_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_select_attivita_task(
                context=context,
                params=params,
            ),
        )

    # Scopo: Genera le righe fattura per il lotto usando il servizio di dominio.
    def _handle_generate_fatture_righe_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.fatture_righe_service.generate_fatture_righe(
                lotto_id,
                dry_run=dry_run,
            ),
        )

    # Scopo: Numera le fatture del lotto, gestisce errori per-fattura e sincronizza stato finale lotto-fatture.
    def _handle_numera_fatture_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Numerazione documenti per lotto massivo con sync stato documento.
        def _action() -> None:
            fattura_ids = self.repository.list_fatture_by_lotto(lotto_id)
            self._run_per_fattura_task(
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                task=task,
                fattura_ids=fattura_ids,
                action=self.repository.numera_fattura_opz_emessa,
            )
            self.repository.sync_lotto_fatture_stato(
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
            )

        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=_action,
        )

    # Scopo: Genera o aggiorna le source fondi per tutte le fatture del lotto.
    def _handle_genera_fondi_source_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Genera/aggiorna source fondi su tutte le fatture del lotto.
        tipo_fondo = str(params.get("tipo_fondo_codice_interno") or "F_F_ADD_ACC")
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_genera_fondi_source_lotto_task(
                lotto_id=lotto_id,
                tipo_fondo_codice_interno=tipo_fondo,
            ),
        )

    # Scopo: Applica i fondi source alle fatture del lotto secondo il tipo fondo configurato.
    def _handle_applica_fondi_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Applica i fondi source alle fatture del lotto.
        tipo_fondo = str(params.get("tipo_fondo_codice_interno") or "F_F_ADD_ACC")
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_applica_fondi_lotto_task(
                lotto_id=lotto_id,
                tipo_fondo_codice_interno=tipo_fondo,
            ),
        )

    # Scopo: Ricalcola i riepiloghi IVA del lotto applicando batch size configurabile.
    def _handle_ricalcola_iva_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Ricalcolo IVA lotto; include aggiornamento totali testata.
        batch_size_raw = params.get("batch_size")
        batch_size = int(batch_size_raw) if batch_size_raw is not None else 1000
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_ricalcola_iva_lotto_task(
                lotto_id=lotto_id,
                batch_size=batch_size,
            ),
        )

    # Scopo: Prepara payload SDI del lotto con parametri stato/tentativo normalizzati.
    def _handle_prepare_sdi_payload_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Preparazione dataset SDI e apertura tentativi per le fatture del lotto.
        stato_sdi_codice_interno = str(params.get("stato_sdi_codice_interno") or "DA_INVIARE")
        force_new_tentativo = as_bool(params.get("force_new_tentativo"), default=False)
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.run_prepare_sdi_payload_lotto_task(
                lotto_id=lotto_id,
                stato_sdi_codice_interno=stato_sdi_codice_interno,
                force_new_tentativo=force_new_tentativo,
            ),
        )

    # Scopo: Chiude operativamente il lotto impostando lo stato operativo a CHIUSO.
    def _handle_close_lotto_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Chiusura operativa lotto: stato_operativo=CHIUSO.
        def _action() -> None:
            if not self.repository.is_stato_doc_chiude_lotto(stato_doc_fiscale_id):
                return
            self.repository.close_lotto_operativo(lotto_id)

        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=_action,
        )

    # Scopo: Gestisce il reset tecnico completo del lotto in stato DRAFT
    def _handle_reset_lotto_draft_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        # Reset tecnico completo del lotto massivo in bozza.
        self._run_validated_task(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            dry_run=dry_run,
            action=lambda: self.repository.reset_lotto_draft(lotto_id),
        )

    # Scopo: Pull commesse → attivita fatturabili (step 0 pipeline fatturazione).
    # Isola gli errori per commessa: un fallimento su una commessa non blocca le altre.
    # In caso di errori parziali il task prosegue e logga; se tutte falliscono alza errore.
    def _handle_pull_attivita_da_commessa_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        self._validate_task_function_name(
            task=task,
            fn_name=fn_name,
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
        )
        commessa_ids = self.commesse_repository.list_commesse_emittibili(
            competenza_mese=context.competenza_mese,
            utility_id=context.utility_id,
            billing_account_id=context.billing_account_id,
            emittente_soggetto_ruolo_id=context.emittente_soggetto_ruolo_id,
            # Corsia: filtro propagato dal lotto (meta), non re-derivato qui dal
            # tipo_lotto (separazione immediata/differita decisa dal driver).
            fatturazione_immediata=context.fatturazione_immediata,
        )
        if dry_run:
            return
        # Isolamento per commessa: savepoint per ogni emit; errore loggato ma non blocca le altre.
        logger = logging.getLogger(__name__)
        errors: list[str] = []
        for commessa_id in commessa_ids:
            try:
                with transaction.atomic():
                    self.commesse_repository.emit_attivita_fatturabili(
                        commessa_id,
                        dry_run=dry_run,
                    )
            except Exception as exc:
                msg = f"Errore emit commessa_id={commessa_id}: {type(exc).__name__}: {exc}"
                logger.exception(msg)
                errors.append(msg)
                self.error_logger.log_error(
                    scope="LOTTO",
                    severity="C",
                    code="E_PULL_COMMESSA",
                    message=f"Errore emissione commessa {commessa_id}",
                    detail=msg,
                    lotto_id=lotto_id,
                    stato_doc_fiscale_id=stato_doc_fiscale_id,
                    context={"commessa_id": commessa_id, "task": task},
                    function_name="vendite.pipeline_step_executor._handle_pull_attivita_da_commessa_task",
                )
        # Se tutte le commesse falliscono, il task e` fallito.
        if errors and len(errors) == len(commessa_ids):
            ErrorManager.raise_error(
                code="E_PULL_COMMESSA_ALL_FAILED",
                message="Emissione commesse fallita per tutte le commesse.",
                detail=f"Errori: {len(errors)}/{len(commessa_ids)}",
                context={"lotto_id": lotto_id, "errors": errors[:5]},
                function_name="vendite.pipeline_step_executor._handle_pull_attivita_da_commessa_task",
                log_to_db=True,
            )
