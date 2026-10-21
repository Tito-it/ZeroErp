// Client API per le edizioni di workflow versionate (Amm. Software, Fase 2).
// Endpoint: /pratiche/definizioni/ (AdminAPIView, super-admin).
// Read-only in Slice 1a (letture già sbloccate a DB via GRANT SELECT); le azioni
// fork/nuova-versione/pubblica arrivano in Slice 1b, in lockstep con la conversione
// SECURITY DEFINER delle fn DB (brief-db-accesso-be-definizioni-workflow §P1).

import api from '../../core/api'

const BASE = '/pratiche/definizioni'

// Lista edizioni per (tipo [, emittente]) con drift. Params opzionali:
// tipo_prestazione_id, emittente_fiscale_id. Assenti = tutte (preset inclusi).
export function listDefinizioniWorkflow(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Dettaglio strutturale di un'edizione (header+drift + steps con figli annidati
// + archi a livello edizione). Alimenta l'editor DefinizioneEditorView.
// 404 E_DEFINIZIONE_NOT_FOUND se l'id non esiste.
export function getDefinizioneDettaglio(definizioneId) {
  return api.get(`${BASE}/${definizioneId}/`)
}

// --- Editing strutturale della BOZZA (Slice 2 anello 3): CRUD step. ---
// La Idempotency-Key delle POST la mette l'interceptor di `core/api.js`
// (PATCH/DELETE ne restano fuori). Campi core: codice, descrizione, sequenza, obbligatorio,
// direzione, modalita_esito, esito_default. definizione_id/tipo_prestazione_id
// sono impostati dal BE. L'immutabilita' (edizione emessa) e' guard DB.

export function createStep(definizioneId, payload) {
  return api.post(`${BASE}/${definizioneId}/steps/`, payload)
}

export function updateStep(definizioneId, stepId, payload) {
  return api.patch(`${BASE}/${definizioneId}/steps/${stepId}/`, payload)
}

export function deleteStep(definizioneId, stepId) {
  return api.delete(`${BASE}/${definizioneId}/steps/${stepId}/`)
}

// --- Figli per-nodo di uno step (Slice 2 anello 4): canali / handler-eventi /
// competenze. `kind` = segmento URL kebab ('canali' | 'handler-eventi' |
// 'competenze'). template_flusso_id impostato dal BE dallo step in URL. ---

export function createStepFiglio(definizioneId, stepId, kind, payload) {
  return api.post(`${BASE}/${definizioneId}/steps/${stepId}/${kind}/`, payload)
}

export function updateStepFiglio(definizioneId, stepId, kind, rowId, payload) {
  return api.patch(`${BASE}/${definizioneId}/steps/${stepId}/${kind}/${rowId}/`, payload)
}

export function deleteStepFiglio(definizioneId, stepId, kind, rowId) {
  return api.delete(`${BASE}/${definizioneId}/steps/${stepId}/${kind}/${rowId}/`)
}

// --- Archi del grafo, a livello edizione (Slice 2 anello 5): prerequisiti /
// formule-tempo / regole-generazione. `kind` = segmento URL kebab. Gli step
// endpoint devono appartenere alla definizione (validati dal BE); per
// formule-tempo il `tipo_prestazione_id` è auto-impostato dal BE. ---

export function createArco(definizioneId, kind, payload) {
  return api.post(`${BASE}/${definizioneId}/archi/${kind}/`, payload)
}

export function updateArco(definizioneId, kind, rowId, payload) {
  return api.patch(`${BASE}/${definizioneId}/archi/${kind}/${rowId}/`, payload)
}

export function deleteArco(definizioneId, kind, rowId) {
  return api.delete(`${BASE}/${definizioneId}/archi/${kind}/${rowId}/`)
}

// --- Azioni ciclo di vita (Slice 1b). Idempotenti (write-once). ---
// Co-requisito: fn DB a SECURITY DEFINER (lockstep §P1) — finché INVOKER
// restituiscono E_DATABASE (permesso negato).

export function forkDefinizione(definizioneId, emittenteFiscaleId) {
  return api.post(
    `${BASE}/${definizioneId}/fork/`,
    { emittente_fiscale_id: emittenteFiscaleId },
  )
}

export function nuovaVersioneDefinizione(definizioneId) {
  return api.post(
    `${BASE}/${definizioneId}/nuova-versione/`,
    {},
  )
}

export function pubblicaDefinizione(definizioneId) {
  return api.post(
    `${BASE}/${definizioneId}/pubblica/`,
    {},
  )
}
