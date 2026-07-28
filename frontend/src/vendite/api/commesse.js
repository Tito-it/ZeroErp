// Client API commesse — governo operativo (cockpit fatturazione, Fase A).
// Doc BE: docs/it/backend/vendite/manual/api_commessa_attivita.md +
//         api_commessa_stato.md + api_commesse_pricing.md.
// La commessa non ha lista/CRUD propria: dettaglio (stato+capabilities),
// righe, approvazione (A-1/A-2), azione di stato utente e azioni prezzo
// N5/N7/sblocco sulle righe.
import api from '../../core/api'
import { generateIdempotencyKey } from '../../core/utils/idempotency'

const BASE = '/vendite/commesse'

// GET stato + contatori + capabilities (script.fn_available_actions_commessa).
export function getCommessaStato(commessaId) {
  return api.get(`${BASE}/${commessaId}/stato/`)
}

// GET righe attivita' paginate (limit/offset; filtri stato opzionali).
export function listCommessaAttivita(commessaId, params = {}) {
  return api.get(`${BASE}/${commessaId}/attivita/`, { params })
}

// POST approvazione righe (A-1): righeIds null/omesso = tutte le NON_EMESSA
// in BOZZA. Idempotency-Key obbligatoria (`require_idempotency_key=True`).
export function approvaCommessaAttivita(commessaId, righeIds = null) {
  const payload = {}
  if (righeIds) payload.righe_ids = righeIds
  return api.post(
    `${BASE}/${commessaId}/attivita/approva/`,
    payload,
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST approvazione massiva per mese di competenza (A-2): la popolazione
// DA_APPROVARE della card (stessa vista del drill-down, scope in-vista).
export function approvaCompetenza(competenzaMese, { commessaIds = null } = {}) {
  const payload = { competenza_mese: competenzaMese }
  if (commessaIds) payload.commessa_ids = commessaIds
  return api.post(
    '/vendite/fatturazione/approva-competenza/',
    payload,
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST azione di stato utente (chiudi/riapri/annulla) — target dalla lista
// available_actions delle capabilities (transizioni manuali data-driven).
export function cambiaStatoCommessa(commessaId, nuovoStato) {
  return api.post(
    `${BASE}/${commessaId}/stato/`,
    { nuovo_stato: nuovoStato },
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST porta oneri: aggiunge alla commessa una riga di puro valore (qta=1,
// tipo_movimento=ONERE, gia' APPROVATA). Causale, unita' di misura e IVA sono
// derivate dall'articolo-onere lato DB; l'istanza utility dal BA della commessa
// se non passata. Gate azione di processo `carica_voce_manuale`.
export function aggiungiOnereCommessa(commessaId, {
  articoloOnereId, importo, tipoDocFiscaleId, motivo = null, dataAttivita = null,
}) {
  const payload = {
    articolo_onere_id: articoloOnereId,
    importo,
    tipo_doc_fiscale_id: tipoDocFiscaleId,
  }
  if (motivo) payload.motivo = motivo
  if (dataAttivita) payload.data_attivita = dataAttivita
  return api.post(
    `${BASE}/${commessaId}/oneri/`,
    payload,
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST riallineo prezzo da listino (N5). `confermaVersioneDiversa` al secondo
// giro quando il BE segnala versione listino cambiata (richiede_conferma).
export function riallineaPrezzoAttivita(commessaId, attId, { confermaVersioneDiversa = false } = {}) {
  const payload = {}
  if (confermaVersioneDiversa) payload.conferma_versione_diversa = true
  return api.post(
    `${BASE}/${commessaId}/attivita/${attId}/riallinea-prezzo/`,
    payload,
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST variazione prezzo eccezionale (N7): prezzo manuale + motivo obbligatorio;
// imposta prezzo_bloccato=true.
export function variazionePrezzoAttivita(commessaId, attId, { prezzo, motivo }) {
  return api.post(
    `${BASE}/${commessaId}/attivita/${attId}/variazione-prezzo-eccezionale/`,
    { prezzo, motivo },
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST annullamento di una riga MANUALE (onere) caricata per errore. Non
// cancella nulla: porta `stato_emissione` ad ANNULLATA, valore che tutte le
// porte verso fattura e cockpit gia' filtrano. `motivo` obbligatorio lato BE e
// lato DB (l'unica traccia del PERCHE' e' l'evento di log). Gate azione di
// processo `carica_voce_manuale`, lo stesso della porta oneri.
export function annullaRigaCommessa(commessaId, attId, { motivo }) {
  return api.post(
    `${BASE}/${commessaId}/attivita/${attId}/annulla/`,
    { motivo },
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST sblocco prezzo (N7-sblocco): rimuove il blocco e ricalcola dal resolver.
// `motivo` obbligatorio lato BE (fn_sblocca_prezzo → _parse_motivo): senza,
// l'endpoint risponde 400 «Motivo obbligatorio».
export function sbloccaPrezzoAttivita(commessaId, attId, { motivo }) {
  return api.post(
    `${BASE}/${commessaId}/attivita/${attId}/sblocca-prezzo/`,
    { motivo },
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}
