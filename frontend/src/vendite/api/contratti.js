// Client API contratti v5 (testata + righe + utility 1:1 + cambio stato).
// Endpoint: /vendite/contratti/ (vedi docs/it/backend/vendite/manual/api_contratti.md).

import api from '../../core/api'

const BASE = '/vendite/contratti'

// Testata
export function listContratti(params = {}) {
  return api.get(`${BASE}/`, { params })
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
export function cambiaStatoContratto(id, codiceInterno, { validoAl = null } = {}) {
  const payload = { codice_interno: codiceInterno }
  if (validoAl) payload.valido_al = validoAl
  return api.post(`${BASE}/${id}/cambia-stato/`, payload)
}

// Righe
export function addRigaContratto(contrattoId, payload) {
  return api.post(`${BASE}/${contrattoId}/righe/`, payload)
}

// Anteprima righe applicate (modalita' A/B). Restituisce envelope con
// testata sintetica (modalita derivata, listino, variazione globale) +
// righe con prezzo_finale gia' calcolato e origine ('DA_LISTINO' /
// 'OVERRIDE'). Modalita' C ritorna righe vuote.
export function listRighePreviewContratto(contrattoId) {
  return api.get(`${BASE}/${contrattoId}/righe-preview/`)
}

export function updateRigaContratto(contrattoId, rigaId, payload) {
  return api.patch(`${BASE}/${contrattoId}/righe/${rigaId}/`, payload)
}

export function deleteRigaContratto(contrattoId, rigaId) {
  return api.delete(`${BASE}/${contrattoId}/righe/${rigaId}/`)
}

// Utility 1:1
export function addUtilityContratto(contrattoId, payload) {
  return api.post(`${BASE}/${contrattoId}/utility/`, payload)
}

export function updateUtilityContratto(contrattoId, utilityId, payload) {
  return api.patch(`${BASE}/${contrattoId}/utility/${utilityId}/`, payload)
}
