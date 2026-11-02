// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: uno store Pinia PER ISTANZA del componente che lo crea — per le
//        liste di sotto-entita' che vivono dentro un drawer (le revisioni di
//        un documento, la Storia di una fattura, i flussi di una pratica).
// Note: ⛔ IL DIFETTO CHE CHIUDE (2026-09-27, ok Tid). `defineStore(id)` e' un
//       singleton: uno store per TIPO di lista, non per drawer. Con due drawer
//       dello stesso tipo vivi insieme — la vista sotto KeepAlive che tiene il
//       suo aperto, un drawer impilato da un chip di collegamento — il secondo
//       scrive righe, padre e pagina nella lista del primo, e tornando al
//       primo si leggono le righe VERE di un documento SBAGLIATO. Nessun
//       errore: e' la forma di `feedback_estrarre_non_condividere_stato`, un
//       livello piu' su (la factory c'era, l'istanza era una sola).
//       ⭐ La forma: il chiamante dichiara COME si costruisce lo store dato un
//       id (`definisci(id) => defineStore(id, ...)`, o `createListaStore(id,
//       ...)`), e riceve un `useXxxStore()` che a ogni chiamata ne costruisce
//       uno nuovo con un id suo. Chi lo chiama nel setup del drawer ha lo
//       stesso nome di prima, e il SUO store.
//       ⚠️ Lo store si distrugge con lo scope che l'ha creato (`$dispose` +
//       stato tolto da `pinia.state`): senza, ogni apertura lascerebbe uno
//       store orfano nel registro. `$dispose` fa uscire lo store anche dal
//       registro `userScoped` (`auto-reset`). Fuori da uno scope (gli spec)
//       non c'e' niente da agganciare: lo store resta, come ogni store Pinia.
//       ⚠️ Una sola chiamata per istanza: lo store lo crea il componente che
//       lo possiede (il drawer, che ne legge anche il contatore) e lo passa
//       al tab come prop. Due chiamate danno due store, per costruzione.
// ------------------------------------------------------------

import { getCurrentScope, onScopeDispose } from 'vue'

let progressivo = 0

// Scopo: da `(idBase, definisci)` a un `useXxxStore()` per istanza.
//        `definisci(id)` ritorna la funzione `useStore` di Pinia per quell'id.
export function storePerIstanza(idBase, definisci) {
  return function useStorePerIstanza() {
    progressivo += 1
    const id = `${idBase}~${progressivo}`
    const store = definisci(id)()
    if (getCurrentScope()) {
      onScopeDispose(() => {
        const pinia = store._p
        store.$dispose()
        if (pinia?.state?.value) delete pinia.state.value[id]
      })
    }
    return store
  }
}
