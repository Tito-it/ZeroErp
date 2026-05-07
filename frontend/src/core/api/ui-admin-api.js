// Scopo: API client per il namespace admin /api/v1/ui/admin/* (Blocco F).
//        11 endpoint per gestione preset e permessi colonna delle liste:
//        Select header, catalogo colonne, CRUD preset (testata + composizione),
//        UPSERT/DELETE permessi colonna.
//
// Convenzione: ritornano la response Axios (envelope `{data, meta}`).
// Lo unwrap viene fatto a livello composable/store (`useApiHandler`).

import api from '../api'

const BASE = '/ui/admin'

// ── Selectore "Lista corrente" + catalogo colonne ──────────────────────

// Scopo: Lista delle definizioni di lista attive (Select header).
//        Visibile a SUPER_ADMIN o utenti con almeno una delle due
//        azioni di processo `ui_preset_manage`/`ui_permesso_manage`.
export function listAdminListaDefinizioni() {
  return api.get(`${BASE}/liste/`)
}

// Scopo: Catalogo colonne grezzo di una lista (per la composizione preset).
export function listAdminListaColonne(listaId) {
  return api.get(`${BASE}/liste/${encodeURIComponent(listaId)}/colonne/`)
}

// ── Preset ─────────────────────────────────────────────────────────────

// Scopo: Lista preset di una lista (con display fields su profilo / emittente
//        e conteggio righe composizione).
export function listAdminPresetByLista(listaId) {
  return api.get(`${BASE}/liste/${encodeURIComponent(listaId)}/preset/`)
}

// Scopo: Crea preset (testata). Idempotency-Key obbligatoria, generata
//        dal caller via crypto.randomUUID().
export function createAdminPreset(listaId, payload, idempotencyKey) {
  return api.post(
    `${BASE}/liste/${encodeURIComponent(listaId)}/preset/`,
    payload,
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
}

// Scopo: Aggiorna campi mutabili di un preset.
export function updateAdminPreset(presetId, payload) {
  return api.patch(`${BASE}/preset/${encodeURIComponent(presetId)}/`, payload)
}

// Scopo: Elimina preset (CASCADE su composizione, SET NULL su preferenze).
export function deleteAdminPreset(presetId) {
  return api.delete(`${BASE}/preset/${encodeURIComponent(presetId)}/`)
}

// Scopo: Restituisce la composizione attuale del preset.
export function listAdminPresetColonne(presetId) {
  return api.get(`${BASE}/preset/${encodeURIComponent(presetId)}/colonne/`)
}

// Scopo: Replace atomico della composizione del preset.
export function replaceAdminPresetColonne(presetId, payload) {
  return api.put(
    `${BASE}/preset/${encodeURIComponent(presetId)}/colonne/`,
    payload,
  )
}

// ── Permessi colonna ───────────────────────────────────────────────────

// Scopo: Lista permessi colonna di una lista (con display fields).
export function listAdminPermessiByLista(listaId) {
  return api.get(`${BASE}/liste/${encodeURIComponent(listaId)}/permessi/`)
}

// Scopo: UPSERT permesso colonna su (colonna_id, profilo_accesso_id).
//        Idempotency-Key obbligatoria.
export function upsertAdminPermesso(payload, idempotencyKey) {
  return api.post(
    `${BASE}/permessi/`,
    payload,
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
}

// Scopo: Elimina permesso per id.
export function deleteAdminPermesso(permessoId) {
  return api.delete(`${BASE}/permessi/${encodeURIComponent(permessoId)}/`)
}
