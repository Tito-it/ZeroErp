// Client API fatture — CONSULTAZIONE.
// Doc BE: docs/it/backend/vendite/manual/api_fattura_dettaglio.md
//
// La fattura non ha CRUD: è prodotta dalla pipeline di fatturazione e oltre
// EMESSA le righe sono congelate a DB. Qui vive solo la lettura del documento
// per il drawer; stampa/allegati passano dal motore documentale
// (`/vendite/fatture/<id>/documenti/…`, BB `PdfDocumentiSorgenteDialog`) e le
// azioni di processo dal cockpit fatturazione.
import api from '../../core/api'

const BASE = '/vendite/fatture'

// GET documento completo: testata (cliente, emittente, pagamento, totali già
// decodificati) + righe + riepilogo IVA + scadenze in un round-trip.
// Sono gli stessi lettori che alimentano il contesto del PDF: video e stampa
// mostrano lo stesso documento per costruzione.
// 404 se la fattura non esiste **o** è fuori dallo scope emittente: i due casi
// sono indistinguibili di proposito.
export function getFatturaDettaglio(fatturaId) {
  return api.get(`${BASE}/${fatturaId}/`)
}

// ⭐ LA STORIA DEL DOCUMENTO: «cosa è successo a questa fattura, in ordine di
//    tempo». Sorgente `script.vw_giornale_entita`, la vista che cuce i registri
//    di evento del progetto — per la fattura oggi risponde `fatture_log`.
// ⛔ Da non confondere con `passaggi/`: quello dice con quali ALTRI documenti la
//    fattura è legata, questo cosa le è successo. Domande diverse, sorgenti
//    diverse.
// ⚠️ 404 unificato inesistente/fuori scope, come il dettaglio.
// ⭐ `sortBy` di default è la GRAVITÀ, e l'ordinamento lo fa il SERVER: la lista
//    è paginata, quindi riordinare qui riordinerebbe la sola pagina caricata —
//    «il più grave» diventerebbe «il più grave fra i primi 50», senza dirlo.
export function getFatturaGiornale(
  fatturaId,
  { page = 1, pageSize = 50, sortBy = 'gravita', sortDir = 'desc' } = {},
) {
  return api.get(`${BASE}/${fatturaId}/giornale/`, {
    params: { page, page_size: pageSize, sort_by: sortBy, sort_dir: sortDir },
  })
}
