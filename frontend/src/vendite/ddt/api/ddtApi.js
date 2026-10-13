// Client API per il sottodominio vendite/ddt (documenti di trasporto di vendita).
// URL REST standard: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: backend/apps/vendite/api/urls_ddt.py (mount in urls_v1.py: /vendite/ddt/).
//
// Clone strutturale di ordiniApi (analisi-ddt-vendita §D-4): testata + righe +
// componenti BoM + emissione (DRAFT->EMESSO, assegna numero) + cambio stato
// data-driven + push singolo a commessa (fatturazione differita). L'evasione
// (genera DDT da ordine) vive nel dominio SORGENTE (ordine), non qui.
// Componenti BoM via building block condiviso `makeComponentiBomApi` (schema URL
// identico ai domini gemelli) — regola del 2, nessuna implementazione nuova.
//
// Fuori scope di questa slice (nessun endpoint BE): indirizzi (in attesa del
// brief DB). I documenti PDF (anteprima/genera/lista/download)
// passano dal client condiviso `ddtDocumenti`
// (documenti/api/documentiPerSorgente.js), non da qui.

import api from '../../../core/api'
import { makeRigheListaApi } from '../../_shared/righe/righeListaApi'
import { makeComponentiBomApi } from '../../../core/api/componentiBom'

const BASE = '/vendite/ddt'

// --- Testata CRUD ---

export function listDdt(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Export CSV/XLSX della lista (DEF-1). `params.formato` = 'csv'|'xlsx' + gli
// stessi filtri della lista. responseType blob (download gestito dal caller).
export function exportDdt(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}

export function getDdt(id) {
  return api.get(`${BASE}/${id}/`)
}

// Crea DDT standalone BOZZA (DRAFT). Il numero NON va nel payload: lo assegna il
// trigger DB (trgfn_ddt_gen_numero_emesso) solo alla transizione a EMESSO.
// Payload testata: le chiavi di `CREATE_KEYS_DDT` del service (cliente,
// destinatario, emittente, trasporto, data, meta, ...): la utility la deriva il
// DB dal cliente, il destinatario non indicato lo propone il DB.
export function createDdt(payload) {
  return api.post(`${BASE}/`, payload)
}

// Aggiorna testata. PATCH: il BE usa request.data. Quali campi si cambiano in
// quale stato lo decide il lock di testata del DB (cliente e destinatario solo in
// bozza: E_DDT_CLIENTE_IMMUTABILE); a video lo dice la capability.
export function updateDdt(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Hard-delete DDT BOZZA orfano (abbandono drawer create, solo DRAFT + 0 righe).
export function deleteDdt(id) {
  return api.delete(`${BASE}/${id}/`)
}

// --- Transizioni / integrazione ---

// DRAFT -> EMESSO (multipart). L'endpoint `/emetti/` orchestra emissione (il
// trigger DB assegna il `numero` + gate componenti BoM) + genera documento
// accompagnatorio + persiste eventuali allegati in transazione atomica lato BE
// (ApiDdtEmetti in ddt_documenti_views, mirror di emettiOrdine). L'emissione da
// UI passa da qui via DdtEmissioneDialog; se la generazione fallisce il BE
// annulla l'emissione (stato resta DRAFT, numero non consumato).
export function emettiDdt(id, { allegati = [], templateId = null } = {}) {
  const formData = new FormData()
  if (templateId != null) formData.append('template_documento_id', templateId)
  for (const file of allegati) formData.append('allegati', file)
  return api.post(`${BASE}/${id}/emetti/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Transizione di stato generica data-driven (SPEDITO / CONSEGNATO / RESO /
// ANNULLATO). `statoCodice` = `target_state` dell'azione da
// script.fn_available_actions_ddt. L'ammissibilita' e' validata dal trigger
// guard DB trgfn_ddt_guard_transizione.
// `dichiarazione`: la conferma dell'annullo di una bolla con legami
// (`{ legami_confermati }`, brief-db-annullo-documento-con-legami). Al primo
// tentativo e' vuota (`useForzaturaConfermata`).
export function cambiaStatoDdt(id, statoCodice, dichiarazione = {}) {
  return api.post(`${BASE}/${id}/cambia-stato/`, { stato_codice: statoCodice, ...dichiarazione })
}

// Push singolo del DDT a commessa (chiusura giro, fatturazione differita,
// sorgente DDT_VENDITA). Ritorna un report orchestrator { stato, push_log_id,
// durata_ms, handlers, commesse_ids, righe_pushable }. Pattern push singolo
// gemello ordini/preventivi/offerte.
export function pushDdtACommessa(id) {
  return api.post(`${BASE}/${id}/push/`, {})
}

// Scopo: Riepilogo IVA aggregato del DDT (una entry per aliquota, regola
// fiscale DPR 633/72 art. 21). Calcolo gia' eseguito in DB dalla vista
// derivata vw_ddt_riepilogo_iva_dettaglio (stessa formula di preventivi e
// ordini; righe con prezzo NULL escluse in vista: DDT solo di trasporto ->
// riepilogo vuoto). Risposta: array di { iva_id, iva_codice, iva_descrizione,
//   iva_aliquota, imponibile, imposta, arrotondamento, totale_riga }.
export function getRiepilogoIva(ddtId) {
  return api.get(`${BASE}/${ddtId}/riepilogo-iva/`)
}

// --- Righe ---

// La LISTA configurabile delle righe (pagina + export, `…/righe/lista/`):
// factory condivisa coi documenti gemelli. ⚠️ Nessuna lettura COMPLETA delle
// righe qui: il FE non ne ha consumatori (a differenza di ordine e reso, per
// i dialog di evasione e ri-consegna). `GET …/righe/` resta lato backend.
export const { listRigheLista, exportRigheLista } = makeRigheListaApi(BASE)

export function createRiga(ddtId, payload) {
  return api.post(`${BASE}/${ddtId}/righe/`, payload)
}

export function updateRiga(ddtId, rigaId, payload) {
  return api.patch(`${BASE}/${ddtId}/righe/${rigaId}/`, payload)
}

export function deleteRiga(ddtId, rigaId) {
  return api.delete(`${BASE}/${ddtId}/righe/${rigaId}/`)
}

// Scopo: Corregge la quantita' evasa di una riga legata a un ordine o a un reso
// (verbo DB, D-2): riga, legami e stato dell'ordine cambiano insieme. Ritorna
// { ddt_id, riga_id, qta_evasa } (unita' base).
export function correggiQtaEvasa(ddtId, rigaId, qtaOperativa) {
  return api.post(`${BASE}/${ddtId}/righe/${rigaId}/qta-evasa/`, { qta_operativa: qtaOperativa })
}

// --- Prelievi: da dove esce la merce (Lotto 3 R-2b) ---
// La situazione della bolla: { muove_merce, magazzino_id, magazzino_usa_ubicazioni,
// magazzino_arrivo_id, magazzino_arrivo_usa_ubicazioni, voci: [{ ddt_riga_id,
// ddt_riga_componente_id, riga_nr, articolo_*, requires_lotto, requires_serial,
// uom_codice, qta, prelevata, automatico, prelievi: [...] }] } (quantita' in UoM base).
export function getPrelievi(ddtId) {
  return api.get(`${BASE}/${ddtId}/prelievi/`)
}

// Payload: qta (obbligatoria), ddt_riga_componente_id (voce di un kit), lotto_id,
// asset_id, ubicazione_id, ubicazione_arrivo_id. Le regole le applica il DB.
export function createPrelievo(ddtId, rigaId, payload) {
  return api.post(`${BASE}/${ddtId}/righe/${rigaId}/prelievi/`, payload)
}

export function updatePrelievo(ddtId, rigaId, prelievoId, payload) {
  return api.patch(`${BASE}/${ddtId}/righe/${rigaId}/prelievi/${prelievoId}/`, payload)
}

export function deletePrelievo(ddtId, rigaId, prelievoId) {
  return api.delete(`${BASE}/${ddtId}/righe/${rigaId}/prelievi/${prelievoId}/`)
}

// --- Componenti BoM CASO A ---
// Schema REST identico ai domini gemelli: i 4 metodi vengono dal building block
// `makeComponentiBomApi` (core/api/componentiBom.js), qui solo bindati al path
// base DDT e ri-esportati con gli stessi nomi. Init componenti avviene lato BE
// in gestisci_riga quando l'articolo e' composito.
const _componentiApi = makeComponentiBomApi(BASE)
export const previewRigaComponenti = _componentiApi.previewRigaComponenti
export const listRigaComponenti = _componentiApi.listRigaComponenti
export const updateRigaComponente = _componentiApi.updateRigaComponente
export const deleteRigaComponente = _componentiApi.deleteRigaComponente
