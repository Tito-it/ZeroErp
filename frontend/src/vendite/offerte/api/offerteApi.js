// Client API per il sottodominio vendite/offerte commerciali.
// URL REST: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: backend/apps/vendite/api/urls_offerte.py (mount in urls_v1.py: /vendite/offerte/).

import api from '../../../core/api'
import { makeRigheListaApi } from '../../_shared/righe/righeListaApi'
import { makeRigaErogazioniApi } from '../../_shared/righe/erogazioniRigaApi'

const BASE = '/vendite/offerte'

// --- Testata CRUD ---

export function listOfferte(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Export CSV/XLSX lista configurabile (DEF-1). responseType blob: NON passare
// da useApiHandler (unwrap envelope perde header/data). Vedi memoria
// feedback_blob_download_no_useapihandler.
export function exportOfferte(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}

export function getOfferta(id) {
  return api.get(`${BASE}/${id}/`)
}

// Crea offerta BOZZA. Il codice OFC-* e' generato dal trigger DB (Step 5
// brief): non va inviato nel payload (la whitelist BE lo rifiuta come unknown_key).
// Payload richiesto: emittente_fiscale_id, billing_account_id, istanza_utility_id,
// utility_id, listino_id, validita_dal. Opzionali: listino_versione_id,
// valore_variazione_globale, tipo_variazione_globale (solo PERCENTUALE),
// validita_al, meta.
export function createOfferta(payload) {
  return api.post(`${BASE}/`, payload)
}

// Aggiorna testata (solo in BOZZA, guard lato BE).
export function updateOfferta(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Hard-delete offerta BOZZA orfana (drawer create abbandono).
// Per annullare un'offerta gia' BOZZA con motivazione di processo usare
// `annullaOfferta` (BOZZA o ACCETTATA -> ANNULLATA).
export function deleteOfferta(id) {
  return api.delete(`${BASE}/${id}/`)
}

// --- Transizioni di stato ---

// BOZZA -> EMESSA. L'endpoint (multipart) emette + genera il documento +
// persiste gli eventuali allegati in una transazione atomica lato BE.
// `allegati` = array di File (opzionale); `templateId` opzionale (default
// = template predefinito per OFFERTA_COMMERCIALE/emittente). Validazioni di
// stato/versione nel trigger DB; mancanza template -> emissione fallisce.
export function emettiOfferta(id, { allegati = [], templateId = null } = {}) {
  const formData = new FormData()
  if (templateId != null) formData.append('template_documento_id', templateId)
  for (const file of allegati) formData.append('allegati', file)
  return api.post(`${BASE}/${id}/emetti/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// EMESSA -> ACCETTATA o RIFIUTATA. Motivazione obbligatoria su RIFIUTATA: lo
// dice la riga del passaggio, al verbo DB (E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA).
// Su ACCETTATA niente motivazione: una non vuota e' un 400 col campo.
export function registraEsitoOfferta(id, { esito, motivazione }) {
  return api.post(`${BASE}/${id}/registra-esito/`, {
    esito,
    motivazione: motivazione || '',
  })
}

// BOZZA o ACCETTATA -> ANNULLATA (ritiro da noi). Motivazione obbligatoria.
// Non e' ammesso annullare da EMESSA (state machine asimmetrica: dopo
// l'emissione, o accetta il cliente o rifiuta, o si riemette come revisione).
// `dichiarazione`: la conferma dell'annullo di una revisione, che fa tornare
// emessa la precedente (`{ legami_confermati }`, brief-modello-documento-vendita
// §13, O-4). Al primo tentativo e' vuota (`useForzaturaConfermata`).
export function annullaOfferta(id, { motivazione, dichiarazione = {} }) {
  return api.post(`${BASE}/${id}/annulla/`, { motivazione, ...dichiarazione })
}

// --- Revisioni ---

// EMESSA -> crea rev.N+1 (BOZZA). La fn DB copia testata + eccezioni attive +
// utility 1:1 e marca la rev.N corrente come SUPERATA via trigger AFTER INSERT.
export function creaRevisioneOfferta(id) {
  return api.post(`${BASE}/${id}/crea-revisione/`, {})
}

// Conversione upstream (§7.4): genera un ordine di vendita DRAFT da un'offerta
// ACCETTATA (righe espanse listino+eccezioni + componenti + documento_origine).
export function generaOrdineFromOfferta(id) {
  return api.post(`${BASE}/${id}/genera-ordine/`, {})
}

// Catena revisioni che condividono la radice, PAGINATA (lista a catalogo
// `vendite.offerta_revisioni`): `params` porta pagina, ordinamento e
// `emittente_fiscale_id` del documento (lo legge il cancello di perimetro).
// Lettura libera in ogni stato.
export function listRevisioniOfferta(id, params = {}) {
  return api.get(`${BASE}/${id}/revisioni/`, { params })
}

// --- Push a contratto ---

// ACCETTATA -> contratto DRAFT (Step 8 brief). Idempotente per costruzione:
// doppia invocazione fallisce con E_OFFERTA_CONTRATTO_GIA_GENERATO.
// `praticaId` opzionale: se valorizzato, il contratto viene collegato come
// sorgente di una pratica esistente.
// `chiudiEsistente` (brief successione 2026-05-31): se true e c'e' un
// contratto sovrapposto, lo chiude per successione (valido_al = nuovo
// valido_dal - 1) e crea il nuovo; se false (default), su overlap il BE
// solleva E_CONTRATTO_OVERLAP_ESISTENTE.
// Risposta: { contratto_id, contratto_codice, sorgente_uid }.
export function pushOffertaAContratto(
  id, { praticaId = null, chiudiEsistente = false } = {},
) {
  const body = {}
  if (praticaId != null) body.pratica_id = praticaId
  if (chiudiEsistente) body.chiudi_esistente = true
  return api.post(`${BASE}/${id}/push-contratto/`, body)
}

// Pre-check overlap (brief successione §3.2.1): contratto attivo la cui
// validita' si sovrappone a quella che il push genererebbe per l'offerta.
// Read-only: alimenta il dialog di successione dopo
// E_CONTRATTO_OVERLAP_ESISTENTE. Risposta: { contratto: {...}|null }.
export function getContrattoSovrapposto(id) {
  return api.get(`${BASE}/${id}/contratto-sovrapposto/`)
}

// --- Righe: la LISTA configurabile (`vendite.offerta_righe`, 106) ---
// Pagina + export su `…/righe/lista/`: le righe OPERATIVE dell'offerta, cioe'
// `vendite.fn_offerta_righe_preview` — listino con le eccezioni sopra, piu' le
// aggiunte, coi verbi del DB — come il contratto (brief-db-righe-esclusione-
// solo-non-si-vende §8.1, 2026-10-05). ⚠️ `GET …/eccezioni/` (le eccezioni
// scritte) non ha piu' un consumatore qui: il drawer legge la lista, il
// dettaglio dell'offerta porta gia' le eccezioni (note, conteggio).
export const { listRigheLista, exportRigheLista } = makeRigheListaApi(BASE)

// Come si puo' erogare un articolo su una riga dell'offerta: le combinazioni
// (erogazione, fonte) ammesse, il default in testa (BB `makeRigaErogazioniApi`).
export const { listRigaErogazioni } = makeRigaErogazioniApi(BASE)

// --- Eccezioni (scritture, solo BOZZA) ---

export function createEccezione(offertaId, payload) {
  return api.post(`${BASE}/${offertaId}/eccezioni/`, payload)
}

export function updateEccezione(offertaId, eccezioneId, payload) {
  return api.patch(`${BASE}/${offertaId}/eccezioni/${eccezioneId}/`, payload)
}

export function deleteEccezione(offertaId, eccezioneId) {
  return api.delete(`${BASE}/${offertaId}/eccezioni/${eccezioneId}/`)
}

// --- Componenti BoM eccezione (mirror contratti, simmetria 2026-05-26) ---
// Pattern speculare a `previewRigaComponenti`/`listRigaComponenti`/
// `updateRigaComponente`/`deleteRigaComponente` di `contratti.js`. Init
// componenti BoM avviene lato BE in `crea_eccezione` quando l'articolo
// e' composito; il payload puo' includere `componenti_overrides` (delta
// prezzi diversi dal suggerito) per pre-impostare prezzi manuali al
// momento della create.

// Preview componenti pre-save: ritorna i figli BoM con `prezzo_suggerito`
// dal resolver bundle-aware. Consumato da `ComponentiDialog` PRIMA del
// save di un'eccezione padre composita.
// Payload: { articolo_id, uom_operativa_id, quantita }.
export function previewEccezioneComponenti(offertaId, payload) {
  return api.post(
    `${BASE}/${offertaId}/eccezioni/preview-componenti/`,
    payload,
  )
}

// `soloAttivi=true` default backcompat. EDIT panel passa false per
// includere opzionali disattivati e permettere il toggle di riattivazione.
export function listEccezioneComponenti(offertaId, eccezioneId, { soloAttivi = true } = {}) {
  const params = soloAttivi ? {} : { solo_attivi: 'false' }
  return api.get(
    `${BASE}/${offertaId}/eccezioni/${eccezioneId}/componenti/`,
    { params },
  )
}

// PATCH singolo componente: `prezzo_unitario`, `attivo`, `meta` e basta
// (`COMPONENTE_PATCH_OPERATORE` del backend). L'origine del prezzo la scrive
// il server; IVA e campi del workflow L3 sono un 400.
export function updateEccezioneComponente(offertaId, eccezioneId, componenteId, payload) {
  return api.patch(
    `${BASE}/${offertaId}/eccezioni/${eccezioneId}/componenti/${componenteId}/`,
    payload,
  )
}

// Soft delete componente: il trigger DB ricalcola il prezzo della
// eccezione padre.
export function deleteEccezioneComponente(offertaId, eccezioneId, componenteId) {
  return api.delete(
    `${BASE}/${offertaId}/eccezioni/${eccezioneId}/componenti/${componenteId}/`,
  )
}

// --- Utility 1:1 (CRUD, solo BOZZA in write) ---

// La utility e' un record 1:1 con la testata offerta: gli endpoint usano il
// pattern collezione per coerenza con `contratti_utilities` (vedi piano
// BE+FE §3.4 C2). Read libero, write solo in BOZZA.
export function getOffertaUtility(offertaId) {
  return api.get(`${BASE}/${offertaId}/utility/`)
}

export function createOffertaUtility(offertaId, payload) {
  return api.post(`${BASE}/${offertaId}/utility/`, payload)
}

export function updateOffertaUtility(offertaId, utilityId, payload) {
  return api.patch(`${BASE}/${offertaId}/utility/${utilityId}/`, payload)
}
