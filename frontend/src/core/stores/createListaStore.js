// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: factory per uno store di SOLA LISTA — nessun create/update, nessun
//        evento di tab. E' `useListaStoreCore` impacchettato in un
//        `defineStore`, e non fa nient'altro.
//
// ⭐ QUANDO SI USA QUESTA E NON `createCrudStore`: quando la lista non possiede
//    l'entita' che mostra. Gli atti di sistemazione si registrano dal drawer
//    dell'eccedenza, i titoli IVA di un soggetto dal drawer del titolo — il
//    ciclo di vita vive altrove, e uno store con `create`/`update` che nessuno
//    chiama sarebbe un contratto che non descrive niente.
// ⭐ E per le liste con il PADRE NEL PATH (`list(parentId, params)`), che
//    `createCrudStore` non sa esprimere: `parentField` le copre.
//
// ⚠️ `userScoped: true` di DEFAULT, come `createCrudStore`: una lista porta dati
//    che l'operatore vede per il suo perimetro, e senza reset restano in memoria
//    al logout (`feedback_pinia_userscoped`).
//
// Uso (lista con padre nel path):
//   export const useSistemazioniFatturaStore = createListaStore(
//     'pagamenti-sistemazioni-fattura',
//     { fetchPage: listSistemazioniFattura, parentField: 'fatturaId' },
//   )
//
// Uso (lista globale che parte piena, con ordinamento di partenza):
//   export const useTitoliIvaSfondatiStore = createListaStore(
//     'anagrafiche-titoli-iva-sfondati',
//     { fetchPage: listTitoliIvaSfondati, orderBy: 'eccedenza', orderDir: 'desc' },
//   )
import { defineStore } from 'pinia'
import { useListaStoreCore } from '../composables/useListaStoreCore'

// I parametri sono quelli di `useListaStoreCore`, piu' `options` (passthrough a
// `defineStore`) ed `extend` — la stessa escape-hatch di `createCrudStore`, per
// lo stato di dominio che una lista puo' avere e che il BB non conosce.
export function createListaStore(storeId, { options = {}, extend = null, ...core } = {}) {
  return defineStore(storeId, () => {
    const base = useListaStoreCore(core)
    // ⚠️ `extend` riceve il base COMPLETO e i suoi ritorni si mergiano sopra:
    //    e' cosi' che un caller aggiunge il proprio stato senza che il BB debba
    //    prevederlo. Chi sovrascrive una chiave del base lo fa apposta.
    return typeof extend === 'function'
      ? { ...base, ...extend(base) }
      : base
  }, { userScoped: true, ...options })
}
