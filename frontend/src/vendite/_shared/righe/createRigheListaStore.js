// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: factory dello store-lista delle RIGHE di un documento di vendita
//        (preventivo, ordine, DDT, reso), montato da `RigheMasterDetailTable`
//        (brief-db-liste-righe-documento, lotto B, 2026-09-28).
// Note: ⭐ E' UNA FACTORY, NON UNO STORE CONDIVISO, e ogni documento lo usa
//       con `storePerIstanza`: due drawer aperti insieme non si scrivono
//       addosso pagina, ricerca e ordinamento (`feedback_estrarre_non_
//       condividere_stato`). Quello che e' uguale e' la FORMA.
//       ⭐ Il PADRE COMPOSTO del core, come le revisioni (`createRevisioni
//       Store`): l'id del documento nel path e il suo emittente
//       (`emittente_fiscale_id`, la PK) in query. L'emittente NON e' un
//       filtro: e' il lasciapassare del cancello di perimetro, e per questo
//       sta nel padre e non nei filtri (non lo conta il segno dei filtri, non
//       lo azzera «Pulisci filtri»). Finche' manca — arriva col dettaglio —
//       la lista non legge ed e' in `attesaPadre`.
//       ⛔ NESSUN ordinamento di partenza: senza indicazioni il backend ordina
//       per l'ordine del DOCUMENTO (`riga_nr`, `ordine` sul preventivo).
//       Scriverne uno qui farebbe aprire le righe in un ordine diverso da
//       quello del documento stampato, senza che nessuno l'abbia chiesto.
// ------------------------------------------------------------
import { createListaStore } from '../../../core/stores/createListaStore'

// Params:
//   - storeId: id Pinia (lo passa `storePerIstanza`).
//   - fetchPage: `(documentoId, params) => Promise<response axios>` con
//       l'envelope paginato (`listRigheLista` di `makeRigheListaApi`).
export function createRigheListaStore(storeId, { fetchPage }) {
  return createListaStore(storeId, {
    fetchPage,
    parentField: 'documentoId',
    emittenteParam: 'emittente_fiscale_id',
    // Dentro un drawer la lista parte piena: il documento c'e' gia'.
    startsEmpty: false,
    orderBy: null,
    orderDir: null,
  })
}
