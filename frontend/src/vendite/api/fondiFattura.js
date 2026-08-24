// Scopo: client API dei «fondi fattura da decidere» — i casi in cui il giro
//        automatico si FERMA e la scelta resta a una persona.
//        Contratto BE: apps/vendite/api/views_fondi_fattura.py
//        (vista `vendite.vw_fondi_fattura_da_decidere`, D-10 del brief
//        fondo-fattura-ricalcolo-e-governo).
//
// ⚠️ SOLA LETTURA, e non e' una fase: l'elenco PRESENTA e non sana. Nessuna di
// queste righe ha un gemello automatico che la corregge da sola — sanarle
// vorrebbe dire muovere denaro senza che nessuno l'abbia deciso.
import api from '../../core/api'

// GET /vendite/fondi-fattura/da-decidere/?motivo=&order_by=&order_dir=&page=&page_size=
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
