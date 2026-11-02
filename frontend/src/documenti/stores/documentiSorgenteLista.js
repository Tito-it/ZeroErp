// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Gli store-LISTA dei documenti generati di una sorgente (lista
//        configurabile `documenti.documenti_sorgente`, 84) — uno per codice
//        sorgente (PREVENTIVO, CONTRATTO, OFFERTA_COMMERCIALE, ORDINE_VENDITA,
//        DDT_VENDITA, FATTURA), costruiti dalla STESSA configurazione.
// Note: ⭐ NASCE DALLO STORE DELLE AZIONI (`documentiPerSorgente`), che fino al
//       2026-09-27 teneva anche la lista: `items`/`totalRecords`/`fetchList`
//       scritti a mano, envelope suo (`total_count`) e NESSUNA paginazione — il
//       frontend non mandava `page_size`, il backend ne dava 50 e la lista si
//       fermava li' senza dirlo. Ora la lista sta sul core
//       (`useListaStoreCore`: filtri, fetch paginata, `fetchSospesa`, reset,
//       «vuota» contro «non letta»), e lo store delle azioni resta alle azioni
//       (genera/anteprima/download/allegati/ristampa).
//       ⛔ UNO STORE PER SORGENTE, NON UNO CONDIVISO FRA LE SEI. Lo stesso
//       componente e' montato da otto chiamanti in sei domini: uno store unico
//       con la sorgente dentro si farebbe scrivere addosso pagina e filtri
//       dalla prossima apertura di un'altra sorgente
//       (`feedback_estrarre_non_condividere_stato`). Si condivide la FABBRICA
//       (`creaStoreSorgente`), e gli store nascono da un ciclo, come le
//       famiglie di magazzino (`magazzino/stores/documentiInterni.js`).
//       ⭐ IL PADRE E' COMPOSTO: la sorgente (nel path) e l'EMITTENTE del
//       documento (in query, `emittente_fiscale_id`, il
//       `lista_emittente_param` della view) — il padre composto del core
//       (`emittenteParam`, 2026-09-27). ⛔ Fino a quel giorno l'emittente era
//       un `ref` dello store letto dalla `fetchPage`, e la lista partiva
//       ANCHE senza — al super admin su «Tutti» quella lettura tornava 422.
//       Ora senza emittente la lista non legge ed e' in `attesaPadre`: ogni
//       chiamante lo passa, perche' un documento l'emittente ce l'ha sempre.
//       ⚠️ `userScoped: true`: i documenti sono dati del perimetro
//       dell'operatore, e al logout non devono restare in memoria.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { useListaStoreCore } from '../../core/composables/useListaStoreCore'
import { storePerIstanza } from '../../core/stores/storePerIstanza'
import { SORGENTE_CLIENT_MAP } from '../api/documentiPerSorgente'

// Scopo: costruisce lo store-lista di UNA sorgente.
// ⭐ Uno store per ISTANZA del dialog (`storePerIstanza`), non per sorgente:
//    due ordini con il dialog dei PDF vivi insieme non si scrivono addosso.
function creaStoreSorgente(sorgenteCode, client) {
  return storePerIstanza(`documenti-sorgente-lista-${sorgenteCode.toLowerCase()}`, (id) => defineStore(id, () => {
    return useListaStoreCore({
      // La sorgente nel PATH; l'emittente del documento in query, dal core.
      fetchPage: (sorgenteId, params) => client.list(sorgenteId, params),
      parentField: 'sorgenteId',
      emittenteParam: 'emittente_fiscale_id',
      // Parte piena: sono i documenti di QUESTA sorgente.
      startsEmpty: false,
      // L'ultimo documento emesso in cima: e' il preset a catalogo
      // (`generato_at desc`) e il default del backend, quindi la lista non si
      // riordina al primo click, e il ripiego del verso segue.
      orderBy: 'generato_at',
      orderDir: 'desc',
      orderDirDefault: 'desc',
    })
  }, { userScoped: true }))
}

// Gli store, uno per sorgente registrata nel client API: una sorgente nuova
// entra dalla mappa dei client, non da qui.
const STORES = Object.fromEntries(
  Object.entries(SORGENTE_CLIENT_MAP).map(
    ([codice, client]) => [codice, creaStoreSorgente(codice, client)],
  ),
)

// Scopo: lo store-lista della sorgente `sorgenteCode`. Solleva se il codice
//        non e' registrato: e' un errore di programmazione, non un dato.
export function useDocumentiSorgenteListaStore(sorgenteCode) {
  const useStore = STORES[sorgenteCode]
  if (!useStore) {
    throw new Error(`SorgenteCode '${sorgenteCode}' non mappato in SORGENTE_CLIENT_MAP`)
  }
  return useStore()
}
