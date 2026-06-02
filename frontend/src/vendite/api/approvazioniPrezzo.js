// Client API workflow L3 approvazione prezzo (Sprint E listini v5 §14.6).
// 3 endpoint: coda approver + approva/rifiuta singola riga.
import api from '../../core/api'

// GET /vendite/approvazioni-prezzo/?limit=&offset=
// Coda paginata pratiche tipo APPROVAZIONE_PREZZO in stato APERTA,
// scope emittente derivato dal JWT operatore.
export function listCodaApprovazioni(params = {}) {
  return api.get('/vendite/approvazioni-prezzo/', { params })
}

// Segmento URL per sorgente: il workflow L3 ha endpoint distinti per
// preventivo / contratto / offerta (riga_id appartiene a tabelle/sequence
// indipendenti). Allineato ai path BE in `urls_v1.py`. Default `preventivo`
// per back-compat con i call site Sprint E.
const _SORGENTE_PATH = {
  preventivo: 'righe',
  contratto: 'righe-contratto',
  offerta: 'eccezioni-offerta',
}

function _segmento(sorgente) {
  return _SORGENTE_PATH[sorgente] || _SORGENTE_PATH.preventivo
}

// POST /vendite/<segmento>/<riga_id>/approva-prezzo/
// Approva la riga PENDING. Richiede azione `approva_prezzo_override` (o superuser).
// Body: { nota?: string }. `sorgente` = preventivo | contratto | offerta.
export function approvaPrezzoRiga(rigaId, payload = {}, sorgente = 'preventivo') {
  return api.post(`/vendite/${_segmento(sorgente)}/${rigaId}/approva-prezzo/`, payload)
}

// POST /vendite/<segmento>/<riga_id>/rifiuta-prezzo/
// Rifiuta la riga PENDING. Body: { motivazione?: string }.
export function rifiutaPrezzoRiga(rigaId, payload = {}, sorgente = 'preventivo') {
  return api.post(`/vendite/${_segmento(sorgente)}/${rigaId}/rifiuta-prezzo/`, payload)
}
