// Client API per il sottodominio vendite/preventivi.
// URL REST standard: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: backend/apps/vendite/api/preventivi_urls.py

import api from '../../../core/api'
import { makeRigheListaApi } from '../../_shared/righe/righeListaApi'
import { makeDateConsegnaApi } from '../../_shared/dateConsegna/dateConsegnaApi'
import { makeComponentiBomApi } from '../../../core/api/componentiBom'

const BASE = '/vendite/preventivi'

// --- Testata CRUD ---

export function listPreventivi(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Export CSV/XLSX lista configurabile (DEF-1). responseType blob: NON passare
// da useApiHandler (unwrap envelope perde header/data del file). Vedi memoria
// feedback_blob_download_no_useapihandler.
export function exportPreventivi(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}

export function getPreventivo(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createPreventivo(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updatePreventivo(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Hard-delete preventivo BOZZA orfano (zero righe, zero pratiche).
// Usato dal flusso "abbandono bozza" del drawer create. Per stati avanzati
// usare invece cambiaStatoPreventivo(id, {nuovo_stato: 'ANNULLATO'}).
export function deletePreventivo(id) {
  return api.delete(`${BASE}/${id}/`)
}

// --- Azioni testata ---

export function cambiaStatoPreventivo(id, payload) {
  return api.post(`${BASE}/${id}/stato/`, payload)
}

// GUIDA (D4): cambia stato del preventivo ROOT risolto dalla pratica — «Accetta/
// Rifiuta» in-pratica (inversione handler→proiezione). Il BE risolve il preventivo
// dal pratica_id; il milestone avanza da solo via trigger DB. Stesso payload di
// cambiaStatoPreventivo ({nuovo_stato, fatturazione_immediata?, competenza_mese?}).
export function cambiaStatoPreventivoDaPratica(praticaId, payload) {
  return api.post(`${BASE}/da-pratica/${praticaId}/stato/`, payload)
}

// BOZZA -> EMESSO. L'endpoint (multipart) cambia stato + genera documento +
// persiste eventuali allegati in transazione atomica lato BE (mirror del
// flusso offerta). NB: la transizione *->EMESSO NON passa piu' da
// cambiaStatoPreventivo (refactor 2026-05-28): usare questa funzione tramite
// PreventivoEmissioneDialog.
export function emettiPreventivo(id, { allegati = [], templateId = null } = {}) {
  const formData = new FormData()
  if (templateId != null) formData.append('template_documento_id', templateId)
  for (const file of allegati) formData.append('allegati', file)
  return api.post(`${BASE}/${id}/emetti/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function creaRevisione(id) {
  return api.post(`${BASE}/${id}/revisione/`, {})
}

// Smistamento MERCE → ordine (modello split D8): righe merce non ancora
// allocate, da mostrare nel dialog di selezione.
export function listRigheSmistabiliOrdine(id) {
  return api.get(`${BASE}/${id}/righe-smistabili-ordine/`)
}

// Smistamento MERCE → ordine: crea un ordine DRAFT dalle righe merce scelte.
// `righeIds` opzionale: assente/null = tutte le righe merce residue.
export function generaOrdineFromPreventivo(id, righeIds = null) {
  const body = righeIds && righeIds.length ? { righe_ids: righeIds } : {}
  return api.post(`${BASE}/${id}/genera-ordine/`, body)
}

// Catena revisioni del preventivo, PAGINATA (lista a catalogo
// `vendite.preventivo_revisioni`): `params` porta pagina, ordinamento e
// `emittente_fiscale_id` del documento (lo legge il cancello di perimetro).
export function listRevisioni(id, params = {}) {
  return api.get(`${BASE}/${id}/revisioni/`, { params })
}

// --- Righe ---

// La LISTA configurabile delle righe (pagina + export, `…/righe/lista/`):
// factory condivisa coi documenti gemelli. ⚠️ Nessuna lettura COMPLETA delle
// righe qui: il FE non ne ha consumatori (a differenza di ordine e reso, per
// i dialog di evasione e ri-consegna). `GET …/righe/` resta lato backend.
export const { listRigheLista, exportRigheLista } = makeRigheListaApi(BASE)
// «Aggiorna date di consegna» (brief-db-date-consegna-righe-in-blocco).
export const { aggiornaDateConsegna } = makeDateConsegnaApi(BASE)

export function createRiga(preventivoId, payload) {
  return api.post(`${BASE}/${preventivoId}/righe/`, payload)
}

export function updateRiga(preventivoId, rigaId, payload) {
  return api.patch(`${BASE}/${preventivoId}/righe/${rigaId}/`, payload)
}

export function deleteRiga(preventivoId, rigaId) {
  return api.delete(`${BASE}/${preventivoId}/righe/${rigaId}/`)
}

// Suggerisce il prezzo riga via pricing resolver v5. Il BE deriva BA, utility
// e data riferimento dal preventivo; al FE basta passare articolo_id + uom_id.
// Risposta: { prezzo_finale, prezzo_base_snapshot, origine, listino_id,
//   contratto_id, promo_id, tipo_variazione_applicata, valore_variazione_applicata }.
// Lettura pura, senza side-effect.
export function suggerisciPrezzoRiga(preventivoId, payload) {
  return api.post(`${BASE}/${preventivoId}/righe/suggerisci-prezzo/`, payload)
}

// Riepilogo IVA aggregato del preventivo (una riga per aliquota IVA, regola
// fiscale DPR 633/72 art. 21). Calcolo gia' eseguito in DB e mantenuto da
// trigger AFTER su preventivi_righe: il FE legge solo lo stato corrente.
// Risposta: array di { iva_id, iva_codice, iva_descrizione, iva_aliquota,
//   imponibile, imposta, arrotondamento, totale_riga, ... }.
export function getRiepilogoIva(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/riepilogo-iva/`)
}

// Contesto pricing: contratto attivo o listino categoria fallback.
// Risposta: { fonte: 'CONTRATTO'|'CATEGORIA'|'NONE',
//   contratto_id, contratto_numero, listino_id, listino_codice,
//   listino_descrizione, categoria_cliente_codice, ... }.
// Usato dall'header del drawer preventivo per audit visivo path resolver.
export function getContestoPricing(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/contesto-pricing/`)
}

// --- Componenti BoM CASO A (refactor componenti 2026-05-11) ---
// Ogni componente esposto in fattura della riga padre composita CASO A diventa
// una riga negoziabile a se stante. Init implicito post-create_riga via
// gestisci_riga BE — niente POST pubblico dedicato.
// Il prezzo della riga padre e' SUM(componenti × coeff_qta), ricalcolato dai
// trigger DB a ogni mutazione del componente.
// Schema REST identico a contratti: i 4 metodi vengono dal building block
// `makeComponentiBomApi` (core/api/componentiBom.js), qui solo bindati al
// path base preventivi e ri-esportati con gli stessi nomi.
const _componentiApi = makeComponentiBomApi(BASE)
export const previewRigaComponenti = _componentiApi.previewRigaComponenti
export const listRigaComponenti = _componentiApi.listRigaComponenti
export const updateRigaComponente = _componentiApi.updateRigaComponente
export const deleteRigaComponente = _componentiApi.deleteRigaComponente

// --- Indirizzi ---
// Gestiti dal BB condiviso `makeIndirizziDocumentoApi` (_shared/indirizzi):
// nessun client dedicato qui (schema REST identico sui 5 domini).

// --- Integrazione ---

// Idempotency-Key obbligatoria lato BE (`require_idempotency_key=True` su
// preventivi_views.py): push-commessa e' write-once, evitare doppio push
// in caso di retry/click ripetuto. `righeIds` opzionale: sottoinsieme righe
// servizio (smistamento selettivo dal Pannello Smistamento); assente = tutte.
export function pushCommessa(preventivoId, righeIds = null) {
  const body = righeIds && righeIds.length ? { righe_ids: righeIds } : {}
  return api.post(
    `${BASE}/${preventivoId}/push-commessa/`,
    body,
  )
}

// Smistamento del preventivo (Pannello Smistamento): aggregato per ramo +
// righe con natura, destinazione e stato autorevole. Sostituisce il vecchio
// /stato-fatturazione/ (viste DB natura-aware, 2026-06-12).
// Risposta: { aggregato: { righe_totali, righe_merce, righe_servizi,
//   righe_a_ordine, righe_in_commessa, righe_emesse_af, righe_fatturate,
//   righe_residue }, righe: [{ riga_id, riga_descrizione, articolo_codice,
//   destinazione_tipo, stato_smistamento, ordine_id, ordine_numero, ... }] }.
export function getSmistamento(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/smistamento/`)
}

// Completa lo step SMISTAMENTO della pratica agganciata al preventivo. L'esito di
// RAMO (MERCE_PRESENTE/SOLO_SERVIZI) e' CALCOLATO dal BE dallo split gia' eseguito
// nel Pannello — l'operatore NON lo sceglie (il FE sopprime il picker). Guard BE:
// smistamento completo su entrambi i rami (nessun residuo). Idempotency-Key:
// completamento write-once, evita doppia esecuzione su retry/doppio click.
// Ritorna { flusso_id, esito, gia_completato }.
export function completaSmistamento(preventivoId) {
  return api.post(
    `${BASE}/${preventivoId}/completa-smistamento/`,
    {},
  )
}

// Idempotency-Key obbligatoria lato BE (`require_idempotency_key=True`):
// la generazione pratica e' write-once, evita doppia pratica su retry.
export function generaPratica(preventivoId, payload) {
  return api.post(
    `${BASE}/${preventivoId}/genera-pratica/`,
    payload,
  )
}

// PREVENTIVAZIONE (percorso pratica-first): aggancia il preventivo come ROOT a
// una pratica. Idempotente. Fonte di verita' del legame preventivo↔pratica.
export function collegaPratica(preventivoId, payload) {
  return api.post(`${BASE}/${preventivoId}/collega-pratica/`, payload)
}

// Riapertura pratica-first: risolve il preventivo ROOT gia' agganciato a un
// flusso (aggancio per-flusso). Ritorna { preventivo_id: <id|null> }. Usato
// dall'attivita' UI "apri preventivo" per riaprire il ROOT di quel flusso in
// edit invece di crearne uno nuovo.
export function getRootPerFlusso(flussoId) {
  return api.get(`${BASE}/root-per-flusso/`, { params: { flusso_id: flussoId } })
}

// Risolve il preventivo ROOT della PRATICA (non per-flusso): usato dagli step a
// valle del percorso (es. SMISTAMENTO) che operano sul preventivo agganciato a
// monte. Ritorna { preventivo_id: <id|null> }.
export function getRootPerPratica(praticaId) {
  return api.get(`${BASE}/root-per-pratica/`, { params: { pratica_id: praticaId } })
}
