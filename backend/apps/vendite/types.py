from typing import Any, TypeAlias, TypedDict

# Tipi condivisi pipeline vendite per ridurre chiavi "magiche" e firma duplicate.

LottoPipelineMeta: TypeAlias = dict[str, Any]


class PipelineStepLogMeta(TypedDict):
    ordine: int | None
    dry_run: bool


class GroupAttivitaKey(TypedDict):
    articolo_id: int
    dest_billing_account_id: int
    uom_id: int | None
    prezzo_unitario: float | None
    iva_id: int | None
    competenza_dal: str | None
    competenza_al: str | None
    visibilita_componenti: str
    calcolo_qta_padre: str
    arrotondamento_importi_dec: int
    arrotondamento_quantita_dec: int
    metodo_arrotondamento_importi: str
    metodo_arrotondamento_quantita: str


class ResetLottoDraftResult(TypedDict):
    updated_lotti: int
    updated_attivita: int
    deleted_fatture: int
    deleted_righe: int


class ResetLottoFatturaDraftResult(TypedDict):
    updated_attivita: int
    deleted_fatture: int
    deleted_righe: int


class LottoSegnalazioniSummary(TypedDict):
    fatture_critical_count: int
    fatture_warning_count: int
    lotto_critical_count: int
    lotto_warning_count: int
    lotto_info_count: int
    fatture_stato_esecuzione_errore_count: int


class LottoTaskRunRow(TypedDict):
    id: int
    lotto_id: int
    pipeline_id: int | None
    stato_doc_fiscale_id: int | None
    task_code: str
    fase: str | None
    tentativo: int
    task_stato: str
    started_at: str | None
    ended_at: str | None
    error_code: str | None
    error_message: str | None
    meta: dict[str, Any]


class LottoFattureRow(TypedDict):
    id: int
    lotto_id: int
    fattura_id: int
    stato_sdi_id: int | None
    stato_sdi_descrizione: str | None
    stato_doc_fiscale_id: int | None
    stato_doc_fiscale_descrizione: str | None
    stato_esecuzione: str
    esclusa: bool
    numero: int | None
    serie: str | None
    data: str | None
    billing_account_id: int
    totale_doc: str | None
    totale_a_pagare: str | None
    soggetto_id: int
    ragione_sociale_completa: str | None
    id_fiscale_univoco_cf_piva: str | None


class LottoListRow(TypedDict):
    id: int
    codice: str
    competenza_mese: str | None
    tipo_lotto: str
    utility_id: int | None
    utility_descrizione: str | None
    stato_lotto: str
    stato_operativo: str
    stato_doc_fiscale_id: int | None
    stato_doc_fiscale_descrizione: str | None
    tipo_doc_fiscale_id: int
    tipo_doc_fiscale_descrizione: str | None
    area_geografica_id: int | None
    area_geografica_descrizione: str | None
    emittente_soggetto_ruolo_id: int | None
    data_insert: str | None
    user_insert: str


class CommessaEmitResult(TypedDict):
    total_candidate: int
    inserted_rows: int
    updated_rows: int


class CommessaStatoResult(TypedDict):
    total_attivita: int
    total_approvate: int
    total_emesse: int


class CommessaPushLogRow(TypedDict):
    id: int
    run_at: str
    dry_run: bool
    source_types: list[str] | None
    risultato: dict[str, Any] | None
    stato: str
    durata_ms: int | None
