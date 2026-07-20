# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo pipeline vendite.
# ------------------------------------------------------------


from dataclasses import replace
from datetime import date

from apps.core.db.dbops_repository import DbopsRepository
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

# Facade servizi: mantiene firme dichiarative e delega alle classi OOP.

# Scopo: Helper privato — valida i lookup ID opzionali della pipeline contro le
#        tabelle config attive. Estratto (2ª occorrenza: run_lotto_pipeline +
#        run_lotto_pipeline_until_done) per evitare duplicazione.
def _validate_pipeline_lookups(
    *,
    tipo_doc_fiscale_id: int | None,
    utility_id: int | None,
    function_name: str,
) -> None:
    if tipo_doc_fiscale_id is not None:
        dbops = DbopsRepository()
        if not dbops.check_lookup_id_exists(rel="config.tipi_doc_fiscale", record_id=tipo_doc_fiscale_id):
            ErrorManager.raise_error(
                code="E_PIPELINE_VALIDATION",
                message="Tipo documento fiscale non valido.",
                detail=f"tipo_doc_fiscale_id={tipo_doc_fiscale_id} non trovato o non attivo in config.tipi_doc_fiscale",
                context={"tipo_doc_fiscale_id": tipo_doc_fiscale_id},
                function_name=function_name,
            )
    if utility_id is not None:
        dbops = DbopsRepository()
        if not dbops.check_lookup_id_exists(rel="config.utilities", record_id=utility_id):
            ErrorManager.raise_error(
                code="E_PIPELINE_VALIDATION",
                message="Utility non valida.",
                detail=f"utility_id={utility_id} non trovato o non attivo in config.utilities",
                context={"utility_id": utility_id},
                function_name=function_name,
            )


# Cache modulo-level codice->id degli stati di fermata (C-1): vocabolario
# config seed-stabile, un solo lookup per processo per codice.
_STATO_FERMATA_ID_CACHE: dict[str, int] = {}


# Scopo: Costruisce i params del runner dai kwargs del facade (riuso single/until-done).
def _build_pipeline_params(
    *,
    lotto_id: int | None,
    competenza_mese: date | None,
    tipo_doc_fiscale_id: int | None,
    utility_id: int | None,
    billing_account_id: int | None,
    emittente_soggetto_ruolo_id: int | None,
    lock_batch_id: str | None,
    meta: LottoPipelineMeta | None,
    dry_run: bool,
    tipo_lotto: str,
) -> LottoPipelineParams:
    return LottoPipelineParams(
        lotto_id=lotto_id,
        competenza_mese=competenza_mese,
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        utility_id=utility_id,
        billing_account_id=billing_account_id,
        emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
        lock_batch_id=lock_batch_id,
        meta=meta,
        dry_run=dry_run,
        tipo_lotto=tipo_lotto,
    )


# Scopo: Facade applicativa: avvia il runner pipeline lotto e restituisce lotto_id eseguito.
def run_lotto_pipeline(
    *,
    lotto_id: int | None = None,
    competenza_mese: date | None = None,
    tipo_doc_fiscale_id: int | None = None,
    utility_id: int | None = None,
    billing_account_id: int | None = None,
    emittente_soggetto_ruolo_id: int | None = None,
    lock_batch_id: str | None = None,
    meta: LottoPipelineMeta | None = None,
    dry_run: bool = False,
    tipo_lotto: str = "MASSIVO",
) -> int:
    """Entrypoint servizio Python per avvio pipeline lotto vendite (UN solo step)."""
    _validate_pipeline_lookups(
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        utility_id=utility_id,
        function_name="vendite.pipeline_service.run_lotto_pipeline",
    )
    runner = LottoPipelineRunner()
    params = _build_pipeline_params(
        lotto_id=lotto_id,
        competenza_mese=competenza_mese,
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        utility_id=utility_id,
        billing_account_id=billing_account_id,
        emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
        lock_batch_id=lock_batch_id,
        meta=meta,
        dry_run=dry_run,
        tipo_lotto=tipo_lotto,
    )
    return runner.run_pipeline(params)


# Scopo: Facade applicativa (driver F2): esegue la pipeline del lotto fino in fondo
#        (più step concatenati) e restituisce l'esito strutturato del driver.
def run_lotto_pipeline_until_done(
    *,
    lotto_id: int | None = None,
    competenza_mese: date | None = None,
    tipo_doc_fiscale_id: int | None = None,
    utility_id: int | None = None,
    billing_account_id: int | None = None,
    emittente_soggetto_ruolo_id: int | None = None,
    lock_batch_id: str | None = None,
    meta: LottoPipelineMeta | None = None,
    dry_run: bool = False,
    tipo_lotto: str = "MASSIVO",
    fino_a_stato: str | None = None,
) -> dict[str, object]:
    """Entrypoint servizio Python per eseguire la catena lotto fino a conclusione.

    `fino_a_stato` (C-1, gate fiscale D-1): codice_interno di
    config.stati_doc_fiscale (es. 'EMESSA') a cui la catena si FERMA con
    motivo_stop=FERMATO_A_STATO. None = fino in fondo (storico)."""
    _validate_pipeline_lookups(
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        utility_id=utility_id,
        function_name="vendite.pipeline_service.run_lotto_pipeline_until_done",
    )
    runner = LottoPipelineRunner()
    # Risoluzione codice -> id qui (il runner confronta id, Python puro), con
    # cache modulo-level: config.stati_doc_fiscale e' vocabolario seed stabile
    # (gli id non cambiano a runtime) e il driver chiama questa facade una
    # volta PER TERNA con lo stesso codice — senza cache sarebbero N lookup
    # identici per giro.
    fino_a_stato_id: int | None = None
    if fino_a_stato is not None:
        fino_a_stato_id = _STATO_FERMATA_ID_CACHE.get(fino_a_stato)
        if fino_a_stato_id is None:
            fino_a_stato_id = runner.repository.get_stato_doc_fiscale_id(fino_a_stato)
            ErrorManager.require(
                fino_a_stato_id is not None,
                code="E_PIPELINE_VALIDATION",
                message="Stato di fermata non valido.",
                detail=f"fino_a_stato={fino_a_stato!r} non trovato in config.stati_doc_fiscale",
                context={"fino_a_stato": fino_a_stato},
                function_name="vendite.pipeline_service.run_lotto_pipeline_until_done",
            )
            assert fino_a_stato_id is not None
            _STATO_FERMATA_ID_CACHE[fino_a_stato] = fino_a_stato_id
    params = _build_pipeline_params(
        lotto_id=lotto_id,
        competenza_mese=competenza_mese,
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        utility_id=utility_id,
        billing_account_id=billing_account_id,
        emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
        lock_batch_id=lock_batch_id,
        meta=meta,
        dry_run=dry_run,
        tipo_lotto=tipo_lotto,
    )
    if fino_a_stato_id is not None:
        params = replace(params, fino_a_stato_doc_fiscale_id=fino_a_stato_id)
    return runner.run_lotto_until_done(params)


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

