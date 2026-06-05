// Building block: stato lista + guardia empty-state per le SearchTable che
// partono vuote (frontend-standards "Empty state — liste che partono vuote").
//
// Estratto 2026-06-03 (regola del 2): la guardia empty-state — search < 3
// caratteri ignorata, primo caricamento senza filtri resta vuoto, search
// svuotata senza filtri torna a stato vuoto — era duplicata bit-per-bit nei
// `fetchList` di 3 store vendite (offerte, preventivi, ordini). È la parte
// fragile/error-prone (i 3 reset di items/totalRecords/hasSearched vanno tenuti
// in sync); la centralizziamo qui.
//
// Ciò che resta al caller, perché DIVERGE legittimamente fra domini, sono i 3
// callback iniettati:
//  - `hasActiveFilters(f)` → bool: quali filtri contano come "ricerca attiva"
//    (stato/utility/date/listino/...). `data_da` default-anno-1 di solito conta,
//    così la lista si popola al mount.
//  - `buildParams(f, searchTerm)` → object: la mappatura filtri→query params,
//    che differisce per dominio (es. preventivi usa page/page_size, offerte e
//    ordini usano limit/offset; nomi filtri diversi). Riceve `searchTerm` già
//    trimmato: il caller decide se/come passarlo (tipicamente se length >= 3).
//  - `fetchPage(params)` → Promise di una response axios con envelope standard
//    `{ data: { data: { results, count } } }` (paginated_envelope BE).
//  - `alwaysFetch` (default false): se true salta i guard empty-state e carica
//    SEMPRE (liste che partono piene: admin, geo). Il search < 3 char resta
//    ignorato da `buildParams`, quindi la lista resta piena mentre si digita
//    (no flash vuoto). Usato dalla factory `createCrudStore` con startsEmpty:false.
//
// Ritorna lo stato reattivo (items/totalRecords/loading/hasSearched) + fetchList.
// Lo store espone questi ref nel proprio `return` insieme a `filters` e alle
// azioni CRUD.

import { ref } from 'vue'

export function useListaEmptyStateFetch({ filters, hasActiveFilters = () => false, buildParams, fetchPage, alwaysFetch = false }) {
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  async function fetchList() {
    const f = filters.value
    const searchTerm = (f.search || '').trim()

    // Guard empty-state: SOLO in modo "starts-empty" (default). In `alwaysFetch`
    // (liste che partono piene) si salta tutto e si carica sempre.
    if (!alwaysFetch) {
      const hasFilters = hasActiveFilters(f)
      // Search con meno di 3 caratteri e nessun filtro attivo → ignora (ed
      // eventualmente svuota se prima c'era un risultato).
      if (searchTerm.length > 0 && searchTerm.length < 3 && !hasFilters) {
        if (hasSearched.value) {
          items.value = []
          totalRecords.value = 0
          hasSearched.value = false
        }
        return
      }
      // Primo caricamento senza filtri → resta vuoto.
      if (!searchTerm && !hasFilters && !hasSearched.value) return
      // Search svuotata senza filtri → torna a stato vuoto.
      if (!searchTerm && !hasFilters) {
        items.value = []
        totalRecords.value = 0
        hasSearched.value = false
        return
      }
    }

    loading.value = true
    try {
      const res = await fetchPage(buildParams(f, searchTerm))
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
      hasSearched.value = true
    } finally {
      loading.value = false
    }
  }

  return { items, totalRecords, loading, hasSearched, fetchList }
}
