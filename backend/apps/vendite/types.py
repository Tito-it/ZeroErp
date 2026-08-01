from datetime import date

from typing import Any, TypeAlias, TypedDict

# Tipi condivisi pipeline vendite per ridurre chiavi "magiche" e firma duplicate.

LottoPipelineMeta: TypeAlias = dict[str, Any]


class PipelineStepLogMeta(TypedDict):
    ordine: int | None
    dry_run: bool


# Chiave di raggruppamento delle attivita' fatturabili in riga di fattura.
# Serializzata in `fatture_righe.meta.group_key` come traccia dell'aggregazione.
# `prezzo_unitario` e' una STRINGA canonica e non un float: il prezzo e' cio' che
# rende l'aggregazione un'identita' esatta (somma(qi*p) = p*somma(qi)), e
# raggruppare su un float la renderebbe approssimata.
# `visibilita_componenti` e' uscita dal modello il 2026-07-28: non era la regola
# di esposizione dei kit (quella e' `articoli_componenti.esposto_in_fattura`) e
# non aveva alcun consumatore vivo.
class GroupAttivitaKey(TypedDict):
    articolo_id: str  # uuid (catalogo.articoli.id)
    dest_billing_account_id: int
    uom_id: int | None
    prezzo_unitario: str | None
    iva_id: int | None
    competenza_dal: str | None
    competenza_al: str | None
    calcolo_qta_padre: str
    arrotondamento_importi_dec: int
    arrotondamento_quantita_dec: int
    metodo_arrotondamento_importi: str
    metodo_arrotondamento_quantita: str


class AnnullaLottoDaDraftResult(TypedDict):
    updated_lotti: int
    updated_attivita: int
    deleted_fatture: int
    deleted_righe: int


class EliminaFatturaDaLottoDraftResult(TypedDict):
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
    stato_doc_fiscale_codice: str | None
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
    # Codice stabile (codice_interno) dello stato doc fiscale: i gate FE usano
    # SEMPRE il codice, mai la descrizione display (lezione B-4). Es. 'EMESSA'
    # abilita «Rendi definitive» (C-4).
    stato_doc_fiscale_codice: str | None
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


class CommessaEmittibileLane(TypedDict):
    # Terna (emittente, tipo_doc_fiscale, utility) con lavoro pronto da fatturare, prodotta
    # da vendite.fn_list_emittibili_lane (discovery del driver batch). `competenza_mese`
    # è la competenza (max delle righe candidate) con cui creare il lotto; le righe con
    # tipo_doc_fiscale NULL sono escluse a monte dalla funzione DB (il lotto la richiede
    # NOT NULL). utility_id è NOT NULL a monte (commesse.utility_id) → mai NULL. emittente
    # può essere NULL (commesse senza emittente, non fatturabili).
    emittente_soggetto_ruolo_id: int | None
    tipo_doc_fiscale_id: int
    utility_id: int
    competenza_mese: date
    total_candidate: int


class CommessaStatoResult(TypedDict):
    # Stato testata + flag di governance (da vendite.stati_commessa)
    stato_commessa_id: int
    stato_commessa: str
    chiude_commessa: bool
    emittibile: bool
    modificabile: bool
    # Config testata
    policy_fatturazione: str | None
    fatturazione_immediata: bool | None
    priorita_operativa: str | None
    billing_account_id: int | None
    utility_id: int | None
    emittente_soggetto_ruolo_id: int | None
    # Contatori righe commesse_attivita
    total_attivita: int
    total_approvate: int
    total_non_approvate: int
    total_emesse: int
    total_non_emesse: int
    total_prezzo_da_riallineare: int
    last_update: str | None
    # Identificazione testata (brief-db-guard-uscita-commessa D6): codice della
    # COMMESSA (c.codice, non lo stato) + ragione sociale cliente. Il drawer li
    # usa per correlarsi alla lista (che mostra commessa_codice) invece di #<PK>.
    commessa_codice: str | None
    cliente_display: str | None


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
    soggetto_ruolo_id: int | None
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
    # ⚠️ Nonostante il nome, porta la RAGIONE SOCIALE del soggetto emittente
    # (`soggetti.ragione_sociale_completa`), non `emittenti_fiscali.descrizione`:
    # quella e' un'etichetta interna divergente, in via di eliminazione (brief
    # `brief-emittente-ragione-sociale-dal-soggetto.md`). L'alias e' rimasto per
    # non rompere 40+ punti a valle; la rinomina e' una fase separata.
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


# Aggregato smistamento per ramo (vw_preventivi_smistamento, sostituisce la
# vecchia vw_preventivi_stato_fatturazione — rename DB 2026-06-12,
# brief-db-smistamento-preventivi.md B). `righe_in_commessa` ora conta solo
# attivita' EMESSA (predicato allineato a capability e list-fn).
class PreventivoSmistamentoRow(TypedDict):
    preventivo_id: int
    preventivo_uid: str
    righe_totali: int
    righe_merce: int
    righe_servizi: int
    righe_a_ordine: int
    righe_in_commessa: int
    righe_emesse_af: int
    righe_fatturate: int
    righe_residue: int


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
    soggetto_ruolo_id: int
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
    # Denormalizzazione EF (pattern preventivi): consumati da
    # `EmittenteFiscaleField` in modalita' edit per costruire la option
    # singola del Select disabled senza round-trip aggiuntivo.
    # ⚠️ `emittente_fiscale_descrizione` porta la RAGIONE SOCIALE del soggetto
    # emittente, non `emittenti_fiscali.descrizione` (vedi PreventivoDetailRow).
    emittente_fiscale_codice: str | None
    emittente_fiscale_descrizione: str | None
    ba_codice: str | None
    billing_account_display: str | None
    # ID fiscale univoco (CF persona fisica o P.IVA) del soggetto del BA.
    # Esposto via JOIN `anagrafiche.vw_soggetti_ruoli_dettaglio`.
    id_fiscale: str | None
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
    stato_codice_interno: str
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
    is_composito: bool
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
    componenti: list[dict[str, Any]]


class OffertaEccezioneComponenteRow(TypedDict):
    id: int
    eccezione_offerta_id: int
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


class DashApertoRiepilogoRow(TypedDict):
    # Cella area × fase del serbatoio pre-commessa (vw_dash_aperto_riepilogo v2,
    # stock senza asse temporale — il pivot area/fasi e' del service). Perimetro
    # aperti-non-chiusi lato vista (DL-15): via n_aperti/valore_transitato.
    # valore_totale NULL per le aree a conteggi (OFFERTE/CONTRATTI, DL-11).
    area: str
    fase: str
    n_documenti: int
    valore_totale: str | None


class DashApertoDocumentoRow(TypedDict):
    # Riga drill-down del serbatoio pre-commessa (vw_dash_aperto_documenti v2:
    # 4 aree documento, perimetro aperti-non-chiusi — is_transitato IS DISTINCT
    # FROM true AND fase<>CHIUSO, DL-14/15). anzianita_giorni derivata in SELECT
    # (GREATEST(current_date - data_riferimento, 0)) come il gemello Backlog,
    # allinea la lettura al filtro "aperti da oltre N giorni" (DL-17).
    area: str
    documento_id: int
    documento_uid: str | None
    codice: str | None
    cliente_display: str | None
    fase: str | None
    stato_codice_interno: str | None
    stato_codice: str | None
    valore_totale: str | None
    unita_totali: int | None
    anzianita_giorni: int
    motivo_fermo: str | None
    data_riferimento: str | None


class DashCompetenzaMensileRow(TypedDict):
    # Riga aggregata Lente 1 Competenza (vw_dash_competenza_mensile, formato
    # lungo mese × stadio × stato fattura — il pivot ai 4 blocchi e' del service).
    # stato_fattura_* NULL per gli stadi non fatturati.
    competenza_mese: str
    stadio: str
    stato_fattura_codice_interno: str | None
    stato_fattura_codice: str | None
    n_attivita: int
    valore: str
    valore_fatturato: str
    n_in_ritardo: int
    valore_in_ritardo: str


class DashCompetenzaAttivitaRow(TypedDict):
    # Riga drill-down attivita' Lente 1 (vw_dash_competenza_attivita + decode
    # articolo via JOIN). Campi fattura NULL per gli stadi non fatturati;
    # data_emissione/emessa_in_ritardo NULL se non emessa.
    commessa_attivita_id: int
    commessa_id: int
    commessa_codice: str | None
    cliente_display: str | None
    articolo_id: str | None
    articolo_codice: str | None
    articolo_descrizione: str | None
    data_attivita: str | None
    quantita: str | None
    stadio: str
    stato_approvazione: str | None
    stato_emissione: str | None
    valore: str | None
    data_emissione: str | None
    emessa_in_ritardo: bool | None
    sospesa: bool | None
    posticipa_al: str | None
    fattura_id: int | None
    fattura_anno: int | None
    fattura_serie: str | None
    fattura_numero: int | None
    # Lotto della fattura (NULL fuori dagli stadi con fattura in lotto): abilita
    # l'atterraggio contestuale sul LottoDrawer dal drill-down (B-5).
    lotto_id: int | None
    stato_fattura_codice_interno: str | None
    stato_fattura_codice: str | None
    valore_fatturato: str | None
    fattura_critical: bool


class DashCompetenzaCommessaRow(TypedDict):
    # Riga drill-down AGGREGATA per commessa (DEC-4): una riga per commessa nel
    # perimetro corrente (competenza_mese + stadio + solo_ritardo), invece della
    # grana attivita'. Le n attivita' e gli estremi fattura restano nel drawer.
    commessa_id: int
    commessa_codice: str | None
    cliente_display: str | None
    n_attivita: int
    n_in_ritardo: int
    valore_tot: str | None
    valore_fatturato_tot: str | None
    data_attivita_min: str | None
    data_attivita_max: str | None


class DashCompetenzaGruppoRow(TypedDict):
    # Riga dell'elenco GRUPPI FATTURABILI (vw_dash_competenza_gruppi): l'unita'
    # su cui l'operatore decide nella card «Da emettere» — un documento sorgente
    # OPPURE le righe manuali/oneri di una commessa (che documento non hanno).
    # `gruppo_key` e' la chiave costruita da fn_build_gruppo_fatturabile_key: e'
    # la STESSA che si rimanda al POST di emissione mirata, senza mapping.
    gruppo_key: str
    tipo_gruppo: str
    area_documento: str | None
    riferimento: str | None
    commessa_id: int | None
    commessa_codice: str | None
    cliente_display: str | None
    stadio: str | None
    n_attivita: int
    valore: str | None
    ha_oneri: bool
    data_attivita_min: str | None
    data_attivita_max: str | None


class DashCompetenzaGruppoTipoRow(TypedDict):
    # Voce del filtro «tipo documento/sorgente» della lista gruppi, calcolata
    # SUI DATI del perimetro (facet) e non da `config.sorgenti`. Due ragioni:
    # quella tabella contiene sorgenti che non possono mai essere un gruppo
    # fatturabile (i `*_RIGA` con scope ROW_VALIDATOR, FATTURA, RESO_VENDITA) e
    # NON contiene `ONERI_COMMESSA`, che e' un valore sintetico della vista —
    # cioe' proprio il caso che si vuole poter isolare.
    tipo_gruppo: str
    area_documento: str | None
    n_gruppi: int
    n_attivita: int


class DashCompetenzaGruppiRiepilogoRow(TypedDict):
    # Totali di perimetro dell'elenco gruppi (vw_dash_competenza_gruppi_riepilogo):
    # aggregano la vista di dettaglio, quindi non possono divergere da essa.
    # Vengono dal DB e non dal FE di proposito: sommare la pagina corrente
    # mostrerebbe un parziale che sembra un totale.
    n_gruppi: int
    n_attivita: int
    valore: str | None
    n_gruppi_oneri: int


class DashBacklogRiepilogoRow(TypedDict):
    # Riga contatori Lente 2 Backlog (vw_dash_backlog_riepilogo, grana
    # classe × area — il pivot per classe e' del service).
    classe: str
    area: str
    n_documenti: int
    valore_fermo_tot: str | None
    unita_ferme_tot: int
    anzianita_max_giorni: int | None


class DashBacklogDocumentoRow(TypedDict):
    # Riga lista Lente 2 Backlog (vw_dash_backlog_documenti): non-collegati
    # non-verdi per anzianita'. valore_fermo NULL per le aree a conteggi;
    # azione = hint operativo dalla lookup config.motivi_fermo.
    area: str
    competenza_mese: str | None
    documento_id: int
    documento_uid: str | None
    codice: str | None
    cliente_display: str | None
    valore_fermo: str | None
    unita_ferme: int | None
    motivo_fermo: str
    classe: str
    azione: str | None
    data_riferimento: str | None
    anzianita_giorni: int | None
    stato_codice_interno: str | None
    stato_codice: str | None
    fase: str | None


class DashCompetenzaErroreRow(TypedDict):
    # Riga blocco errori Lente 1 (vw_dash_competenza_errori): union
    # TASK_ERRORE (campi fattura NULL) + FATTURA_CRITICA (task_code NULL).
    tipo_evento: str
    competenza_mese: str | None
    lotto_id: int | None
    lotto_codice: str | None
    stato_lotto: str | None
    fattura_id: int | None
    fattura_anno: int | None
    fattura_serie: str | None
    fattura_numero: int | None
    task_code: str | None
    error_code: str | None
    messaggio: str | None
    data_evento: str | None


class LineageSorgenteRow(TypedDict):
    # Riga di config.sorgenti per la risoluzione della chiave nodo lineage
    # (convenzione chiave sorgente: docs/it/dbzero/config/manual/sorgenti.md).
    id: int
    key_selector: str
    target_table: str


class LineageNodoRow(TypedDict):
    # Riga summary di vendite.vw_documento_lineage per un documento:
    # nodo + pratica collegata + frontiera forward + contatori genealogia.
    tipo_id: int
    tipo_codice: str
    uid: str
    codice: str | None
    stato_codice_interno: str | None
    stato_codice: str | None
    stato_descrizione: str | None
    fase: str | None
    is_abortito: bool
    pratica_id: int | None
    pratica_numero: str | None
    n_pratiche: int
    frontiera_tipo_id: int | None
    frontiera_tipo_codice: str | None
    frontiera_uid: str | None
    frontiera_codice: str | None
    frontiera_stato_codice_interno: str | None
    frontiera_fase: str | None
    n_discendenti_diretti: int
    n_discendenti_attivi: int
    is_transitato: bool
    n_sorgenti: int
    root_codice: str | None


class LineagePassaggioRow(TypedDict):
    # Riga del traversal vendite.fn_documento_lineage (pannello "Passaggi"):
    # un arco della catena, con stato/fase del nodo target e flag ramo
    # inverso (arco R DDT->Reso, merce che torna).
    livello: int
    ordine: int
    arco: str
    ruolo: str | None
    from_tipo_id: int
    from_tipo_codice: str | None
    from_uid: str
    from_codice: str | None
    from_stato_codice_interno: str | None
    from_fase: str | None
    from_doc_id: int | None
    to_tipo_id: int
    to_tipo_codice: str | None
    to_uid: str
    to_codice: str | None
    to_stato_codice_interno: str | None
    to_fase: str | None
    to_is_abortito: bool
    to_doc_id: int | None
    is_ramo_inverso: bool
