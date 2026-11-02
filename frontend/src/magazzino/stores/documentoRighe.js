// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Gli store delle RIGHE di un documento interno — uno per famiglia
//        (`magazzino.inventario_righe`, `magazzino.rettifica_righe`),
//        consumati dal drawer del documento attraverso `useDrawerTabLista`.
// Note: ⭐ Le righe sono una LISTA STANDARD (frontend-standards §Regola zero:
//       «una lista su un tab di drawer e' una lista, le manca il paginator,
//       non la natura»): pagine, ricarica, «Personalizza colonne», export.
//       Le colonne vengono dal catalogo (liste 71 e 74).
//       ⭐ IL PADRE E' NELLO STORE, NON NEI FILTRI: `documentoId` e' il
//       contesto (arriva dal path dell'endpoint), i filtri sono le scelte
//       dell'operatore — e al cambio padre i secondi si azzerano mentre il
//       primo si riscrive.
//       ⛔ NESSUN ordinamento di partenza: senza indicazioni il backend ordina
//       `id ASC`, cioe' l'ORDINE DI DIGITAZIONE — e' cosi' che un conteggio a
//       scaffale si rilegge. Scrivere qui una colonna farebbe divergere
//       l'apertura dal default del backend senza che nessuno l'abbia chiesto.
//       ⭐ I verbi di riga NON stanno qui: cambiano il documento (il
//       `righe_count`, il riepilogo del piano), quindi emettono l'evento della
//       FAMIGLIA — e stanno nello store della famiglia, non in quello delle
//       righe. Qui si legge e basta.
// ------------------------------------------------------------

import { createListaStore } from '../../core/stores/createListaStore'
import { storePerIstanza } from '../../core/stores/storePerIstanza'
import { listRighe } from '../api/magazzino'
import { FAMIGLIE } from '../vocabolari'

const STORES = Object.fromEntries(
  Object.values(FAMIGLIE).map((f) => [
    f.codice,
    // ⭐ Uno store per ISTANZA del drawer (`storePerIstanza`, 2026-09-27),
    //    non per famiglia: due documenti vivi insieme non si scrivono addosso
    //    le righe.
    storePerIstanza(`magazzino-${f.codice}-righe`, (id) => createListaStore(id, {
      fetchPage: (docId, params) => listRighe(f.codice, docId, params),
      parentField: 'documentoId',
      // Il documento e' gia' scelto quando il drawer si apre: non e' una lista
      // che parte vuota in attesa di una ricerca.
      startsEmpty: false,
      orderDir: null,
    })),
  ]),
)

// Scopo: lo store delle righe della famiglia chiesta.
export function useDocumentoRigheStore(famiglia) {
  const useStore = STORES[famiglia]
  if (!useStore) throw new Error(`[magazzino] famiglia sconosciuta: ${famiglia}`)
  return useStore()
}
