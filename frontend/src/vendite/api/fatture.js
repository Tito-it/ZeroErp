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
