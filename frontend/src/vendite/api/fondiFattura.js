// Scopo: client API dei «fondi fattura da decidere» — i casi in cui il giro
//        automatico si FERMA e la scelta resta a una persona.
//        Contratto BE: apps/vendite/api/views_fondi_fattura.py
//        (vista `vendite.vw_fondi_fattura_da_decidere`, D-10 del brief
//        fondo-fattura-ricalcolo-e-governo).
//
// ⚠️ L'ELENCO PRESENTA E NON SANA: nessuna di queste righe ha un gemello
// automatico che la corregge da sola — sanarle vorrebbe dire muovere denaro
// senza che nessuno l'abbia deciso.
// ⭐ ~~Sola lettura~~ non piu' dal 2026-08-31: c'e' UN verbo, la cancellazione
// dell'atto (BE-4, in fondo al file). Non contraddice la riga qui sopra —
// cancellare un atto che non ha mai mosso denaro non e' «sanare», e' togliere
// una proposta che nessuno ha accettato. E lo chiede una persona, ogni volta.
import api from '../../core/api'

// GET /vendite/fondi-fattura/da-decidere/?motivo=&order_by=&order_dir=&limit=&offset=
// Elenco paginato. `motivo` e' un vocabolario CHIUSO (PROPOSTA_SENZA_ATTO |
// UTILITY_NON_ATTRIBUIBILE | IMPORTO_NON_CORRISPONDENTE | NON_PIU_CAPIENTE):
// un valore fuori elenco torna 400, non una lista vuota — su un vocabolario
// chiuso il silenzio sarebbe indistinguibile da «non c'e' niente da decidere».
export function listFondiFatturaDaDecidere(params) {
  return api.get('/vendite/fondi-fattura/da-decidere/', { params })
}

// GET /vendite/fondi-fattura/da-decidere/export/?formato=csv|xlsx&<stessi filtri>
// Export della STESSA lista: colonne, ordine e visibilita' vengono dalla
// configurazione dell'operatore sul catalogo `vendite.fondi_fattura_da_decidere`,
// non da un elenco fisso — un file con colonne diverse da quelle a video
// sarebbe un secondo elenco da riconciliare a mano.
// ⚠️ `formato`, non `format`: quest'ultimo e' magic per DRF (content
// negotiation) e intercetterebbe la chiamata prima della view.
export function exportFondiFatturaDaDecidere(params = {}) {
  return api.get('/vendite/fondi-fattura/da-decidere/export/', {
    params,
    responseType: 'blob',
  })
}

// ══════════════════════════════════════════════════════════════
//  Il verbo (BE-4) — cancellare un atto che non e' ancora un fatto
// ══════════════════════════════════════════════════════════════

// DELETE /vendite/fondi-fattura/<id>/
// Cancella l'atto di fondo, oppure il database RIFIUTA dicendo perche'.
//
// ⭐ Il METODO dice il verbo: `api.md` §Grammatica URL vieta di scriverlo nel
// path, quindi non esiste un `POST .../cancella/`.
//
// ⛔ NON serve al riporto sbagliato. Quello si disfa annullando la sistemazione
// che lo ha creato (`POST /pagamenti/sistemazioni/{id}/annulla/`), e se si prova
// da qui il backend risponde `E_FONDO_TRATTENUTO_DA_SISTEMAZIONE` — che NOMINA
// quell'alternativa invece di dire «non si puo'». Qui si serve l'ALTRA
// popolazione: il fondo `AUTOMATICA` non piu' capiente, che nessuno trattiene.
//
// ⚠️ `Idempotency-Key` obbligatoria (il backend dichiara
// `require_idempotency_key`): il gesto e' IRREVERSIBILE. ⛔ La key che mette
// l'interceptor (`applicaIdempotencyKey`) e' una per CHIAMATA: da sola NON fa
// rispondere il doppio invio come il primo — un secondo clic e' una chiamata
// nuova, e dopo una cancellazione riuscita riceverebbe un errore. Il replay
// c'e' solo se il chiamante passa in `config` la key del GESTO
// (`useChiaveGesto`), come fa `FondiFatturaDaDecidereTab`, e il backend e' in
// modalita' forte (`DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1`).
export function cancellaFondoFattura(fondoSourceId, config = {}) {
  return api.delete(`/vendite/fondi-fattura/${fondoSourceId}/`, config)
}
