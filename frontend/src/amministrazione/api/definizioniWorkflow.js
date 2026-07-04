// Client API per le edizioni di workflow versionate (Amm. Software, Fase 2).
// Endpoint: /pratiche/definizioni/ (AdminAPIView, super-admin).
// Read-only in Slice 1a (letture già sbloccate a DB via GRANT SELECT); le azioni
// fork/nuova-versione/pubblica arrivano in Slice 1b, in lockstep con la conversione
// SECURITY DEFINER delle fn DB (brief-db-accesso-be-definizioni-workflow §P1).

import api from '../../core/api'
import { generateIdempotencyKey } from '../../core/utils/idempotency'

const BASE = '/pratiche/definizioni'

// Lista edizioni per (tipo [, emittente]) con drift. Params opzionali:
// tipo_prestazione_id, emittente_fiscale_id. Assenti = tutte (preset inclusi).
export function listDefinizioniWorkflow(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// --- Azioni ciclo di vita (Slice 1b). Idempotenti (write-once). ---
// Co-requisito: fn DB a SECURITY DEFINER (lockstep §P1) — finché INVOKER
// restituiscono E_DATABASE (permesso negato).

export function forkDefinizione(definizioneId, emittenteFiscaleId) {
  return api.post(
    `${BASE}/${definizioneId}/fork/`,
    { emittente_fiscale_id: emittenteFiscaleId },
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

export function nuovaVersioneDefinizione(definizioneId) {
  return api.post(
    `${BASE}/${definizioneId}/nuova-versione/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

export function pubblicaDefinizione(definizioneId) {
  return api.post(
    `${BASE}/${definizioneId}/pubblica/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}
