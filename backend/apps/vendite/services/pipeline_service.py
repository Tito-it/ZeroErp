# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo pipeline vendite.
# ------------------------------------------------------------


from datetime import date

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import SdiPayloadRow, VenditePipelineRepository
from apps.vendite.services.lotto_segnalazioni_service import LottoSegnalazioniService
from apps.vendite.services.pipeline_runner import LottoPipelineParams, LottoPipelineRunner
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor
from apps.vendite.services.fatture_righe_service import FattureRigheService
from apps.vendite.services.lotto_reset_service import LottoResetService
from apps.vendite.types import (
    GroupAttivitaKey,
    LottoPipelineMeta,
    LottoTaskRunRow,
    ResetLottoDraftResult,
    ResetLottoFatturaDraftResult,
)

# Facade servizi: mantiene firme SQL-like e delega alle classi OOP.

# Scopo: Facade applicativa: avvia il runner pipeline lotto e restituisce lotto_id eseguito.
def pr_run_lotto_pipeline(
    *,
    lotto_id: int | None = None,
    competenza_mese: date | None = None,
    tipo_doc_fiscale_id: int | None = None,
    utility_id: int | None = None,
    billing_account_id: int | None = None,
    lock_batch_id: str | None = None,
    meta: LottoPipelineMeta | None = None,
    dry_run: bool = False,
    tipo_lotto: str = "MASSIVO",
) -> int:
    """Entrypoint servizio Python con lo stesso intento della procedura SQL pr_run_lotto_pipeline."""
    # Facade sottile: firma simile alla SQL, comportamento delegato al runner OOP.
    runner = LottoPipelineRunner()
    params = LottoPipelineParams(
        lotto_id=lotto_id,
        competenza_mese=competenza_mese,
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        utility_id=utility_id,
        billing_account_id=billing_account_id,
        lock_batch_id=lock_batch_id,
        meta=meta,
        dry_run=dry_run,
        tipo_lotto=tipo_lotto,
    )
    return runner.run_pipeline(params)


# Scopo: Facade applicativa: esegue un singolo step pipeline sul lotto richiesto.
def fn_execute_pipeline_step(
    *,
    lotto_id: int,
    stato_doc_fiscale_id: int,
    tipo_lotto: str = "MASSIVO",
    rollback: bool = False,
    dry_run: bool = False,
) -> None:
    """Entrypoint servizio Python con lo stesso intento della funzione SQL fn_execute_pipeline_step."""
    # Facade usata da API/test e futuri handler applicativi.
    executor = PipelineStepExecutor()
    executor.execute_step(
        lotto_id=lotto_id,
        stato_doc_fiscale_id=stato_doc_fiscale_id,
        tipo_lotto=tipo_lotto,
        rollback=rollback,
        dry_run=dry_run,
    )


# Scopo: Facade applicativa: prepara payload SDI per lotto e restituisce dataset strutturato.
def fn_prepare_sdi_payload_lotto(
    *,
    lotto_id: int,
    stato_sdi_codice_interno: str = "DA_INVIARE",
    force_new_tentativo: bool = False,
) -> list[SdiPayloadRow]:
    """Entrypoint servizio Python per estrazione payload SDI da lotto."""
    repository = VenditePipelineRepository()
    return repository.run_prepare_sdi_payload_lotto_task(
        lotto_id=lotto_id,
        stato_sdi_codice_interno=stato_sdi_codice_interno,
        force_new_tentativo=force_new_tentativo,
    )


# Scopo: Facade applicativa: calcola la chiave di grouping per una attivita fatturabile.
def fn_group_attivita_fatturabili(*, attivita_id: int) -> GroupAttivitaKey:
    """Entrypoint servizio Python con lo stesso intento della funzione SQL fn_group_attivita_fatturabili."""
    service = FattureRigheService()
    return service.group_attivita_fatturabili(attivita_id)


# Scopo: Facade applicativa: genera le righe fattura del lotto e restituisce il riepilogo elaborazione.
def fn_generate_fatture_righe(*, lotto_id: int, dry_run: bool = False) -> int:
    """Entrypoint servizio Python con lo stesso intento della funzione SQL fn_generate_fatture_righe."""
    service = FattureRigheService()
    return service.generate_fatture_righe(lotto_id, dry_run=dry_run)


# Scopo: Facade applicativa: esegue reset tecnico completo del lotto in stato DRAFT.
def fn_reset_lotto_draft(*, lotto_id: int) -> ResetLottoDraftResult:
    """Entrypoint servizio Python con lo stesso intento della funzione SQL fn_reset_lotto_draft."""
    service = LottoResetService()
    return service.reset_lotto_draft(lotto_id)


# Scopo: Facade applicativa: esegue reset tecnico della singola fattura DRAFT nel lotto.
def fn_reset_lotto_fattura_draft(
    *,
    lotto_id: int,
    fattura_id: int,
) -> ResetLottoFatturaDraftResult:
    """Entrypoint servizio Python per reset singola fattura del lotto."""
    service = LottoResetService()
    return service.reset_lotto_fattura_draft(lotto_id, fattura_id)


# Scopo: Restituisce riepilogo segnalazioni del lotto con regola di blocco step successivo.
def fn_get_lotto_segnalazioni_summary(*, lotto_id: int) -> dict[str, object]:
    ErrorManager.require(
        bool(lotto_id and lotto_id > 0),
        code="E_PIPELINE_VALIDATION",
        message="Parametri pipeline non validi.",
        detail="lotto_id obbligatorio e > 0",
        context={"lotto_id": lotto_id},
        function_name="vendite.pipeline_service.fn_get_lotto_segnalazioni_summary",
        log_to_db=True,
    )
    service = LottoSegnalazioniService()
    status = service.evaluate_lotto_status(lotto_id)
    return {
        "lotto_id": lotto_id,
        "critical_count": status.critical_count,
        "warning_count": status.warning_count,
        "attention_count": status.attention_count,
        "is_error": status.is_error,
        "blocks_next_step": status.blocks_next_step,
        "summary": status.summary,
    }


# Scopo: Restituisce i task run runtime del lotto per consultazione operativa (API/UI).
def fn_get_lotto_task_runs(*, lotto_id: int, limit: int = 100) -> dict[str, object]:
    ErrorManager.require(
        bool(lotto_id and lotto_id > 0),
        code="E_PIPELINE_VALIDATION",
        message="Parametri pipeline non validi.",
        detail="lotto_id obbligatorio e > 0",
        context={"lotto_id": lotto_id},
        function_name="vendite.pipeline_service.fn_get_lotto_task_runs",
        log_to_db=True,
    )
    ErrorManager.require(
        1 <= int(limit) <= 500,
        code="E_PIPELINE_VALIDATION",
        message="Parametri pipeline non validi.",
        detail="limit deve essere compreso tra 1 e 500",
        context={"lotto_id": lotto_id, "limit": limit},
        function_name="vendite.pipeline_service.fn_get_lotto_task_runs",
        log_to_db=True,
    )
    repository = VenditePipelineRepository()
    runs: list[LottoTaskRunRow] = repository.list_lotto_task_runs(lotto_id, limit=limit)
    return {
        "lotto_id": lotto_id,
        "count": len(runs),
        "task_runs": runs,
    }
