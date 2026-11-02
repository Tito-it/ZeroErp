// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: STACCARE UN VALORE DI FILTRO DAL LETTERALE CHE LO DICHIARA — la copia
//        profonda e il congelamento profondo dei `filterDefaults` di una lista.
// Note: ⛔ PERCHE' NON BASTA `{ ...filterDefaults }`, ed e' la forma di difetto
//        che questo repo paga piu' cara: lo spread e `Object.freeze` sono
//        entrambi di PRIMO LIVELLO. Con un default ad array — una multi-select
//        — `filtriDefault.stati` resta LO STESSO array del letterale dello
//        store, e `azzeraFiltri` lo riassegna ai filtri vivi per RIFERIMENTO.
//        Da quel momento il widget che ci scrive dentro (`push`, `splice`)
//        muta anche il default: il metro si sposta insieme alla cosa misurata,
//        `segnoFiltri` legge «sempre al default» per sempre e mostra il
//        il numero in GRIGIO su una lista che l'operatore ha ristretto a mano.
//        ⚠️ Nessun errore, da nessuna parte.
//
//       ⭐ IL CASO E' DICHIARATO AMMESSO DAL CONTRATTO, ed e' per questo che si
//        presidia anche senza occorrenze: `segnoFiltri.uguale()` tratta
//        apposta array e oggetti con `JSON.stringify`, e la sua spec ha il caso
//        del filtro ad array. Un ramo che il contratto dichiara ammesso va
//        provato per intero (`feedback_contratto_dichiarato_provalo_intero`),
//        non lasciato al «oggi nessuno store ha un default ad array» — che e'
//        l'assenza di un controesempio, non l'assenza del caso.
//
//       ⭐ TRE CONSUMATORI, UNA SEDE: `useListaStoreCore.filtriDiPartenza()` (i
//        valori di NASCITA), `useContrattoFiltriLista` (la fotografia del
//        default e «Pulisci filtri») e `useContrattoFiltriLocali` (le superfici
//        senza store-lista). Se la copia fosse profonda in uno solo dei tre, il
//        letterale resterebbe condiviso dagli altri due.
//
//       ⚠️ `structuredClone` non si usa: non attraversa le funzioni e solleva
//        su un `Proxy` reattivo di Vue, due cose che in un valore di filtro
//        possono capitare (un `_obj` di `bindLookup` letto da uno store
//        reattivo). Qui si copia cio' che un filtro puo' essere — scalare,
//        `Date`, array, oggetto semplice — e tutto il resto passa com'e'.
// ------------------------------------------------------------

// Scopo: la copia profonda di UN valore di filtro.
// ⚠️ La `Date` si duplica, non si condivide: e' mutabile (`setDate`) ed e' un
//    default vero — la data di validita' «oggi alla nascita» del drawer BoM.
export function clonaValore(v) {
  if (v instanceof Date) return new Date(v.getTime())
  if (Array.isArray(v)) return v.map(clonaValore)
  if (v !== null && typeof v === 'object') {
    return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, clonaValore(x)]))
  }
  return v
}

// Scopo: la copia profonda dell'INTERO letterale dei filtri di default.
export function clonaFiltri(defaults = {}) {
  return clonaValore({ ...defaults })
}

// Scopo: il congelamento PROFONDO — un consumatore non puo' cambiare il metro
//        nemmeno scrivendo dentro un array annidato.
// ⚠️ `Object.freeze` di primo livello impedisce `filtriDefault.stati = [...]` e
//    NON impedisce `filtriDefault.stati.push(...)`: il secondo e' proprio il
//    gesto che un widget fa.
export function congelaProfondo(v) {
  if (v !== null && typeof v === 'object' && !Object.isFrozen(v)) {
    Object.freeze(v)
    for (const x of Object.values(v)) congelaProfondo(x)
  }
  return v
}
