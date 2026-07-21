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


# Scopo: Guard comune dei verbi per-lotto (C-4 numera, C-8 ristampa — estratto
#        alla 2ª occorrenza, regola del 2): carica il lotto nello scope
#        operatore (fuori scope/inesistente → 404 unificato E_LOTTO_NON_TROVATO),
#        risolve l'id dello stato fiscale richiesto (fail-fast su config rotta:
#        senza questo guard, lookup None e lotto con stato NULL passerebbero il
#        gate per None == None) e applica il gate di stato con l'errore di
#        dominio parlante del verbo chiamante. Ritorna il lotto caricato.
def _get_lotto_in_stato(
    *,
    lotto_id: int,
    auth_user_id: int | None,
    stato_codice: str,
    error_code: str,
    error_message: str,
) -> dict[str, object]:
    from apps.vendite.db.vendite_repository import VenditeRepository

    lotto = VenditeRepository().get_lotto(lotto_id=lotto_id, auth_user_id=auth_user_id)
    ErrorManager.require(
        lotto is not None,
        code="E_LOTTO_NON_TROVATO",
        message="Lotto non trovato.",
        detail=f"lotto_id={lotto_id}",
    )
    assert lotto is not None

    stato_id = VenditePipelineRepository().get_stato_doc_fiscale_id(stato_codice)
    ErrorManager.require(
        stato_id is not None,
        code="E_PIPELINE_VALIDATION",
        message=(
            f"Stato {stato_codice} non configurato in config.stati_doc_fiscale."
        ),
    )
    ErrorManager.require(
        lotto["stato_doc_fiscale_id"] == stato_id,
        code=error_code,
        message=error_message,
        detail=(
            f"lotto_id={lotto_id} "
            f"stato_doc_fiscale_id={lotto['stato_doc_fiscale_id']} atteso={stato_id}"
        ),
    )
    return lotto


# Scopo: C-4 — Numerazione (step DEFINITIVA) di un SINGOLO lotto EMESSA.
#        Obiettivo: eseguire il verbo fiscale «Rendi definitive» su un lotto,
#        come atto separato e consapevole (gate fiscale I-7): lo step DEFINITIVA
#        contiene `numera_fatture` (numera, atomico) E `stampa_documenti_lotto`
#        (che ACCODA la stampa, I-2/I-4b) — l'endpoint non chiama la stampa per
#        conto suo. Perimetro: un lotto per chiamata (I-3 sincrono); il giro di
#        perimetro (più lotti) passa dalla coda lavori generica (background).
#        Risultato: l'esito strutturato del runner (motivo_stop, stato).
#        Guard: scope operatore + stato EMESSA (via _get_lotto_in_stato — il
#        gate fiscale non sta dietro lo stesso pulsante della pre-fiscale).
def numera_lotto(
    *, lotto_id: int, auth_user_id: int | None = None,
) -> dict[str, object]:
    _get_lotto_in_stato(
        lotto_id=lotto_id,
        auth_user_id=auth_user_id,
        stato_codice="EMESSA",
        error_code="E_LOTTO_NON_NUMERABILE",
        error_message=(
            "Il lotto non è in stato EMESSA: la numerazione (Rendi definitive) "
            "non è applicabile."
        ),
    )

    # Esegue la catena fino a DEFINITIVA: da EMESSA è esattamente lo step
    # DEFINITIVA (numera + accoda stampa), poi si ferma (DEFINITIVA chiude il lotto).
    return run_lotto_pipeline_until_done(
        lotto_id=lotto_id, fino_a_stato="DEFINITIVA",
    )


# Scopo: C-8 — Ristampa MASSIVA di un lotto DEFINITIVA: accoda in
#        `vendite.fatture_stampa_coda` una riga per ogni fattura non esclusa del
#        lotto (`fn_accoda_stampe_lotto`, idempotente sui work-item vivi); il
#        worker `draina_coda_stampa` le renderizza (async — lo stato si vede nel
#        pannello esiti C-5). Stampa = lettura (I-4): NESSUNA numerazione qui. Il
#        gate DEFINITIVA (via _get_lotto_in_stato) garantisce fatture già
#        numerate → il backstop del worker (C-2d) non ha nulla da numerare: la
#        ristampa non è mai un atto fiscale mascherato (I-7). Scope operatore:
#        lotto fuori scope/inesistente → 404.
def ristampa_lotto(
    *, lotto_id: int, auth_user_id: int | None = None,
) -> dict[str, object]:
    _get_lotto_in_stato(
        lotto_id=lotto_id,
        auth_user_id=auth_user_id,
        stato_codice="DEFINITIVA",
        error_code="E_LOTTO_NON_RISTAMPABILE",
        error_message=(
            "Il lotto non è definitivo: la ristampa massiva è disponibile solo "
            "su lotti con fatture numerate (Rendi definitive)."
        ),
    )

    accodate = VenditePipelineRepository().accoda_stampe_lotto(lotto_id)
    return {"lotto_id": lotto_id, "accodate": accodate}


# Prefissi jobname delle corsie di fatturazione in maintenance.job_run_log:
# il batch registra `run_fatturazione_batch:<corsia>`, i worker
# `draina_coda_stampa` / (futuro) `draina_coda_lavori`. Owner unico del
# vocabolario jobname lato lettura esiti.
_JOBNAME_PREFISSI_FATTURAZIONE = (
    "run_fatturazione_batch",
    "draina_coda_stampa",
    "draina_coda_lavori",
)


# Scopo: C-5 — Esiti dei giri di fatturazione + stato della coda stampa, per il
#        cockpit. Aggrega due sorgenti di sola lettura, nessuna tabella nuova
#        (I-5): (a) `maintenance.job_run_log` riassunto per corsia (ultimo esito,
#        ultimo run, ok/fail) filtrato ai jobname di fatturazione; (b) i conteggi
#        della coda stampa per stato, **con scope emittente dell'operatore** (la
#        coda non ha emittente → JOIN fatture nel repo, brief §5). `auth_user_id`
#        None solo per usi di sistema; dal cockpit è sempre l'operatore.
def esiti_fatturazione(*, auth_user_id: int | None = None) -> dict[str, object]:
    from apps.core.db.maintenance_repository import MaintenanceRepository

    # limit=200 sui JOBNAME DISTINTI (il summary e' un GROUP BY jobname):
    # i job registrati sono decine, il cap e' largo per costruzione. Se mai
    # venisse superato, i giri fatturazione potrebbero uscire dalla finestra
    # (ordinata per last_run_at): rivedere con un filtro SQL sul repo core.
    summary, _ = MaintenanceRepository().list_job_summary(limit=200)
    giri = []
    for s in summary:
        if not str(s.get("jobname", "")).startswith(_JOBNAME_PREFISSI_FATTURAZIONE):
            continue
        # `last_run_at` arriva come testo PG ("YYYY-MM-DD HH:MM:SS...+TZ",
        # spazio non 'T'): normalizzato a ISO-8601 per il parse Date()
        # cross-browser del FE (displayTimestamp).
        last_run = s.get("last_run_at")
        giri.append({
            **s,
            "last_run_at": last_run.replace(" ", "T", 1) if last_run else None,
        })
    coda_stampa = VenditePipelineRepository().count_coda_stampa_per_stato(
        auth_user_id=auth_user_id,
    )
    return {"giri": giri, "coda_stampa": coda_stampa}


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

