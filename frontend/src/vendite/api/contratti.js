// Client API contratti v5 (testata + righe + utility 1:1 + cambio stato).
// Endpoint: /vendite/contratti/ (vedi docs/it/backend/vendite/manual/api_contratti.md).

import api from '../../core/api'
import { makeComponentiBomApi } from '../../core/api/componentiBom'
import { makeRigheListaApi } from '../_shared/righe/righeListaApi'
import { makeRigaErogazioniApi } from '../_shared/righe/erogazioniRigaApi'

const BASE = '/vendite/contratti'

// Testata
export function listContratti(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Export CSV/Excel (DEF-1). Stessi filtri della lista; `responseType: blob`
// per il download. Il param `formato` (italiano) evita il magic `format` DRF.
export function exportContratti(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}

export function getContratto(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createContratto(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateContratto(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Cambio stato. `validoAl` opzionale (formato ISO YYYY-MM-DD): se presente,
// il BE applica anche PATCH valido_al nella stessa transazione (caso d'uso:
// dialog "Cessa contratto" che chiede la data di cessazione al click).
// NB refactor 2026-05-28: DRAFT->ATTIVO NON passa piu' da qui — usare
// `emettiContratto()` (orchestra atomic state + documento + allegati via
// ContrattoEmissioneDialog). Il BE rifiuterebbe E_VENDITE_VALIDAZIONE.
// `dichiarazione`: la conferma dell'annullo di un contratto con legami
// (`{ legami_confermati }`, brief-db-annullo-documento-con-legami). Al primo
// tentativo e' vuota (`useForzaturaConfermata`).
export function cambiaStatoContratto(id, codiceInterno, { validoAl = null, dichiarazione = {} } = {}) {
  const payload = { codice_interno: codiceInterno, ...dichiarazione }
  if (validoAl) payload.valido_al = validoAl
  return api.post(`${BASE}/${id}/cambia-stato/`, payload)
}

// DRAFT -> ATTIVO (multipart). Cambia stato + genera documento + persiste
// eventuali allegati in transazione atomica lato BE (mirror del flusso
// offerta/preventivo). Invocata dal ContrattoEmissioneDialog.
export function emettiContratto(id, { allegati = [], templateId = null } = {}) {
  const formData = new FormData()
  if (templateId != null) formData.append('template_documento_id', templateId)
  for (const file of allegati) formData.append('allegati', file)
  return api.post(`${BASE}/${id}/emetti/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Righe
export function addRigaContratto(contrattoId, payload) {
  return api.post(`${BASE}/${contrattoId}/righe/`, payload)
}

// La LISTA configurabile delle righe (`vendite.contratto_righe`, pagina +
// export, `…/righe/lista/`): le righe OPERATIVE del contratto, cioe'
// `vendite.fn_contratto_righe_preview` — listino con le eccezioni sopra, piu'
// le aggiunte — per le due forme (brief-db-liste-righe-documento, lotto D).
export const { listRigheLista, exportRigheLista } = makeRigheListaApi(BASE)

// Come si puo' erogare un articolo su una riga del contratto: le combinazioni
// (erogazione, fonte) ammesse, il default in testa (BB `makeRigaErogazioniApi`).
export const { listRigaErogazioni } = makeRigaErogazioniApi(BASE)

// Contesto pricing contratto (FE 2.2): forma, listino + versione fissata
// (post-attivazione) o corrente (DRAFT), variazione, categoria cliente.
// Lettura informativa per il banner header drawer righe.
export function getContrattoContestoPricing(contrattoId) {
  return api.get(`${BASE}/${contrattoId}/contesto-pricing/`)
}

export function updateRigaContratto(contrattoId, rigaId, payload) {
  return api.patch(`${BASE}/${contrattoId}/righe/${rigaId}/`, payload)
}

export function deleteRigaContratto(contrattoId, rigaId) {
  return api.delete(`${BASE}/${contrattoId}/righe/${rigaId}/`)
}

// --- Componenti BoM riga contratto (modello unificato 2026-05-13) ---
// Specchio simmetrico dei 4 endpoint preventivi. Auto-init dei componenti
// avviene lato BE in `addRigaContratto` quando l'articolo e' composito;
// il payload può includere `componenti_overrides` (delta dei prezzi diversi
// dal suggerito) per pre-impostare prezzi manuali al momento della create.
// Schema REST identico a preventivi: i 4 metodi vengono dal building block
// `makeComponentiBomApi` (core/api/componentiBom.js), qui solo bindati al
// path base contratti e ri-esportati con gli stessi nomi.
const _componentiApi = makeComponentiBomApi(BASE)
export const previewRigaComponenti = _componentiApi.previewRigaComponenti
export const listRigaComponenti = _componentiApi.listRigaComponenti
export const updateRigaComponente = _componentiApi.updateRigaComponente
export const deleteRigaComponente = _componentiApi.deleteRigaComponente
