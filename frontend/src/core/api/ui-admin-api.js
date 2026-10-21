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

// Scopo: Crea preset (testata). Idempotency-Key obbligatoria:
//        l'`Idempotency-Key` la mette l'interceptor di `core/api.js` (§A5, 2026-10-20).
export function createAdminPreset(listaId, payload) {
  return api.post(
    `${BASE}/liste/${encodeURIComponent(listaId)}/preset/`,
    payload,
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
export function upsertAdminPermesso(payload) {
  return api.post(
    `${BASE}/permessi/`,
    payload,
  )
}

// Scopo: Elimina permesso per id.
export function deleteAdminPermesso(permessoId) {
  return api.delete(`${BASE}/permessi/${encodeURIComponent(permessoId)}/`)
}

// ── Fase 2 — DEF-5b CRUD definizioni (SUPER_ADMIN only) ───────────────
//
// Pagina tecnica `/amm-software/personalizzazioni-liste-tecniche`. La
// permission e' gestita lato BE (`AdminAPIView` -> `IsAdminZeroERP`):
// utenti senza SUPER_ADMIN ricevono 403 anche se chiamano direttamente.

// Scopo: Lista completa definizioni (incluse disattivate) per la pagina
//        tecnica. Proiezione full (vista_sql, note, audit).
export function listAdminDefinizioniAdmin() {
  return api.get(`${BASE}/definizioni/`)
}

// Scopo: Crea una nuova definizione lista. Idempotency-Key obbligatoria
//        (UNIQUE codice mappato lato service).
export function createAdminDefinizione(payload) {
  return api.post(
    `${BASE}/definizioni/`,
    payload,
  )
}

// Scopo: Dettaglio definizione (campi completi, anche disattivate).
export function getAdminDefinizione(listaId) {
  return api.get(`${BASE}/definizioni/${encodeURIComponent(listaId)}/`)
}

// Scopo: Aggiorna campi mutabili. Tutti i campi mutabili eccetto `id`
//        (lo schema non ha colonne immutabili by design).
export function updateAdminDefinizione(listaId, payload) {
  return api.patch(
    `${BASE}/definizioni/${encodeURIComponent(listaId)}/`,
    payload,
  )
}

// Scopo: Cancella definizione. FK RESTRICT su lista_colonna,
//        lista_preset e lista_preferenza_utente: in uso -> 409.
export function deleteAdminDefinizione(listaId) {
  return api.delete(`${BASE}/definizioni/${encodeURIComponent(listaId)}/`)
}

// ── Fase 2 — DEF-5b CRUD colonne (SUPER_ADMIN only) ───────────────────

// Scopo: Lista completa colonne admin di una lista (incluse disattive).
//        Endpoint distinto da `listAdminListaColonne` (Fase 1, proiezione
//        minima per composizione preset) perche' qui vogliamo i 17 campi
//        editabili dalla pagina tecnica.
export function listAdminColonneAdmin(listaId) {
  return api.get(
    `${BASE}/definizioni/${encodeURIComponent(listaId)}/colonne/`,
  )
}

// Scopo: Crea colonna nella lista indicata. Idempotency-Key obbligatoria.
export function createAdminColonna(listaId, payload) {
  return api.post(
    `${BASE}/definizioni/${encodeURIComponent(listaId)}/colonne/`,
    payload,
  )
}

// Scopo: Dettaglio colonna per id (campi completi).
export function getAdminColonna(colonnaId) {
  return api.get(`${BASE}/colonne/${encodeURIComponent(colonnaId)}/`)
}

// Scopo: Aggiorna campi mutabili. lista_id e' immutabile: per spostare
//        una colonna fra liste, cancellarla e ricrearla.
export function updateAdminColonna(colonnaId, payload) {
  return api.patch(
    `${BASE}/colonne/${encodeURIComponent(colonnaId)}/`,
    payload,
  )
}

// Scopo: Cancella colonna. Soft-block applicativo se referenziata da
//        preferenze utente; FK CASCADE su preset_colonna e permessi.
export function deleteAdminColonna(colonnaId) {
  return api.delete(`${BASE}/colonne/${encodeURIComponent(colonnaId)}/`)
}
