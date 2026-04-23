// Client API workflow L3 approvazione prezzo (Sprint E listini v5 §14.6).
// 3 endpoint: coda approver + approva/rifiuta singola riga.
import api from '../../core/api'

// GET /vendite/approvazioni-prezzo/?limit=&offset=
// Coda paginata pratiche tipo APPROVAZIONE_PREZZO in stato APERTA,
// scope emittente derivato dal JWT operatore.
export function listCodaApprovazioni(params = {}) {
  return api.get('/vendite/approvazioni-prezzo/', { params })
}

// POST /vendite/righe/<riga_id>/approva-prezzo/
// Approva la riga PENDING. Richiede azione `approva_prezzo` (o superuser).
// Body: { nota?: string }
export function approvaPrezzoRiga(rigaId, payload = {}) {
  return api.post(`/vendite/righe/${rigaId}/approva-prezzo/`, payload)
}

// POST /vendite/righe/<riga_id>/rifiuta-prezzo/
// Rifiuta la riga PENDING. Body: { motivazione?: string }
export function rifiutaPrezzoRiga(rigaId, payload = {}) {
  return api.post(`/vendite/righe/${rigaId}/rifiuta-prezzo/`, payload)
}
