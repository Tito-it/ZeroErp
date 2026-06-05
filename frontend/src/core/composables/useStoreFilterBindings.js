// Scopo: binding toolbar filtri ↔ store.filters per le liste (B14 2026-06-05,
//        regola del 2). Le SearchTable vendite (ordini/offerte/contratti/
//        preventivi) ripetevano per ogni filtro la coppia
//        `const xFilter = ref(store.filters.key ?? null)` +
//        `function onXChange() { store.filters.key = xFilter.value; applyFilters() }`,
//        e per le date un parse ISO→Date inline **non uniforme** (contratti
//        usava `new Date(iso)` → timezone-shift; gli altri `T00:00:00`
//        local-safe). Qui le primitive centralizzano ref + handler usando
//        sempre `parseIsoDate`/`toDateString` local-safe.
//
// I binder ritornano `{ value, onChange }` con `value` = il **ref** (non
// unwrappato): il consumer lo destruttura coi propri nomi storici, cosi' il
// template resta invariato.
//
//   const { bindSelect, bindDate } = useStoreFilterBindings(store, applyFilters)
//   const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato')
//   const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da')
//   // template: v-model="statoFilter" @change="onStatoChange"
//   //           v-model="dataDaFilter" @date-select="onDataDaChange" ...
//
// `buildExportParams` resta caller-side: la mappatura filtri→query export
// diverge per ogni lista (rename `data_a`→`data_al`/`validita_dal_max`,
// `solo_attiva` string-cast, `scadenza_mese` YYYY-MM) e ingabbiarla qui
// sarebbe un config piu' lungo del codice che sostituisce.

import { ref } from 'vue'
import { parseIsoDate, toDateString } from '../utils/date'

export function useStoreFilterBindings(store, applyFilters) {
  // Filtro select/valore semplice: ref inizializzato dallo store, onChange
  // riscrive lo store e rilancia la fetch.
  function bindSelect(storeKey, { defaultValue = null } = {}) {
    const value = ref(store.filters[storeKey] ?? defaultValue)
    function onChange() {
      store.filters[storeKey] = value.value
      applyFilters()
    }
    return { value, onChange }
  }

  // Filtro data: ref Date local-safe dallo store (ISO 'YYYY-MM-DD'), onChange
  // serializza con `toDateString`. `clearTo` (opzionale) ripristina un floor
  // quando l'utente cancella (es. contratti: anno-1, la lista vuole un floor).
  function bindDate(storeKey, { clearTo = null } = {}) {
    const value = ref(parseIsoDate(store.filters[storeKey]))
    function onChange() {
      if (!value.value && clearTo) {
        const fallback = clearTo()
        value.value = fallback
        store.filters[storeKey] = toDateString(fallback)
      } else {
        store.filters[storeKey] = value.value ? toDateString(value.value) : null
      }
      applyFilters()
    }
    return { value, onChange }
  }

  return { bindSelect, bindDate }
}
