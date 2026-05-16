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
// testata sintetica (forma derivata, listino + versione fissata, variazione
// globale) + righe con prezzo_finale calcolato e origine ('DA_LISTINO' /
// 'OVERRIDE' / 'ESCLUSIONE' / 'AGGIUNTA'). Forma "senza_listino" ritorna
// righe vuote (le righe AGGIUNTA vivono in `contratti_righe` e si leggono
// dall'endpoint /righe/).
export function listRighePreviewContratto(contrattoId) {
  return api.get(`${BASE}/${contrattoId}/righe-preview/`)
}

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

// Utility 1:1
export function addUtilityContratto(contrattoId, payload) {
  return api.post(`${BASE}/${contrattoId}/utility/`, payload)
}

export function updateUtilityContratto(contrattoId, utilityId, payload) {
  return api.patch(`${BASE}/${contrattoId}/utility/${utilityId}/`, payload)
}

// --- Componenti BoM riga contratto (modello unificato 2026-05-13) ---
// Specchio simmetrico dei 4 endpoint preventivi. Auto-init dei componenti
// avviene lato BE in `addRigaContratto` quando l'articolo e' composito;
// il payload può includere `componenti_overrides` (delta dei prezzi diversi
// dal suggerito) per pre-impostare prezzi manuali al momento della create.

// Preview componenti pre-save (read-only): ritorna i figli BoM con
// `prezzo_suggerito` dal resolver bundle-aware. Consumato da
// `ComponentiDialog` PRIMA del save di una riga padre composita.
// Payload: { articolo_id, uom_operativa_id, quantita }.
export function previewRigaComponenti(contrattoId, payload) {
  return api.post(
    `${BASE}/${contrattoId}/righe/preview-componenti/`,
    payload,
  )
}

// `soloAttivi=true` default backcompat. EDIT panel passa false per
// includere opzionali disattivati e permettere il toggle di riattivazione.
export function listRigaComponenti(contrattoId, rigaId, { soloAttivi = true } = {}) {
  const params = soloAttivi ? {} : { solo_attivi: 'false' }
  return api.get(`${BASE}/${contrattoId}/righe/${rigaId}/componenti/`, { params })
}

// PATCH singolo componente (prezzo override, IVA, origine, ecc.).
// Coerente con updateRiga/updateContratto: nessuna Idempotency-Key.
export function updateRigaComponente(contrattoId, rigaId, componenteId, payload) {
  return api.patch(
    `${BASE}/${contrattoId}/righe/${rigaId}/componenti/${componenteId}/`,
    payload,
  )
}

// Soft delete componente: il trigger DB ricalcola il prezzo della riga padre.
export function deleteRigaComponente(contrattoId, rigaId, componenteId) {
  return api.delete(
    `${BASE}/${contrattoId}/righe/${rigaId}/componenti/${componenteId}/`,
  )
}
