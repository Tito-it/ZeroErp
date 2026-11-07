# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo pipeline vendite.
# ------------------------------------------------------------


import re
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any

from apps.core.api.payload_validators import envelope_da_offset
from apps.core.api.constants import DEFAULT_LIMIT, DEFAULT_LIMIT_EVENTI, MAX_LIMIT
from apps.core.db._helpers import order_dir_ammessa
from apps.core.db.dbops_repository import DbopsRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.fan_out import FanOutRunLogger, run_fan_out
from apps.core.services.service_errors import E_VALIDATION_INPUT
from apps.vendite.db.pipeline_repository import (
    SdiPayloadRow,
    VenditePipelineRepository,
)
# Solo la costante: il modulo e' gia' caricato da `pipeline_repository`
# (via `commesse_repository`), il repository resta importato al bisogno.
from apps.vendite.db.vendite_repository import STATO_DEFINITIVA
from apps.vendite.services._fatturazione_job_helpers import JOB_TYPES_FATTURAZIONE_APP
from apps.vendite.services._lotto_perimetro import lotto_visibile
from apps.vendite.services.lotto_segnalazioni_service import LottoSegnalazioniService
from apps.vendite.services.pipeline_runner import LottoPipelineParams, LottoPipelineRunner
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor
from apps.vendite.services.fatture_righe_service import FattureRigheService
from apps.vendite.services.lotto_reset_service import (
    CODICE_RIPIEGO_USCITA,
    LottoResetService,
)
from apps.vendite.types import (
    AnnullaLottoDaDraftResult,
    EliminaFatturaDaLottoResult,
    EsclusioneDocumentoDaGiroResult,
    EsitoDataDocumento,
    GroupAttivitaKey,
    LottoListRow,
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
    data_documento: date | None = None,
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
        data_documento=data_documento,
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
    data_documento: date | None = None,
) -> dict[str, Any]:
    """Entrypoint servizio Python per eseguire la catena lotto fino a conclusione.

    `fino_a_stato` (C-1, gate fiscale D-1): codice_interno di
    config.stati_doc_fiscale (es. 'EMESSA') a cui la catena si FERMA con
    motivo_stop=FERMATO_A_STATO. None = fino in fondo (storico).

    `gruppi` (emissione mirata, D-3): chiavi dei gruppi fatturabili da lavorare.
    Vengono PERSISTITE sul lotto alla creazione, non passate agli step: da li'
    in poi il perimetro vive nel `LottoContext` e sopravvive ai rerun. None =
    nessuna restrizione (giro di massa, comportamento storico).

    `data_documento` (BE-1, brief numerazione): la data dichiarata per i
    documenti del lotto. Scritta sul lotto alla creazione, come i gruppi. None =
    NON dichiarata, e la decide la politica del registro — non e' un sinonimo
    di «oggi»."""
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
        data_documento=data_documento,
    )
    if fino_a_stato_id is not None:
        params = replace(params, fino_a_stato_doc_fiscale_id=fino_a_stato_id)
    return runner.run_lotto_until_done(params)




# Scopo: BE-5 — LA FINESTRA DI NUMERAZIONE di un perimetro: con quale data si
#        puo' numerare, e da quale data i documenti partono ADESSO.
#        Risponde a due perimetri con una funzione sola, perche' e' la stessa
#        domanda su due insiemi: un LOTTO (dialog «Rendi definitive» del
#        drawer) oppure un MESE DI COMPETENZA (atto di perimetro, che tocca N
#        lotti e vuole la data che li accontenta tutti).
#
#        Ritorna quattro cose, tutte ISO o `None`:
#          `data_minima`   il PAVIMENTO — prima di quella data il DB rifiuta;
#                          `None` = nessun numero ancora emesso su quei
#                          sezionali, quindi nessun limite;
#          `data_corrente` la data che i documenti da numerare portano OGGI;
#                          `None` = non c'e' niente da numerare;
#          `data_documento` la DICHIARAZIONE sul lotto (spesso assente: vince
#                          la politica del registro). Solo sul perimetro lotto;
#          piu' l'eco del perimetro chiesto.
#
# ⭐ PERCHE' ESISTE, e non e' un abbellimento. Con la politica
#    `FINE_MESE_COMPETENZA` sul Back-office, ogni lotto di competenza ARRETRATA
#    nasce con una data anteriore all'ultimo numero emesso: senza questa
#    lettura il dialog proporrebbe ogni volta una data che il DB rifiuta, e
#    l'operatore imparerebbe a leggere l'errore invece della targa.
#
# ⚠️ E' una TARGA, non un lucchetto. La funzione DB e' SECURITY INVOKER su
#    `vendite.fatture`, che ha la RLS: sotto un perimetro ristretto il minimo
#    esce PIU' BASSO del vero. Il rifiuto vero resta del cancello in
#    `fn_get_next_progressivo`, che legge il contatore — tabella senza RLS.
#    Chi usasse questa risposta AL POSTO del cancello starebbe sostituendo un
#    presidio con un suggerimento.
# Scopo: il repository vendite, importato al bisogno.
# ⚠️ Import LOCALE come gia' fa `lotto_visibile` (`_lotto_perimetro`): la
#    catena `vendite_repository` non va caricata al boot di `pipeline_service`.
def _vendite_repo():
    from apps.vendite.db.vendite_repository import VenditeRepository
    return VenditeRepository()


def finestra_numerazione(
    *,
    lotto_id: int | None = None,
    competenza_mese: date | None = None,
    lotti_ids: list[int] | None = None,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    # Esattamente uno dei tre: senza perimetro la domanda non ha risposta, con
    # piu' di uno ne avrebbe due e non si saprebbe quale si e' ottenuta.
    # ⭐ Il terzo — `lotti_ids` — e' la SELEZIONE della lista lotti, e su di
    #    esso il pavimento e' quello che conta di piu': spuntando lotti di
    #    sezionali diversi il limite e' del piu' restrittivo, e cambia mentre si
    #    spunta. Per questo la finestra si ricalcola sulla selezione e non una
    #    volta all'apertura del dialog.
    scelti = [p for p in (lotto_id, competenza_mese, lotti_ids) if p is not None]
    ErrorManager.require(
        len(scelti) == 1,
        code=E_VALIDATION_INPUT,
        message=(
            "Indicare `lotto_id`, `competenza_mese` oppure `lotti`, "
            "esattamente uno."
        ),
        detail=(
            f"lotto_id={lotto_id} competenza_mese={competenza_mese} "
            f"lotti_ids={lotti_ids}"
        ),
    )
    repo = VenditePipelineRepository()

    # Scopo: la risposta, in UNA forma sola per i due perimetri — cosi' una
    #        chiave nuova si aggiunge in un posto e non in due.
    def _risposta(*, minima, corrente, data_documento=None, n_lotti=None) -> dict[str, Any]:
        return {
            "lotto_id": lotto_id,
            "competenza_mese": competenza_mese.isoformat() if competenza_mese else None,
            # ⚠️ Quanti lotti l'atto TOCCHEREBBE davvero — non quanti ne ha
            #    chiesti il chiamante. Sono due numeri diversi: una selezione
            #    puo' contenere lotti non piu' numerabili (li ha presi un altro
            #    giro, un collega li ha resi definitivi), e dire «l'atto numera
            #    5 lotti» quando ne tocchera' 3 e' una frase falsa nel punto in
            #    cui l'operatore sta per confermare un atto fiscale.
            # ⛔ E lo dice il SERVER, per entrambi i perimetri. Sul mese il
            #    chiamante quel numero non ce l'ha proprio — la lista e'
            #    paginata e filtrata su un altro asse — e infatti la prima
            #    versione gli passava `0`: il dialog annunciava «l'atto numera
            #    0 lotti» mentre stava per numerarne tutti quelli del mese.
            "n_lotti": n_lotti,
            "data_documento": data_documento,
            "data_corrente": corrente.isoformat() if corrente else None,
            "data_minima": minima.isoformat() if minima else None,
        }

    if lotto_id is not None:
        lotto = lotto_visibile(lotto_id=lotto_id, auth_user_id=auth_user_id)
        return _risposta(
            minima=repo.get_data_minima_numerabile_lotto(lotto_id),
            corrente=repo.get_data_documento_corrente(lotto_id=lotto_id),
            data_documento=lotto.get("data_documento"),
        )

    # Perimetro di ATTO — un mese intero oppure una selezione di lotti. In
    # entrambi i casi sono i lotti EMESSA: gli stessi che `list_lotti_numerabili`
    # restituisce. Config rotta -> fail-loud, non zero lotti silenziosi (stessa
    # disciplina dell'handler di coda).
    emessa_id = repo.get_stato_doc_fiscale_id("EMESSA")
    ErrorManager.require(
        emessa_id is not None,
        code="E_PIPELINE_VALIDATION",
        message="Stato EMESSA non configurato in config.stati_doc_fiscale.",
    )
    assert emessa_id is not None
    perimetro: dict[str, Any] = {"competenza_mese": competenza_mese, "lotti_ids": lotti_ids}
    return _risposta(
        minima=repo.get_data_minima_numerabile_perimetro(
            stato_doc_fiscale_id=emessa_id, **perimetro,
        ),
        corrente=repo.get_data_documento_corrente(
            stato_doc_fiscale_id=emessa_id, **perimetro,
        ),
        # ⚠️ La STESSA discovery che l'atto percorrera': cosi' il numero
        #    annunciato e quello dei lotti toccati non possono divergere. Costa
        #    una query in piu' all'apertura del dialog, e la si paga.
        n_lotti=len(_vendite_repo().list_lotti_numerabili(
            stato_doc_fiscale_id=emessa_id, **perimetro,
        )),
    )


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
) -> LottoListRow:
    lotto = lotto_visibile(lotto_id=lotto_id, auth_user_id=auth_user_id)

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
    *,
    lotto_id: int,
    auth_user_id: int | None = None,
    data_documento: date | None = None,
) -> dict[str, Any]:
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

    # ⭐ LA DATA SI DICHIARA PRIMA DI NUMERARE (BE-2, brief numerazione §4
    #    DB-11), e l'ordine e' un requisito, non una comodita': la funzione
    #    madre riscrive `fatture.data` e RIGENERA i piani rate, e le rate devono
    #    quadrare quando il guard D-K le guarda — cioe' dentro la numerazione.
    #    Farlo dopo vorrebbe dire cambiare la data di un documento gia' numerato,
    #    che il trigger `trg_fatture_a10_guard_data_numerata_upd` rifiuta.
    # ⚠️ Se la data e' sotto il pavimento del sezionale, la funzione madre
    #    solleva SUBITO — con lo stesso codice del cancello — invece di lasciare
    #    che il giro si fermi a meta' lotto.
    # ⚠️ `None` = nessuna dichiarazione: non si tocca niente e valgono le date
    #    che i documenti gia' portano. Non e' «usa oggi».
    # ⛔ I DUE ATTI NON SONO NELLA STESSA TRANSAZIONE, e va saputo: se la
    #    numerazione poi fallisce (guard D-K, padre di una nota ancora senza
    #    numero), la data e le rate rigenerate RESTANO. Non e' un difetto da
    #    correggere avvolgendo tutto in un `atomic`: il runner tiene apposta il
    #    lavoro parziale degli step gia' fatti, e un rollback esterno lo
    #    butterebbe via. E' invece il motivo per cui l'esito porta
    #    `aggiornate`/`rate_rigenerate` ANCHE quando il giro si ferma — chi
    #    legge deve poter sapere che la data si e' mossa lo stesso.
    esito_data: EsitoDataDocumento | None = None
    if data_documento is not None:
        esito_data = VenditePipelineRepository().imposta_data_documento_lotto(
            lotto_id=lotto_id, data_documento=data_documento,
        )

    # Esegue la catena fino a DEFINITIVA: da EMESSA è esattamente lo step
    # DEFINITIVA (numera + accoda stampa), poi si ferma (DEFINITIVA chiude il lotto).
    esito = run_lotto_pipeline_until_done(
        lotto_id=lotto_id, fino_a_stato=STATO_DEFINITIVA,
    )
    # ⚠️ L'esito della dichiarazione viaggia con quello della numerazione, e non
    #    e' decorazione: `saltate_numerate` e `rate_rigenerate` sono le due
    #    conseguenze che l'operatore non si aspetta — un lotto numerato a meta'
    #    e delle scadenze che si sono spostate. Chi non le mostra le nasconde.
    # `esito_data` c'e' solo se c'e' `data_documento` (sopra): le due condizioni
    # sono la stessa, scritte entrambe per il type checker.
    if esito_data is not None and data_documento is not None:
        esito = {**esito, "data_documento": data_documento.isoformat(), **esito_data}
    return esito


# Scopo: L'ELENCO paginato delle segnalazioni di un lotto (BE-4 del brief liste
#        drawer lotto). Sorgente: `vendite.fn_list_lotto_segnalazioni`.
#
# ⭐ SEPARATO DA `fn_get_lotto_segnalazioni_summary`, e non e' una duplicazione:
#    quello CONTA e alimenta il banner di testata — una risposta piccola che il
#    drawer chiede sempre; questo ELENCA, e' paginato e ordinabile, e serve alla
#    scheda. Farne uno solo avrebbe voluto dire portarsi dietro l'elenco a ogni
#    apertura del drawer per mostrarne un numero.
#
# ⚠️ `livello` e `origine` sono filtri OPZIONALI: assenti = tutto. Il vocabolario
#    lo valida la funzione DB, qui si controlla solo cio' che il DB non puo'
#    dire con un messaggio utile (paginazione e direzione).
def fn_list_lotto_segnalazioni(
    *,
    lotto_id: int,
    auth_user_id: int | None,
    livello: str | None = None,
    origine: str | None = None,
    solo_attive: bool = True,
    solo_job_corrente: bool = False,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str = "desc",
    max_rows: int | None = None,
) -> dict[str, Any]:
    ErrorManager.require(
        bool(lotto_id and lotto_id > 0),
        code="E_PIPELINE_VALIDATION",
        message="Parametri pipeline non validi.",
        detail="lotto_id obbligatorio e > 0",
        context={"lotto_id": lotto_id},
        function_name="vendite.pipeline_service.fn_list_lotto_segnalazioni",
        log_to_db=False,
    )
    # ⛔ La finestra (`limit` fra 1 e il tetto, `offset` non negativo) la
    #    valida la view con `pagina_da_query`, che dal 2026-10-21 risponde 400
    #    sul fuori limite (Tid): qui era una seconda copia, irraggiungibile.
    # ⛔ Il predicato unico `order_dir_ammessa` (2026-09-26), non un secondo
    #    `in ("asc", "desc")`: la fn DB legge `lower(btrim(...))`, quindi
    #    maiuscole, spazi e assenza (= il suo default `desc`) sono gia' suoi.
    ErrorManager.require(
        order_dir_ammessa(order_dir),
        code="E_PIPELINE_VALIDATION",
        message="Parametri pipeline non validi.",
        detail=f"order_dir={order_dir!r} non ammesso",
        context={"lotto_id": lotto_id, "order_dir": order_dir},
        function_name="vendite.pipeline_service.fn_list_lotto_segnalazioni",
        log_to_db=False,
    )
    # ⛔ Il cancello di perimetro PRIMA dell'elenco (vedi `_lotto_perimetro`).
    lotto_visibile(
        lotto_id=lotto_id, auth_user_id=auth_user_id,
        function_name="vendite.pipeline_service.fn_list_lotto_segnalazioni",
    )
    righe, total_count, fuori_job = VenditePipelineRepository().list_lotto_segnalazioni(
        lotto_id=lotto_id,
        livello=livello,
        origine=origine,
        solo_attive=solo_attive,
        solo_job_corrente=solo_job_corrente,
        limit=limit,
        offset=0 if max_rows else offset,
        order_by=order_by,
        order_dir=order_dir,
        max_rows=max_rows,
    )
    return {
        "lotto_id": lotto_id,
        **envelope_da_offset(righe, total_count, limit=limit, offset=offset),
        # ⭐ Quante segnalazioni restano FUORI dal job corrente: e' il numero che
        # rende onesto il filtro «solo l'ultima corsa». Senza, un elenco filtrato
        # e uno vuoto si leggono uguali.
        "fuori_job_count": fuori_job,
        "results": righe,
    }


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
) -> dict[str, Any]:
    _get_lotto_in_stato(
        lotto_id=lotto_id,
        auth_user_id=auth_user_id,
        stato_codice=STATO_DEFINITIVA,
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
) -> dict[str, Any]:
    from apps.core.db.maintenance_repository import MaintenanceRepository
    from apps.core.services.coda_lavori.gestione_service import (
        perimetro_coda_operatore,
    )
    from apps.core.services.coda_lavori.repository import CodaLavoriRepository

    # (a) Giri lanciati dall'APP: totale complessivo + split miei/altri. «Miei»
    #     = delle aziende del mio perimetro; senza utente nessuno è mio (`[]`:
    #     None vorrebbe dire «tutte le aziende», l'admin globale).
    caller_emittenti = [] if user is None else perimetro_coda_operatore(user)
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
            caller_emittenti=caller_emittenti,
        )
    ]

    # (b) Giri del BATCH schedulato. Una pagina piena (`MAX_LIMIT`) di JOBNAME DISTINTI (il summary
    # e' un GROUP BY jobname) gia' ristretti al prefisso di fatturazione: le
    # corsie sono 2, il cap e' largo per costruzione.
    summary, _ = MaintenanceRepository().list_job_summary(
        limit=MAX_LIMIT,
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
    #
    # ⚠️ NESSUN `correlation_id`, ed e' deliberato (D-7). Qui si esegue UNO step
    #    fuori da un giro: non c'e' nessun altro registro — eventi, altri
    #    tentativi, riga di push — che condividerebbe il filo, quindi un uuid
    #    coniato qui non cucirebbe niente e sembrerebbe soltanto un filo.
    #    E' la stessa scelta che il DB ha fatto su `fn_start_commessa_push_run`:
    #    *un buco dichiarato si conta, un filo che non lega sembra un filo*.
    #    Il giorno in cui questa facade diventasse essa stessa un giro (piu'
    #    step, o eventi propri), il filo si genera QUI e non nello step executor.
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


# Scopo: Entrypoint servizio per l'uscita di UN documento dal giro (brief
#        `brief-db-uscita-documento-dal-giro`). Stesso intento della funzione
#        SQL omonima, e stessa forma degli altri verbi del lotto.
# ⚠️ Non e' l'entrypoint dell'API: quello e' `fn_escludi_documenti_da_giro`, che
#    tratta la riga singola come una lista di uno. Questa resta la primitiva su
#    cui il giro di massa itera.
def fn_escludi_documento_da_giro(
    *,
    lotto_id: int,
    gruppo_key: str,
    motivo: str,
) -> EsclusioneDocumentoDaGiroResult:
    """Entrypoint servizio Python con lo stesso intento della funzione SQL fn_escludi_documento_da_giro."""
    service = LottoResetService()
    return service.escludi_documento_da_giro(lotto_id, gruppo_key, motivo)


# Scopo: diario del fan-out delle uscite — l'unica parte di DOMINIO del giro.
#        Serve a tenere il CODICE di ogni documento rifiutato: `FanOutEsito`
#        porta il messaggio normalizzato, non il codice, e il codice e' cio' su
#        cui il frontend instrada — «gia' uscito» si legge diverso da «non e' in
#        errore». Il BB sa QUANDO chiamare, questo sa COSA tenere.
@dataclass
class _EsclusioneRunLogger(FanOutRunLogger):
    esiti: dict[str, tuple[str, str]] = field(default_factory=dict)

    # Scopo: Registra codice e messaggio del documento che non e' uscito.
    def item_failed(self, *, item: Any, indice: int, exc: Exception) -> None:
        codice = getattr(exc, "code", None) or CODICE_RIPIEGO_USCITA
        messaggio = getattr(exc, "message", None) or str(exc)
        self.esiti[str(item)] = (codice, messaggio)


# Scopo: toglie N documenti dal giro in una corsa sola.
#
# ⭐ UN ENDPOINT SOLO, e la riga singola e' una lista di uno — la lezione e'
#    scritta sul gemello degli accrediti: due superfici per lo stesso verbo
#    divergerebbero su permessi, conferme e forma dell'esito.
#
# ⭐ La risposta e' un REPORT e torna sempre 200, anche quando tutti i documenti
#    sono rifiutati. Il verbo non produce un atto fiscale: lascia documenti che
#    tornano in competenza. E sollevare sul «tutti falliti» darebbe al chiamante
#    DUE forme da leggere per la stessa domanda — un elenco di esiti oppure un
#    errore — che e' lo stesso argomento per cui l'endpoint e' uno.
#
# ⚠️ `run_fan_out` e non un ciclo scritto a mano: savepoint per elemento (un
#    documento rifiutato non si porta via le uscite gia' riuscite), stack
#    loggato una volta per tutte, esito a tre stati.
# ⚠️ Il MOTIVO e' uno per il giro, non uno per riga: chi toglie cinque documenti
#    li toglie per la stessa ragione, e chiederne cinque renderebbe il gesto di
#    massa piu' lento della somma dei singoli. La D-5 resta soddisfatta — ogni
#    riga il suo motivo ce l'ha, scritto dall'operatore.
def fn_escludi_documenti_da_giro(
    *,
    lotto_id: int,
    gruppo_keys: Any,
    motivo: Any,
) -> dict[str, Any]:
    chiavi = _parse_gruppo_keys(gruppo_keys)
    motivo_testo = _testo_del_motivo(motivo)
    diario = _EsclusioneRunLogger()
    esito = run_fan_out(
        chiavi,
        lambda chiave: fn_escludi_documento_da_giro(
            lotto_id=lotto_id, gruppo_key=chiave, motivo=motivo_testo,
        ),
        run_logger=diario,
    )
    # ⚠️ UN SOLO lookup con UN default, e la coppia si sfascia in due nomi: due
    #    `.get` separati con default diversi sullo stesso item potrebbero
    #    raccontare due storie — codice di ripiego e messaggio vero, o viceversa
    #    — proprio nel caso in cui il diario non ha visto l'errore, cioe'
    #    quando serve capirlo.
    # ⚠️ E il default e' RAGGIUNGIBILE: `run_fan_out` inghiotte di proposito i
    #    fallimenti del proprio logger, quindi `esiti` puo' non avere la chiave.
    falliti = []
    for errore in esito.errori:
        chiave = str(errore.item)
        codice, messaggio = diario.esiti.get(
            chiave, (CODICE_RIPIEGO_USCITA, errore.messaggio),
        )
        falliti.append(
            {"gruppo_key": chiave, "codice": codice, "messaggio": messaggio},
        )
    return {
        "esito": esito.esito,
        "totale": esito.totale,
        "ok": esito.ok,
        "usciti": list(esito.risultati),
        "falliti": falliti,
    }


# Scopo: il motivo come TESTO — un guard di TIPO, non di contenuto.
#
# ⛔ NON VALIDA LA REGOLA: «il motivo e' obbligatorio» e' la D-5, la tiene il
#    `CHECK` di tabella e la madre solleva anche sui soli spazi. Riscriverla qui
#    sarebbe la seconda sede di una regola che il database gia' possiede — e
#    quella dell'applicazione e' la copia che invecchia.
#
# ⚠️ `None` NON e' un errore di tipo: e' l'ASSENZA, e diventa stringa vuota
#    perche' il rifiuto lo dica il database con la sua frase a catalogo.
# 🔴 Ma qualunque ALTRO tipo si RIFIUTA, ed e' il difetto che questo guard
#    chiude: prima il confine faceva `str(payload.get("motivo") or "")`, e su un
#    body storto — un numero, una lista, un oggetto — `str()` non fallisce, ne
#    INVENTA uno. Un «[1, 2]» finiva scritto come motivo dell'uscita e ci
#    restava per sempre, dove D-5 vuole una frase che fra un mese qualcuno possa
#    leggere.
def _testo_del_motivo(raw: Any) -> str:
    if raw is None:
        return ""
    ErrorManager.require(
        isinstance(raw, str),
        code="E_PIPELINE_VALIDATION",
        message="`motivo` deve essere testo.",
        detail=f"tipo ricevuto: {type(raw).__name__}",
        function_name="vendite.pipeline_service._testo_del_motivo",
        log_to_db=False,
    )
    assert isinstance(raw, str)
    return raw


# Scopo: normalizza e valida le chiavi da togliere dal giro.
# ⚠️ Lista VUOTA rifiutata e non trattata come «tutti»: indovinare male qui
#    vorrebbe dire svuotare un giro intero con una richiesta che non lo chiedeva.
# ⚠️ Deduplica PRESERVANDO L'ORDINE: la stessa chiave due volte nello stesso
#    body produrrebbe un `E_LOTTO_DOC_GIA_USCITO` autoinflitto, che a video
#    sembra un difetto del sistema mentre e' il body.
def _parse_gruppo_keys(raw: Any) -> tuple[str, ...]:
    fn = "vendite.pipeline_service._parse_gruppo_keys"
    ErrorManager.require(
        isinstance(raw, (list, tuple)) and len(raw) > 0,
        code="E_PIPELINE_VALIDATION",
        message="`gruppo_keys` deve essere una lista non vuota di documenti.",
        detail=f"tipo ricevuto: {type(raw).__name__}",
        function_name=fn,
        log_to_db=False,
    )
    chiavi: list[str] = []
    for elemento in raw:
        valido = isinstance(elemento, str) and bool(elemento.strip())
        ErrorManager.require(
            valido,
            code="E_PIPELINE_VALIDATION",
            message="`gruppo_keys` contiene un documento non valido.",
            detail=repr(elemento),
            function_name=fn,
            log_to_db=False,
        )
        valore = elemento.strip()
        if valore not in chiavi:
            chiavi.append(valore)
    return tuple(chiavi)


# Scopo: Restituisce riepilogo segnalazioni del lotto con regola di blocco step successivo.
def fn_get_lotto_segnalazioni_summary(*, lotto_id: int, auth_user_id: int | None) -> dict[str, Any]:
    ErrorManager.require(
        bool(lotto_id and lotto_id > 0),
        code="E_PIPELINE_VALIDATION",
        message="Parametri pipeline non validi.",
        detail="lotto_id obbligatorio e > 0",
        context={"lotto_id": lotto_id},
        function_name="vendite.pipeline_service.fn_get_lotto_segnalazioni_summary",
        log_to_db=True,
    )
    # ⛔ Il cancello di perimetro PRIMA dei conteggi: senza, un lotto fuori
    #    scope rispondeva zero segnalazioni, cioe' «lotto pulito» (2026-10-20).
    lotto_visibile(
        lotto_id=lotto_id, auth_user_id=auth_user_id,
        function_name="vendite.pipeline_service.fn_get_lotto_segnalazioni_summary",
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
def fn_get_lotto_task_runs(
    *,
    lotto_id: int,
    auth_user_id: int | None,
    limit: int = DEFAULT_LIMIT_EVENTI,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str = "desc",
    solo_giro_corrente: bool = False,
    task_stato: list[str] | None = None,
    max_rows: int | None = None,
) -> dict[str, Any]:
    ErrorManager.require(
        bool(lotto_id and lotto_id > 0),
        code="E_PIPELINE_VALIDATION",
        message="Parametri pipeline non validi.",
        detail="lotto_id obbligatorio e > 0",
        context={"lotto_id": lotto_id},
        function_name="vendite.pipeline_service.fn_get_lotto_task_runs",
        log_to_db=True,
    )
    # ⛔ La finestra (`limit` fra 1 e il tetto, `offset` non negativo) la
    #    valida la view con `pagina_da_query`, che dal 2026-10-21 risponde 400
    #    sul fuori limite (Tid): qui era una seconda copia, irraggiungibile.
    # ⛔ Il predicato unico `order_dir_ammessa` (2026-09-26), non un secondo
    #    `in ("asc", "desc")`: la fn DB legge `lower(btrim(...))`, quindi
    #    maiuscole, spazi e assenza (= il suo default `desc`) sono gia' suoi.
    ErrorManager.require(
        order_dir_ammessa(order_dir),
        code="E_PIPELINE_VALIDATION",
        message="Parametri pipeline non validi.",
        detail=f"order_dir={order_dir!r} non ammesso",
        context={"lotto_id": lotto_id, "order_dir": order_dir},
        function_name="vendite.pipeline_service.fn_get_lotto_task_runs",
        log_to_db=False,
    )
    # ⛔ Il cancello di perimetro PRIMA dell'elenco (vedi `_lotto_perimetro`).
    lotto_visibile(
        lotto_id=lotto_id, auth_user_id=auth_user_id,
        function_name="vendite.pipeline_service.fn_get_lotto_task_runs",
    )
    repository = VenditePipelineRepository()
    runs: list[LottoTaskRunRow]
    # ⚠️ Il vocabolario degli stati NON si valida qui: lo possiede la funzione
    # DB, e uno stato che non conosce non aggiunge e non toglie nulla. Un
    # elenco chiuso ricopiato nel backend sarebbe la seconda verita' sullo
    # stesso vocabolario — la stessa ragione per cui `order_by` passa intatto.
    runs, total_count, esclusi_count = repository.list_lotto_task_runs(
        lotto_id,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
        solo_giro_corrente=solo_giro_corrente,
        task_stato=task_stato,
        max_rows=max_rows,
    )
    # ⚠️ ENVELOPE PAGINATO, non piu' `{lotto_id, count, task_runs}`: `count`
    # diceva quante righe erano ARRIVATE, cioe' la dimensione della pagina, e
    # una lista che si paginava da sola l'avrebbe letto come «totale». Le
    # chiavi sono quelle di tutte le altre liste (`envelope_da_offset`), cosi'
    # il BB di lista non ha bisogno di sapere che questa e' speciale.
    # 📌 `task_runs` resta come alias di `results` per il consumatore attuale
    # del drawer: la conversione a `<ListaConfigurabile>` e' un altro passo
    # (FE-2) e questo endpoint non deve romperlo nel frattempo.
    envelope = envelope_da_offset(runs, total_count, limit=limit, offset=offset)
    return {
        "lotto_id": lotto_id,
        "count": envelope["count"],
        "page": envelope["page"],
        "page_size": envelope["page_size"],
        "total_pages": envelope["total_pages"],
        # ⭐ Quante righe i filtri lasciano FUORI — il gemello di
        # `fuori_job_count` delle segnalazioni, con un nome piu' largo perche'
        # qui i filtri sono DUE (stato e giro): un nome che parlasse del giro
        # avrebbe costretto a inventarne un secondo alla prossima domanda.
        # ⛔ Senza questo numero una lista filtrata e una lista vuota si
        # leggono uguali — ed e' il difetto che il filtro «giro corrente»
        # produrrebbe da solo, visto che sul lotto 6260 mostra 1 riga su 90.
        "esclusi_count": esclusi_count,
        "results": runs,
        "task_runs": runs,
    }

