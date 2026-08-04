# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo pipeline vendite.
# ------------------------------------------------------------


import re
from dataclasses import replace
from datetime import date
from typing import Any

from apps.core.db.dbops_repository import DbopsRepository
from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import SdiPayloadRow, VenditePipelineRepository
from apps.vendite.services._fatturazione_job_helpers import JOB_TYPES_FATTURAZIONE_APP
from apps.vendite.services.lotto_segnalazioni_service import LottoSegnalazioniService
from apps.vendite.services.pipeline_runner import LottoPipelineParams, LottoPipelineRunner
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor
from apps.vendite.services.fatture_righe_service import FattureRigheService
from apps.vendite.services.lotto_reset_service import LottoResetService
from apps.vendite.types import (
    AnnullaLottoDaDraftResult,
    EliminaFatturaDaLottoResult,
    GroupAttivitaKey,
    LottoPipelineMeta,
    LottoTaskRunRow,
    RiportaLottoADraftResult,
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
    gruppi: tuple[str, ...] | None = None,
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
        gruppi=gruppi,
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
    gruppi: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Entrypoint servizio Python per eseguire la catena lotto fino a conclusione.

    `fino_a_stato` (C-1, gate fiscale D-1): codice_interno di
    config.stati_doc_fiscale (es. 'EMESSA') a cui la catena si FERMA con
    motivo_stop=FERMATO_A_STATO. None = fino in fondo (storico).

    `gruppi` (emissione mirata, D-3): chiavi dei gruppi fatturabili da lavorare.
    Vengono PERSISTITE sul lotto alla creazione, non passate agli step: da li'
    in poi il perimetro vive nel `LottoContext` e sopravvive ai rerun. None =
    nessuna restrizione (giro di massa, comportamento storico)."""
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
        gruppi=gruppi,
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
#        `vendite.fatture_stampa_coda` una riga per ogni fattura del
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


# Prefisso jobname delle CORSIE DI FATTURAZIONE in maintenance.job_run_log:
# il batch registra `run_fatturazione_batch:<corsia>` (immediata/differita).
#
# I worker di drenaggio code (`draina_coda_lavori`/`draina_coda_stampa`) NON
# sono qui di proposito (2026-07-23, richiesta Tid): sono poller che si
# svegliano ogni 1-2 minuti, quindi il loro contatore di run cresce di ~1440
# al giorno e non dice nulla sulla fatturazione — affiancato alle corsie vere
# rendeva indistinguibile «worker vivo» da «batch fermo da un mese». La
# liveness delle code resta esposta dove è pertinente, accanto alle code
# stesse: `coda_lavori.gestione_service.conteggi_code` -> `worker.*`
# (last_run_at + attivo), reso nei tab della vista Code di lavoro.
_JOBNAME_PREFISSO_FATTURAZIONE = "run_fatturazione_batch"


# Scopo: normalizza il timestamp testuale di PG ("YYYY-MM-DD HH:MM:SS...+TZ",
#        spazio non 'T') a ISO-8601, per il parse Date() cross-browser del FE
#        (displayTimestamp). Entrambe le sorgenti dei giri lo restituiscono
#        come testo, quindi la conversione è una sola.
#        L'offset PG senza minuti ("+02") viene completato a "+02:00": lo
#        standard ECMA per Date() richiede ±HH:MM — V8 è permissivo, Safari
#        no (Invalid Date → cella vuota). Gli offset con minuti ("+05:30")
#        arrivano già completi e non vengono toccati.
_OFFSET_SENZA_MINUTI = re.compile(r"([+-]\d{2})$")


def _iso(raw: str | None) -> str | None:
    if not raw:
        return None
    return _OFFSET_SENZA_MINUTI.sub(r"\1:00", raw.replace(" ", "T", 1))


# Job type dei lavori di fatturazione accodati dall'APP (C-3 giro, C-4 numera):
# l'altra strada con cui si fattura, quella usata quotidianamente dagli
# operatori. Vive in `dbops.coda_lavori`, non in `maintenance.job_run_log`.
# Le costanti sono in `_fatturazione_job_helpers` (condivise con l'enqueue
# delle view — regola del 2, ok Tid 2026-07-23), importate in testa al modulo.

# Etichette di ORIGINE dei giri: dicono da DOVE è partito il lavoro, non cosa ha
# fatto. Servono al FE per non confondere le due strade in un unico mucchio.
ORIGINE_APP = "app"
ORIGINE_BATCH = "batch"


# Scopo: C-5 — Esiti dei giri di fatturazione + stato della coda stampa, per il
#        cockpit. Aggrega sorgenti di sola lettura, nessuna tabella nuova (I-5).
#
# I giri arrivano dalle DUE strade con cui si può fatturare, unite in un'unica
# lista e distinguibili per `origine` (2026-07-23):
#   - `app`   → `dbops.coda_lavori` (FATTURAZIONE_GIRO/NUMERA): i lavori
#               lanciati dagli operatori dai pulsanti del cockpit;
#   - `batch` → `maintenance.job_run_log` (`run_fatturazione_batch:<corsia>`):
#               il batch da riga di comando, per quando verrà schedulato.
# Mostrarne UNA sola è il difetto che ha reso il pannello fuorviante: leggeva
# solo `batch` e dichiarava «nessun giro» mentre gli operatori fatturavano ogni
# giorno dall'app. Tenerle entrambe significa che attivare (o spegnere) lo
# scheduler non fa sparire nulla dal pannello.
#
# CONTEGGI COMPLESSIVI, non per-operatore (decisione Tid 2026-07-23): chi è
# autorizzato all'attività vede il totale dei giri del mese — un totale
# ristretto ai propri sarebbe un'informazione sbagliata (il pannello di `pochi`
# dichiarava «nessun giro» mentre l'admin fatturava per tutti). Il totale delle
# righe `app` è pero' SPEZZATO in `mio_count`/`altri_count` (identità is_mio
# della vista code): l'operatore distingue il proprio lavoro da quello altrui
# senza perdere il quadro. Le righe `batch` non hanno split: sono di sistema,
# non di un operatore.
#
# `competenza_mese` restringe i giri a quel mese. L'attribuzione differisce per
# sorgente, ed è volutamente la più precisa disponibile per ciascuna:
#   - app   → `payload->>'competenza_mese'`, DICHIARATO all'accodamento;
#   - batch → competenza dal meta del run se c'è, altrimenti mese di esecuzione
#             (i run storici non la scrivevano: vedi `list_job_summary`).
# Anche `coda_stampa` segue il mese (via il lotto della riga di coda): senza, i
# suoi contatori sono cumulativi da sempre — «Fatte: 7» cresce all'infinito e
# non dice nulla sul mese che si sta fatturando. L'intero pannello parla quindi
# di UN periodo solo, quello filtrato nella lista sottostante.
#
# `user` serve allo split miei/altri dei giri app; `auth_user_id` allo scope
# della coda stampa. None = uso di sistema (split a 0, coda senza scope).
def esiti_fatturazione(
    *,
    auth_user_id: int | None = None,
    competenza_mese: date | None = None,
    user: Any = None,
) -> dict[str, object]:
    from apps.core.db.maintenance_repository import MaintenanceRepository
    from apps.core.services.coda_lavori.gestione_service import (
        scope_key_operatore,
    )
    from apps.core.services.coda_lavori.repository import CodaLavoriRepository

    # (a) Giri lanciati dall'APP: totale complessivo + split miei/altri.
    caller_scope_key = None if user is None else scope_key_operatore(user)
    giri = [
        {
            **r,
            "origine": ORIGINE_APP,
            "altri_count": int(r["total_runs"]) - int(r["mio_count"]),
            "last_run_at": _iso(r.get("last_run_at")),
        }
        for r in CodaLavoriRepository().summary_per_job_type(
            job_types=list(JOB_TYPES_FATTURAZIONE_APP),
            competenza_mese=competenza_mese,
            caller_scope_key=caller_scope_key,
        )
    ]

    # (b) Giri del BATCH schedulato. limit=200 sui JOBNAME DISTINTI (il summary
    # e' un GROUP BY jobname) gia' ristretti al prefisso di fatturazione: le
    # corsie sono 2, il cap e' largo per costruzione.
    summary, _ = MaintenanceRepository().list_job_summary(
        limit=200,
        jobname_prefix=_JOBNAME_PREFISSO_FATTURAZIONE,
        meta_month_equals=(
            ("competenza", competenza_mese.replace(day=1).isoformat())
            if competenza_mese is not None
            else None
        ),
    )
    giri.extend(
        {**s, "origine": ORIGINE_BATCH, "last_run_at": _iso(s.get("last_run_at"))}
        for s in summary
    )
    coda_stampa = VenditePipelineRepository().count_coda_stampa_per_stato(
        auth_user_id=auth_user_id,
        competenza_mese=competenza_mese,
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


# Scopo: Facade applicativa: ANNULLA il lotto che si trova in DRAFT (stato ad
#        ANNULLATA/CHIUSO, fatture pre-fiscali eliminate, attivita' liberate).
def fn_annulla_lotto_da_draft(*, lotto_id: int) -> AnnullaLottoDaDraftResult:
    """Entrypoint servizio Python con lo stesso intento della funzione SQL fn_annulla_lotto_da_draft."""
    service = LottoResetService()
    return service.annulla_lotto_da_draft(lotto_id)


# Scopo: Facade applicativa: RIPORTA A BOZZA il lotto (Fase 6) perche' si possa
#        correggere a monte e rifare il giro. Cancella le fatture e riporta le
#        `commesse_attivita` a NON_EMESSA; il rilancio le rigenera.
def fn_riporta_lotto_a_draft(*, lotto_id: int) -> RiportaLottoADraftResult:
    """Entrypoint servizio Python con lo stesso intento della funzione SQL fn_riporta_lotto_a_draft."""
    service = LottoResetService()
    return service.riporta_lotto_a_draft(lotto_id)


# Scopo: Facade applicativa: elimina UNA fattura dal lotto, liberandone le
#        attivita'. Perimetro lotto E fattura PRE-FISCALI (DRAFT o EMESSA);
#        togliere la fattura significa CANCELLARLA, non archiviarla (RD-7).
def fn_elimina_fattura_da_lotto(
    *,
    lotto_id: int,
    fattura_id: int,
) -> EliminaFatturaDaLottoResult:
    """Entrypoint servizio Python con lo stesso intento della funzione SQL fn_elimina_fattura_da_lotto."""
    service = LottoResetService()
    return service.elimina_fattura_da_lotto(lotto_id, fattura_id)


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

