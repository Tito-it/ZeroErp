// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: factory dello store-lista del tab «Revisioni» di un documento di
//        vendita (preventivo, offerta): la catena delle revisioni del
//        documento aperto, paginata lato server, montata da `RevisioniTab`.
// Note: ⭐ E' UNA FACTORY, NON UNO STORE CONDIVISO. Ogni documento ha il SUO
//       store (`usePreventivoRevisioniStore`, `useOffertaRevisioniStore`):
//       condividerne uno farebbe scrivere a un drawer pagina e ordinamento
//       dell'altro — i due possono essere aperti insieme, uno sopra l'altro
//       (`feedback_estrarre_non_condividere_stato`). Quello che e' uguale e'
//       la FORMA, ed e' questa: nasce alla seconda copia (regola del 2).
//       ⭐ Il PADRE e' il documento, e porta DUE cose: l'id (nel path) e
//       l'emittente del documento (`emittente_fiscale_id`, la PK). Il secondo
//       NON e' un filtro — il backend non ci restringe le righe, la catena e'
//       di un emittente solo per costruzione — ma il lasciapassare del
//       cancello di perimetro: le liste sono `multi_emittente = f`, e senza di
//       lui chi vede piu' emittenti riceve E_UI_LISTA_EMITTENTE_DA_SCEGLIERE
//       dentro un drawer gia' aperto. ⚠️ Per questo sta nel padre e non in
//       `filterDefaults`: un filtro lo conterebbe il segno dei filtri attivi e
//       lo azzererebbe «Pulisci filtri».
//       ⭐ E' il PADRE COMPOSTO del core (`parentField: 'documentoId'` +
//       `emittenteParam`, 2026-09-27): finche' manca l'emittente, che arriva
//       col dettaglio, la lista non legge ed e' in `attesaPadre`. Stessa forma
//       di `pratiche/stores/praticaFlussi.js` e di `giornaleEntita.js`.
// ------------------------------------------------------------
import { createListaStore } from '../../../core/stores/createListaStore'

// Params:
//   - storeId: id Pinia dello store (uno per documento).
//   - fetchRevisioni: `(documentoId, params) => Promise<response axios>` con
//       l'envelope paginato standard.
//   - orderBy: il `campo_sorgente` dell'ordinamento di partenza — la colonna
//       `rev` del catalogo, che sul preventivo legge `rev` e sull'offerta
//       `revisione_numero`. ASC: la catena si legge dalla prima revisione.
export function createRevisioniStore(storeId, { fetchRevisioni, orderBy }) {
  return createListaStore(storeId, {
    fetchPage: fetchRevisioni,
    parentField: 'documentoId',
    emittenteParam: 'emittente_fiscale_id',
    // Dentro un drawer la lista parte piena: il padre c'e' gia'.
    startsEmpty: false,
    orderBy,
    orderDir: 'asc',
    // Scopo: rileggere la catena dopo un'azione di stato sul documento
    //        (emissione, esito, annullo, nuova revisione) — che cambia lo
    //        stato di una riga della catena senza cambiare il padre.
    // ⚠️ Solo se lo store e' GIA' agganciato a QUEL documento: al primo
    //    caricamento, o passando a un altro documento, la lettura la fa il
    //    cambio di padre in `useDrawerTabLista`, e una seconda qui partirebbe
    //    col padre vecchio. Sta nella factory e non nei due drawer perche' e'
    //    lo stesso controllo, e nasce gia' in due copie.
    extend: (base) => ({
      rileggiSeAgganciato(documentoId) {
        const agganciato = base.documentoId.value
        if (!agganciato || Number(agganciato) !== Number(documentoId)) return false
        return base.fetchList()
      },
    }),
  })
}
