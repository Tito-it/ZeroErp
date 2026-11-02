// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Client API del dominio MAGAZZINO — le rotte di `/api/v1/magazzino/`:
//        il documento interno (inventari e rettifiche, STESSA forma sotto due
//        segmenti), l'anteprima dei motivi di riga, i tre lookup di riga, le
//        tre ANAGRAFICHE (magazzini, ubicazioni, lotti) e la consultazione
//        (disponibilita', movimenti).
// Note: Piano: docs/it/dev/work-done/piano-be-fe-magazzino-lotto-2-motore.md
//       ⭐ Le rotte del documento interno prendono la FAMIGLIA come primo
//       argomento (`'inventari'` | `'rettifiche'`, da `FAMIGLIA` di
//       `vocabolari.js`): il backend le monta da una sola factory sotto
//       `<famiglia>/`, e due elenchi di funzioni scritti a mano divergerebbero
//       al primo verbo nuovo — Q-1 del piano, decisa da Tid il 2026-09-18.
//       ⚠️ Le liste sono OFFSET-based (`limit`/`offset`, `{count, results}`),
//       la lingua di `useSearchTable`: nessuna conversione nello store.
//       ⛔ `POSTED` non si chiede con `stato/`: lo scrive SOLO `registra/`
//       (il guard risponderebbe con un TECNICO, cioe' un 500 per un pulsante).
// ------------------------------------------------------------

import api from '../../core/api'
import { FAMIGLIA } from '../vocabolari'

const BASE = '/magazzino'


// Scopo: il prefisso di una famiglia: `/magazzino/inventari` | `/magazzino/rettifiche`.
function base(famiglia) {
  return `${BASE}/${famiglia}`
}

// ══════════════════════════════════════════════════════════════
//  Il documento interno — testata
// ══════════════════════════════════════════════════════════════

// Elenco paginato delle testate. Filtri: `magazzino_id`, `stato`, `data_da`/
// `data_a` (il floor standard lo applica lo store), `search` (min 3, sotto:
// 400; le colonne le accende il catalogo della lista). Senza ordinamento:
// `data DESC, id DESC`.
export function listDocumenti(famiglia, params = {}) {
  return api.get(`${base(famiglia)}/`, { params })
}

// Scopo: export CSV/Excel dell'elenco, con gli stessi filtri e ordinamento.
// ⚠️ `formato` e non `format`: quest'ultimo e' un parametro magico di DRF e
//    collide col content negotiation (`feedback_drf_format_magic_param`).
//    Risposta Blob: errore 422 se il dataset supera il cap.
export function exportDocumenti(famiglia, params = {}) {
  return api.get(`${base(famiglia)}/export/`, { params, responseType: 'blob' })
}

// ⭐ Crea la BOZZA. Il magazzino si sceglie QUI e basta: e' l'ancora del
//    documento (RLS, ubicazioni delle righe, `qta_sistema` del piano) e il
//    PATCH non lo accetta. Payload: `magazzino_id` (obbligatorio), `data`
//    (default oggi, a DB), `descrizione` (solo inventario), `meta`.
export function creaDocumento(famiglia, payload) {
  return api.post(`${base(famiglia)}/`, payload)
}

// Dettaglio: testata + magazzino (`magazzino_codice`, `_descrizione`,
// `magazzino_usa_ubicazioni`) + `righe_count` e, per l'inventario,
// `piano_riepilogo`. ⭐ E le `capabilities` (R-1, dal 2026-09-23; la nota di
// stato sta SOLO li'): `available_actions[]` (le transizioni che il guard ammette),
// `can_registra` + `_reason` + `_reason_key`, `can_edit_testata`/`_righe`,
// `can_delete`, `stato_info_key`. Il blob viene da
// `script.fn_available_actions_<famiglia>` e il backend lo trasporta intatto:
// il drawer ci disegna la barra senza sapere le regole che ci stanno dietro.
export function getDocumento(famiglia, docId) {
  return api.get(`${base(famiglia)}/${docId}/`)
}

// PATCH della testata: `data`, `descrizione` (solo inventario), `meta`.
// ⛔ Non lo stato (`stato/`), non il magazzino (si sceglie alla nascita).
export function aggiornaDocumento(famiglia, docId, payload) {
  return api.patch(`${base(famiglia)}/${docId}/`, payload)
}

// Elimina una BOZZA: il DB decide (`E_MAG_DOCUMENTO_NON_ELIMINABILE`, 409
// fuori da `DRAFT`). ⚠️ Il metodo dice il verbo: niente `/elimina/` nel path.
// E' una scrittura, quindi porta l'`Idempotency-Key` come le POST.
export function eliminaDocumento(famiglia, docId) {
  return api.delete(`${base(famiglia)}/${docId}/`)
}

// Chiede un cambio di stato fra i RICHIEDIBILI (`CONFIRM` · `CANCEL` · `DRAFT`);
// la matrice la applica il guard (`E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`).
export function cambiaStatoDocumento(famiglia, docId, stato) {
  return api.post(`${base(famiglia)}/${docId}/stato/`, { stato })
}

// ⛔ IL POSTING, l'unico gesto irreversibile del dominio: una `SELECT` sulla
//    madre (`fn_posta_*`), il DB e' la transazione. Rifiuta non-`CONFIRM`, senza
//    righe, righe non postabili — TUTTO, lo stato resta `CONFIRM`. Risposta:
//    `{movimenti: [{movimento_id, riga_id, qta}], n_movimenti, documento}`.
//    Gate: azione di processo `registra_magazzino` (R-3, fail-closed).
export function registraDocumento(famiglia, docId, config = {}) {
  return api.post(`${base(famiglia)}/${docId}/registra/`, {}, config)
}

// ══════════════════════════════════════════════════════════════
//  Il documento interno — righe e piano
// ══════════════════════════════════════════════════════════════

// Le righe di UNA testata, paginate (lista `magazzino.<famiglia>_righe`).
// Filtro `search` (colonne dal catalogo; sotto 3 caratteri non filtra): la
// casella sta nel `#filtri-sempre` del drawer del documento e compare solo se
// il catalogo accende almeno una colonna (`ricerca_full`).
// Senza ordinamento: `id ASC`, l'ordine di digitazione.
export function listRighe(famiglia, docId, params = {}) {
  return api.get(`${base(famiglia)}/${docId}/righe/`, { params })
}

export function exportRighe(famiglia, docId, params = {}) {
  return api.get(`${base(famiglia)}/${docId}/righe/export/`, { params, responseType: 'blob' })
}

// La riga: `articolo_id` (uuid), la quantita' col nome FISICO della famiglia
// (`qta_contata` ≥ 0 | `qta_delta` ≠ 0) + `motivo` (rettifica),
// `costo_unitario` (≥ 0, nullable: vuoto = alla media corrente),
// `ubicazione_id` / `lotto_id` / `asset_id` (nullable), `meta`.
// ⛔ Il backend NON ricalcola la coerenza della riga (Q-3): il DB la accetta in
//    `DRAFT`, il piano la dichiara `NON_POSTABILE`, il form la MOSTRA con
//    `motiviRiga`. Solo in `DRAFT`: fuori, `E_MAG_DOCUMENTO_RIGHE_CONGELATE`.
export function creaRiga(famiglia, docId, payload) {
  return api.post(`${base(famiglia)}/${docId}/righe/`, payload)
}

// PATCH parziale della riga; `null` esplicito AZZERA un nullable (togliere il lotto).
export function aggiornaRiga(famiglia, docId, rigaId, payload) {
  return api.patch(`${base(famiglia)}/${docId}/righe/${rigaId}/`, payload)
}

export function eliminaRiga(famiglia, docId, rigaId) {
  return api.delete(`${base(famiglia)}/${docId}/righe/${rigaId}/`)
}

// ⭐ IL PIANO dell'inventario (solo `inventari`): che cosa il posting scrivera',
//    riga per riga, con l'`esito` e — su `NON_POSTABILE` — la coppia
//    `posting_blocco_reason` / `_reason_key` (famiglia «riga» di api.md
//    §Capability). Nessun vincolo di stato: in `DRAFT` e' un'anteprima, dopo
//    `CONFIRM` e' la fotografia contro cui si registra (D-L2-n).
export function listPiano(docId, params = {}) {
  return api.get(`${base(FAMIGLIA.INVENTARI)}/${docId}/piano/`, { params })
}

export function exportPiano(docId, params = {}) {
  return api.get(`${base(FAMIGLIA.INVENTARI)}/${docId}/piano/export/`, { params, responseType: 'blob' })
}

// ⭐ L'ANTEPRIMA DEI MOTIVI di una riga: `script.fn_check_riga_magazzino` cosi'
//    com'e' — la STESSA funzione che il piano e la primitiva usano, quindi «cio'
//    che si vede e' cio' che verra' scritto». `{motivi: [...]}`, array ordinato
//    del DB (`codice`, `reason_key`, `dettaglio`…); `[]` = nessun motivo.
//    ⚠️ Lettura best-effort per il form: non blocca il Salva (Q-3).
export function motiviRiga(params) {
  return api.get(`${BASE}/righe/motivi/`, { params })
}

// ══════════════════════════════════════════════════════════════
//  I tre lookup di riga — envelope `{"results": [...]}`
// ══════════════════════════════════════════════════════════════

// Le ubicazioni ATTIVE di un magazzino (solo se `usa_ubicazioni`).
export function lookupUbicazioni(magazzinoId) {
  return api.get(`${BASE}/magazzini/${magazzinoId}/ubicazioni/lookup/`)
}

// I lotti attivi di un articolo (solo se `requires_lotto`), con ricerca sul codice.
export function lookupLotti(articoloId, search = null) {
  const params = { articolo_id: articoloId }
  if (search) params.search = search
  return api.get(`${BASE}/lotti/lookup/`, { params })
}

// I seriali attivi di un articolo (solo se `requires_serial`), dell'emittente
// del magazzino — la RLS su `assets` fa il resto.
export function lookupAssets(articoloId, magazzinoId) {
  return api.get(`${BASE}/assets/lookup/`, {
    params: { articolo_id: articoloId, magazzino_id: magazzinoId },
  })
}

// ══════════════════════════════════════════════════════════════
//  Consultazione — la disponibilita' e il registro
// ══════════════════════════════════════════════════════════════

// La disponibilita' per (articolo, magazzino) — `vw_disponibilita`, lista
// `magazzino.disponibilita`. Filtri: `magazzino_id`, `articolo_id`,
// `solo_negativa` (disponibile < 0: le promesse non piu' mantenibili, D-L2-d),
// `solo_con_giacenza`, `search` (min 3, sotto: 400; le colonne le accende il
// catalogo della lista).
// ⚠️ La vista e' `security_invoker`: si legge con la connessione dell'utente.
export function listDisponibilita(params = {}) {
  return api.get(`${BASE}/disponibilita/`, { params })
}

export function exportDisponibilita(params = {}) {
  return api.get(`${BASE}/disponibilita/export/`, { params, responseType: 'blob' })
}

// La disponibilita' per ARTICOLO (somma sui magazzini visibili, `n_magazzini`)
// — lista `magazzino.disponibilita_articoli`, colonne sue.
export function listDisponibilitaArticoli(params = {}) {
  return api.get(`${BASE}/disponibilita/articoli/`, { params })
}

export function exportDisponibilitaArticoli(params = {}) {
  return api.get(`${BASE}/disponibilita/articoli/export/`, { params, responseType: 'blob' })
}

// I BLOCCHI di (articolo, magazzino): gli attesi `APERTA` in uscita, col
// soggetto decodificato e la nota — il drill-down di `n_blocchi` (D-L2-j).
export function listBlocchi(articoloId, magazzinoId) {
  return api.get(`${BASE}/disponibilita/blocchi/`, {
    params: { articolo_id: articoloId, magazzino_id: magazzinoId },
  })
}

// APRE un blocco manuale (Lotto 3 R-5, verbo `magazzino.fn_apri_blocco`):
// { magazzino_id, articolo_id, qta (positiva), soggetto_ruolo_id?, nota?,
// lotto_id?, asset_id?, ubicazione_id? }. Per chi (soggetto) o perche' (nota):
// lo pretende il DB. Azione `blocca_merce`.
export function apriBlocco(payload) {
  return api.post(`${BASE}/disponibilita/blocchi/`, payload)
}

// LIBERA un blocco manuale (autore, momento e nota li scrive il verbo).
export function liberaBlocco(bloccoId, nota = null) {
  return api.post(`${BASE}/disponibilita/blocchi/${bloccoId}/libera/`, { nota })
}

// IL REGISTRO dei movimenti — lista `magazzino.movimenti`, sola lettura per
// costruzione. Filtri: `magazzino_id`, `articolo_id`, `causale_id`, `data_da`/
// `data_a` (su `data_mov`), `sorgente_tipo` (`config.sorgenti.codice_interno`),
// e i due deep-link dal documento POSTED: `inventario_id` / `rettifica_id`
// (i movimenti nati dalle righe di QUEL documento), `search` (colonne dal
// catalogo; sotto 3 caratteri non filtra — la casella compare solo se il
// catalogo accende almeno una colonna, `ricerca_full`). Senza ordinamento:
// `data_mov DESC, id DESC`.
export function listMovimenti(params = {}) {
  return api.get(`${BASE}/movimenti/`, { params })
}

export function exportMovimenti(params = {}) {
  return api.get(`${BASE}/movimenti/export/`, { params, responseType: 'blob' })
}


// ══════════════════════════════════════════════════════════════
//  Le anagrafiche: magazzini, ubicazioni (figlie), lotti (dell'articolo)
//  Piano: piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config §4-6.
//  ⚠️ Nessuna azione di dominio: disattivare e' un PATCH `{attivo: false}`,
//  e il DB decide (`block_deact`).
// ══════════════════════════════════════════════════════════════

// I magazzini del perimetro — lista `magazzino.magazzini`. Filtri: `search`
// (min 3, sotto: 400; colonne dal catalogo), `attivo` (assente = tutti). Senza ordinamento:
// `codice`.
export function listMagazzini(params = {}) {
  return api.get(`${BASE}/magazzini/`, { params })
}

export function exportMagazzini(params = {}) {
  return api.get(`${BASE}/magazzini/export/`, { params, responseType: 'blob' })
}

// Dettaglio: la riga della lista (emittente e indirizzo decodificati,
// `ubicazioni_count`).
export function getMagazzino(magazzinoId) {
  return api.get(`${BASE}/magazzini/${magazzinoId}/`)
}

// ⭐ Crea: `codice`, `descrizione`, `indirizzo_dettaglio_id` (obbligatori),
//    `usa_ubicazioni`, `predefinito`. ⛔ NON `emittente_fiscale_id`: lo mette il
//    DB dall'emittente della sessione.
export function creaMagazzino(payload) {
  return api.post(`${BASE}/magazzini/`, payload)
}

// PATCH per DELTA: solo le chiavi che cambiano — il lock su `codice` scatta
// solo se il codice viaggia, il guard su `usa_ubicazioni` solo se lo si tocca.
export function aggiornaMagazzino(magazzinoId, payload) {
  return api.patch(`${BASE}/magazzini/${magazzinoId}/`, payload)
}

// Le ubicazioni di UN magazzino — lista `magazzino.ubicazioni`. Filtri:
// `search` (min 3, sotto: 400; colonne dal catalogo), `attivo`, `parent_id`.
// Senza ordinamento: `codice`.
export function listUbicazioni(magazzinoId, params = {}) {
  return api.get(`${BASE}/magazzini/${magazzinoId}/ubicazioni/`, { params })
}

export function exportUbicazioni(magazzinoId, params = {}) {
  return api.get(`${BASE}/magazzini/${magazzinoId}/ubicazioni/export/`, { params, responseType: 'blob' })
}

export function getUbicazione(magazzinoId, ubicazioneId) {
  return api.get(`${BASE}/magazzini/${magazzinoId}/ubicazioni/${ubicazioneId}/`)
}

// Crea nel magazzino del path: `codice`, `tipo_id` (obbligatori), `parent_id`
// (dello stesso magazzino, senza cicli: lo decide il DB), `descrizione`,
// `area`/`corsia`/`scaffale`/`piano`/`posizione`.
export function creaUbicazione(magazzinoId, payload) {
  return api.post(`${BASE}/magazzini/${magazzinoId}/ubicazioni/`, payload)
}

// PATCH per delta. ⛔ Non `magazzino_id`: un'ubicazione nasce nel suo magazzino.
export function aggiornaUbicazione(magazzinoId, ubicazioneId, payload) {
  return api.patch(`${BASE}/magazzini/${magazzinoId}/ubicazioni/${ubicazioneId}/`, payload)
}

// I lotti di UN articolo — lista `magazzino.lotti`. `articolo_id` OBBLIGATORIO
// (uuid): un elenco di tutti i lotti di tutti gli articoli non e' una domanda
// di nessuno. Filtri: `search` (min 3, sotto: 400; colonne dal catalogo),
// `attivo`. Senza ordinamento:
// `data_arrivo DESC`.
export function listLotti(params = {}) {
  return api.get(`${BASE}/lotti/`, { params })
}

export function exportLotti(params = {}) {
  return api.get(`${BASE}/lotti/export/`, { params, responseType: 'blob' })
}

export function getLotto(lottoId) {
  return api.get(`${BASE}/lotti/${lottoId}/`)
}

// Crea: `articolo_id`, `codice`, `data_arrivo` (obbligatori), `data_scadenza`
// (>= arrivo: lo dice il CHECK, il BE traduce).
export function creaLotto(payload) {
  return api.post(`${BASE}/lotti/`, payload)
}

// PATCH per delta. ⛔ Non `articolo_id`: un lotto nasce del suo articolo.
export function aggiornaLotto(lottoId, payload) {
  return api.patch(`${BASE}/lotti/${lottoId}/`, payload)
}
