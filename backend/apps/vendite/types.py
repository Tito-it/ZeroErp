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


# ── Preventivi vendita ──


class PreventivoListRow(TypedDict):
    id: int
    uid: str
    numero: str
    rev: int
    is_attiva: bool
    data: str
    stato_doc_preventivo_id: int
    stato_codice: str
    stato_descrizione: str
    billing_account_id: int | None
    ba_utility_id: int | None
    soggetto_id: str | None
    cliente_denominazione: str | None
    emittente_fiscale_id: int | None
    utility_id: int
    istanza_utility_id: int | None
    totale_imponibile: str | None
    totale_iva: str | None
    totale_documento: str | None
    valuta_id: int | None
    valuta_codice: str | None
    termine_pagamento_id: int | None
    termine_pagamento_descrizione: str | None
    validita_dal: str | None
    validita_al: str | None
    competenza_mese: str | None
    fatturazione_immediata: bool
    storicizza: bool
    data_insert: str | None


class PreventivoDetailRow(TypedDict):
    id: int
    uid: str
    numero: str
    rev: int
    is_attiva: bool
    data: str
    stato_doc_preventivo_id: int
    stato_codice_interno: str
    stato_codice: str
    stato_descrizione: str
    billing_account_id: int | None
    cliente_denominazione: str | None
    utility_id: int
    utility_descrizione: str | None
    istanza_utility_id: int | None
    valuta_id: int | None
    valuta_codice: str | None
    termine_pagamento_id: int | None
    termine_pagamento_descrizione: str | None
    validita_dal: str | None
    validita_al: str | None
    competenza_mese: str | None
    fatturazione_immediata: bool
    totale_imponibile: str | None
    totale_iva: str | None
    totale_documento: str | None
    emittente_fiscale_id: int | None
    emittente_fiscale_codice: str | None
    emittente_fiscale_descrizione: str | None
    ba_ha_contratto_attivo: bool
    storicizza: bool
    meta: dict[str, Any]
    data_insert: str | None
    user_insert: str
    data_update: str | None
    user_update: str | None


class PreventivoRigaRow(TypedDict):
    id: int
    preventivo_id: int
    articolo_id: str
    codice_articolo: str
    descrizione_articolo: str
    descrizione: str | None
    quantita: str | None
    qta_operativa: str | None
    uom_operativa_id: int | None
    codice_uom: str | None
    factor_to_base: str | None
    prezzo_unitario: str | None
    sconto_percentuale: str | None
    iva_id: int | None
    codice_iva: str | None
    aliquota_iva: str | None
    ordine: int | None
    attivo: bool
    importo_riga: str | None
    importo_iva_riga: str | None
    meta: dict[str, Any]
    is_composito_caso_a: bool


class PreventivoRigaComponenteRow(TypedDict):
    id: int
    riga_preventivo_id: int
    articolo_componente_id: str
    componente_id: str
    componente_codice: str | None
    componente_descrizione: str | None
    coeff_qta_snapshot: str
    quantita: str
    uom_operativa_id: int | None
    uom_codice: str | None
    factor_to_base: str | None
    qta_operativa: str | None
    prezzo_unitario: str
    iva_id: int | None
    iva_codice: str | None
    iva_aliquota: str | None
    origine_prezzo: str
    prezzo_resolver_context: dict[str, Any] | None
    stato_approvazione_prezzo: str | None
    pratica_approvazione_prezzo_id: int | None
    meta: dict[str, Any]
    ordine: int | None
    attivo: bool
    obbligatorio: bool
    esposto_in_fattura: bool


class PreventivoRigaComponentePreviewRow(TypedDict):
    articolo_componente_id: str
    componente_id: str
    componente_codice: str | None
    componente_descrizione: str | None
    coeff_qta_snapshot: str
    quantita_componente: str
    uom_id: int | None
    uom_codice: str | None
    iva_id: int | None
    prezzo_suggerito: str | None
    origine_prezzo: str | None
    resolver_error_reason: str | None
    obbligatorio: bool
    esposto_in_fattura: bool


# Componente BoM di riga contratto (modello unificato 2026-05-13). Specchio
# simmetrico di `PreventivoRigaComponenteRow`, differisce solo per FK
# `riga_contratto_id` (vs `riga_preventivo_id`).
class ContrattoRigaComponenteRow(TypedDict):
    id: int
    riga_contratto_id: int
    articolo_componente_id: str
    componente_id: str
    componente_codice: str | None
    componente_descrizione: str | None
    coeff_qta_snapshot: str
    quantita: str
    uom_operativa_id: int | None
    uom_codice: str | None
    factor_to_base: str | None
    qta_operativa: str | None
    prezzo_unitario: str
    iva_id: int | None
    iva_codice: str | None
    iva_aliquota: str | None
    origine_prezzo: str
    prezzo_resolver_context: dict[str, Any] | None
    stato_approvazione_prezzo: str | None
    pratica_approvazione_prezzo_id: int | None
    meta: dict[str, Any]
    ordine: int | None
    attivo: bool
    obbligatorio: bool
    esposto_in_fattura: bool


class PreventivoIndirizzoRow(TypedDict):
    id: int
    preventivo_id: int
    tipo_indirizzo_id: int
    tipo_indirizzo_descrizione: str | None
    snapshot: dict[str, Any]
    origine_indirizzo_id: int | None
    origine_soggetto_ruolo_id: int | None


class PreventivoStatoFatturazioneRow(TypedDict):
    preventivo_id: int
    preventivo_uid: str
    righe_totali: int
    righe_in_commessa: int
    righe_emesse_af: int
    righe_fatturate: int


class PreventivoPraticaRow(TypedDict):
    pratica_id: int
    pratica_codice: str | None
    pratica_descrizione: str | None
    stato_codice: str
    stato_descrizione: str
    ruolo_link: str


# ── Offerte commerciali ──
# Specchio strutturale di Contratto/ContrattoRiga/ContrattoUtility (decisioni
# §5 analisi-offerta-commerciale + brief DB 2026-05-24 step 1-4 atterrati).
# Le date/Decimal sono `str` ISO/serializzati, coerente col pattern preventivi
# e contratti (psycopg ritorna stringhe via row_to_dict).


class OffertaRow(TypedDict):
    id: int
    uid: str
    codice: str
    emittente_fiscale_id: int
    billing_account_id: int
    istanza_utility_id: int
    utility_id: int
    listino_id: int
    listino_versione_id: int | None
    valore_variazione_globale: str | None
    tipo_variazione_globale: str | None
    validita_dal: str
    validita_al: str | None
    stato_doc_offerta_id: int
    revisione_numero: int
    revisione_padre_id: int | None
    data_emissione: str | None
    data_accettazione: str | None
    data_rifiuto: str | None
    data_annullamento: str | None
    motivazione_rifiuto: str | None
    meta: dict[str, Any]
    # Display fields da JOIN. Naming coerente col piano FE+BE rev. f:
    # `billing_account_display` + `utility_display` sono i campi consumati
    # dal drawer/lista (display fields backend, niente lookup client-side).
    stato_codice_interno: str
    stato_descrizione: str
    ba_codice: str | None
    billing_account_display: str | None
    utility_codice: str | None
    utility_display: str | None
    listino_codice: str | None
    listino_descrizione: str | None
    listino_versione_codice: str | None
    # Riferimento al contratto generato (pattern A idempotenza). NULL se
    # l'offerta non e' ancora stata pushata (o non e' ACCETTATA). Coppia
    # stabile id + numero: il FE puo' linkare al ContrattoDrawer e mostrare
    # il dialog parlante post-E_OFFERTA_CONTRATTO_GIA_GENERATO.
    contratto_id: int | None
    contratto_numero: str | None
    # Capability blob da `script.fn_available_actions_offerta` merged sul
    # detail in `OfferteService.get_offerta` (data-driven 2026-05-26).
    # Il FE consuma questi campi con `useEntityCapabilities` +
    # `mapAvailableActionsToDrawerActions` senza ricalcolare la state
    # machine: la verita' della transizione vive solo in DB.
    # `available_actions` e' lista di dict opachi (chiave/label_key/severity/
    # icon/target_state/requires_confirm/requires_motivazione) — Any per non
    # vincolare il TypedDict a una sotto-shape che il BE puo' arricchire.
    available_actions: list[dict[str, Any]]
    can_change_state: bool
    can_edit_testata: bool
    can_edit_eccezioni: bool
    can_edit_utility: bool
    can_create_revisione: bool
    can_push_contratto: bool
    can_push_contratto_reason: str | None
    can_push_contratto_reason_key: str | None
    non_editable_fields: list[str]
    stato_codice: str
    # Audit
    data_insert: str
    user_insert: str
    data_update: str | None
    user_update: str | None


class OffertaEccezioneRow(TypedDict):
    id: int
    offerta_id: int
    articolo_id: str
    articolo_codice: str | None
    articolo_descrizione: str | None
    tipo_eccezione: str
    tipo_erogazione: str | None
    fonte_quantita_attesa: str
    periodicita: str | None
    generazione_canone: str | None
    competenza_canone: str | None
    prezzo_unitario: str | None
    quantita: str | None
    qta_operativa: str | None
    uom_operativa_id: int | None
    uom_codice: str | None
    factor_to_base: str
    ordine: int | None
    attivo: bool
    meta: dict[str, Any]


class OffertaUtilityRow(TypedDict):
    id: int
    offerta_id: int
    istanza_utility_id: int
    utility_id: int
    utility_codice: str | None
    utility_descrizione: str | None
    istanza_dati_precontrattuali_id: int | None
    tipo_utenza_id: int | None
    tipo_utenza_codice: str | None
    tipo_utenza_descrizione: str | None
    classe_utenza_id: int | None
    classe_utenza_codice: str | None
    classe_utenza_descrizione: str | None
    param_1_num: str | None
    param_2_txt: str | None
    meta: dict[str, Any]


class NotaOffertaRow(TypedDict):
    id: int
    offerta_id: int
    eccezione_id: int | None
    autore: str | None
    testo: str
    meta: dict[str, Any]
    data_insert: str
    user_insert: str
    data_update: str | None
    user_update: str | None


class OffertaPushResult(TypedDict):
    # In attesa step 8 brief DB (fn_push_offerta_a_contratto). TypedDict
    # definito per stabilizzare la forma di ritorno futura.
    contratto_id: int
    contratto_codice: str
    sorgente_uid: str
