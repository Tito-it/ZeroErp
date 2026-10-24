// Client API per il sottodominio vendite/ordini (ordini di vendita).
// URL REST standard: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: backend/apps/vendite/api/urls_ordini.py (mount in urls_v1.py: /vendite/ordini/).
//
// Scheletro (analisi-ordini-vendita.md §6): testata + righe + componenti BoM
// + conferma (DRAFT->CONFERMATO) + push singolo a commessa. Niente revisioni
// ne' listino in testata (a differenza di preventivi/offerte). Componenti BoM
// via building block condiviso `makeComponentiBomApi` (schema URL identico ai
// domini gemelli) — regola del 2, nessuna implementazione nuova.

import api from '../../../core/api'
import { makeRigheListaApi } from '../../_shared/righe/righeListaApi'
import { makeDateConsegnaApi } from '../../_shared/dateConsegna/dateConsegnaApi'
import { makeComponentiBomApi } from '../../../core/api/componentiBom'

const BASE = '/vendite/ordini'

// --- Testata CRUD ---

export function listOrdini(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Export CSV/XLSX lista configurabile (DEF-1). responseType blob: NON passare
// da useApiHandler (unwrap envelope perde header/data del file). Vedi memoria
// feedback_blob_download_no_useapihandler.
export function exportOrdini(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}

export function getOrdine(id) {
  return api.get(`${BASE}/${id}/`)
}

// Crea ordine BOZZA (DRAFT). Il numero e' generato dal trigger DB
// (trgfn_ordini_gen_codice) — non va nel payload. Payload: billing_account_id
// (o soggetto_ruolo_id), utility_id, emittente_fiscale_id, valuta_id,
// modalita_pagamento_id, termine_pagamento_id, fatturazione_trigger,
// agente_soggetto_ruolo_id, data, meta.
export function createOrdine(payload) {
  return api.post(`${BASE}/`, payload)
}

// Aggiorna testata (solo in DRAFT, guard lato BE). PATCH: il BE usa request.data.
export function updateOrdine(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Hard-delete ordine BOZZA (abbandono drawer create, solo DRAFT).
export function deleteOrdine(id) {
  return api.delete(`${BASE}/${id}/`)
}

// --- Transizioni / integrazione ---

// DRAFT -> CONFERMATO. Guard BE: origine DRAFT + almeno una riga. Endpoint di
// sola transizione: il flusso utente passa da `emettiOrdine` (/emetti/), questo
// resta come API di servizio.
export function confermaOrdine(id) {
  return api.post(`${BASE}/${id}/conferma/`, {})
}

// DRAFT -> CONFERMATO (multipart). L'endpoint `/emetti/` orchestra conferma +
// genera documento + persiste eventuali allegati in transazione atomica lato BE
// (ApiOrdineEmetti, §6 brief-ordini-stampa.md, mirror di emettiPreventivo). La
// conferma da UI passa da qui via OrdineEmissioneDialog; se la generazione
// fallisce il BE annulla la conferma (stato resta DRAFT).
export function emettiOrdine(id, { allegati = [], templateId = null } = {}) {
  const formData = new FormData()
  if (templateId != null) formData.append('template_documento_id', templateId)
  for (const file of allegati) formData.append('allegati', file)
  return api.post(`${BASE}/${id}/emetti/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Transizione di stato generica data-driven (es. annulla DRAFT->ANNULLATO).
// `statoCodice` = `target_state` dell'azione da fn_available_actions_ordine.
// L'ammissibilita' della transizione e' validata dal trigger guard DB.
// `dichiarazione`: la conferma dell'annullo di un ordine con legami
// (`{ legami_confermati }`, brief-db-annullo-documento-con-legami). Al primo
// tentativo e' vuota (`useForzaturaConfermata`).
export function cambiaStatoOrdine(id, statoCodice, dichiarazione = {}) {
  return api.post(`${BASE}/${id}/cambia-stato/`, { stato_codice: statoCodice, ...dichiarazione })
}

// Push singolo dell'ordine CONFERMATO a commessa (chiusura giro). Ritorna un
// report orchestrator { stato, push_log_id, durata_ms, handlers, righe_pushable,
// fatturazione_trigger }. Pattern push singolo gemello preventivi/offerte.
export function pushOrdineACommessa(id) {
  return api.post(`${BASE}/${id}/push/`, {})
}

// Evasione: genera un DDT (DRAFT) dall'ordine. L'endpoint vive nel dominio
// SORGENTE (ordine), la logica sta in ddt_service (gemello di
// "genera ordine da preventivo"). `righe` = [{ordine_riga_id, qta_da_evadere}]
// in unita' operativa; se null/omesso il BE evade TUTTO il residuo. La fn DB
// madre e' atomica (testata+righe+componenti+fulfillment+proiezione stato
// ordine). Ritorna { ddt_id, numero(null in DRAFT), ordine_id }.
export function generaDdtFromOrdine(ordineId, righe = null) {
  const body = righe && righe.length ? { righe } : {}
  return api.post(`${BASE}/${ordineId}/genera-ddt/`, body)
}

// Risolve l'ordine COLLEGATO a una pratica (agganciato dallo smistamento). Usato
// dagli step pratica a valle (CONFERMA_ORDINE / INVIO_COMMESSA) per aprire
// l'OrdiniDrawer sull'ordine giusto. Ritorna { ordine_id: <id|null> }.
export function getOrdinePerPratica(praticaId) {
  return api.get(`${BASE}/per-pratica/`, { params: { pratica_id: praticaId } })
}

// --- Righe ---

// La LISTA configurabile delle righe (pagina + export, `…/righe/lista/`):
// factory condivisa coi documenti gemelli. `listRighe` qui sotto resta la
// lettura COMPLETA (dialog, stampe).
export const { listRigheLista, exportRigheLista } = makeRigheListaApi(BASE)
// «Aggiorna date di consegna» (brief-db-date-consegna-righe-in-blocco).
export const { aggiornaDateConsegna } = makeDateConsegnaApi(BASE)

export function listRighe(ordineId) {
  return api.get(`${BASE}/${ordineId}/righe/`)
}

export function createRiga(ordineId, payload) {
  return api.post(`${BASE}/${ordineId}/righe/`, payload)
}

export function updateRiga(ordineId, rigaId, payload) {
  return api.patch(`${BASE}/${ordineId}/righe/${rigaId}/`, payload)
}

export function deleteRiga(ordineId, rigaId) {
  return api.delete(`${BASE}/${ordineId}/righe/${rigaId}/`)
}

// La promessa di consegna di UNA riga, anche dopo la conferma (verbo dedicato,
// brief-db-testata-dopo-emissione fase 1). `data` = 'AAAA-MM-GG' oppure null,
// che toglie la promessa. In quali stati si puo' lo dice il DB.
export function cambiaDataConsegnaConfermata(ordineId, rigaId, data) {
  return api.post(
    `${BASE}/${ordineId}/righe/${rigaId}/data-consegna-confermata/`,
    { data_consegna_confermata: data },
  )
}

// --- Riepilogo IVA ---

// Riepilogo IVA aggregato dell'ordine (una riga per aliquota, regola fiscale
// DPR 633/72 art. 21). Calcolo gia' eseguito in DB dalla vista derivata
// vw_ordini_riepilogo_iva_dettaglio (stessa formula dei preventivi): il FE
// legge solo lo stato corrente, sempre coerente con le righe attive.
// Risposta: array di { iva_id, iva_codice, iva_descrizione, iva_aliquota,
//   imponibile, imposta, arrotondamento, totale_riga }.
export function getRiepilogoIva(ordineId) {
  return api.get(`${BASE}/${ordineId}/riepilogo-iva/`)
}

// --- Componenti BoM CASO A ---
// Schema REST identico a preventivi/contratti: i 4 metodi vengono dal building
// block `makeComponentiBomApi` (core/api/componentiBom.js), qui solo bindati al
// path base ordini e ri-esportati con gli stessi nomi. Init componenti avviene
// lato BE in gestisci_riga quando l'articolo e' composito.
const _componentiApi = makeComponentiBomApi(BASE)
export const previewRigaComponenti = _componentiApi.previewRigaComponenti
export const listRigaComponenti = _componentiApi.listRigaComponenti
export const updateRigaComponente = _componentiApi.updateRigaComponente
export const deleteRigaComponente = _componentiApi.deleteRigaComponente
