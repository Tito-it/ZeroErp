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
//   const { bindSelect, bindDate, bindToggle, bindLookup } = useStoreFilterBindings(store, applyFilters)
//   const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato')
//   const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da')
//   const { value: soloNegativa, onChange: onSoloNegativaChange } = bindToggle('solo_negativa')
//   const { value: articoloFilter, onChange: onArticoloChange } = bindLookup('articolo_id')
//   // template: v-model="statoFilter" @change="onStatoChange"
//   //           v-model="dataDaFilter" @date-select="onDataDaChange" ...
//   //           <FiltroToggle v-model="soloNegativa" @change="onSoloNegativaChange" />
//   //           <ArticoloLookup v-model="articoloFilter" @update:model-value="onArticoloChange" />
//
// ⭐ LA DISCIPLINA COMUNE AI QUATTRO: `onChange` scatta SOLO da un evento
//    utente nel template, mai da un `watch` sul widget. Il `watch` c'e', ma
//    nel verso opposto (store → widget), per i cambi fatti FUORI dal widget —
//    `useSearchTable` che azzera i default data su una ricerca esterna, un
//    reset, un deep-link: l'operatore deve sempre vedere il valore che limita
//    la lista. Cosi' non c'e' nessun loop da guardare.
//
// `buildExportParams` resta caller-side: la mappatura filtri→query export
// diverge per ogni lista (rename `data_a`→`data_al`/`validita_dal_max`,
// `solo_ultima_revisione` string-cast, `scadenza_mese` YYYY-MM) e ingabbiarla qui
// sarebbe un config piu' lungo del codice che sostituisce.

import { computed, ref, watch } from 'vue'
import { parseIsoDate, toDateString } from '../utils/date'

export function useStoreFilterBindings(store, applyFilters) {
  // Filtro select/valore semplice: ref inizializzato dallo store, onChange
  // riscrive lo store e rilancia la fetch. Il watch store→ref tiene la
  // toolbar allineata anche quando il filtro viene cambiato FUORI dal
  // widget (es. useSearchTable che azzera i default data su ricerca
  // esterna): l'operatore deve sempre vedere il valore che limita la lista.
  // Nessun loop: onChange scatta solo da evento utente, mai dal watch.
  function bindSelect(storeKey, { defaultValue = null } = {}) {
    const value = ref(store.filters[storeKey] ?? defaultValue)
    watch(() => store.filters[storeKey], (nuovo) => {
      value.value = nuovo ?? defaultValue
    })
    function onChange() {
      store.filters[storeKey] = value.value
      applyFilters()
    }
    return { value, onChange }
  }

  // Filtro data: ref Date local-safe dallo store (ISO 'YYYY-MM-DD'), onChange
  // serializza con `toDateString`. `clearTo` (opzionale) ripristina un floor
  // quando l'utente cancella (es. contratti: il floor standard, la lista ne vuole uno).
  // Stesso sync store→ref di bindSelect (vale solo per i cambi esterni:
  // il floor clearTo resta legato al gesto utente di svuotamento).
  function bindDate(storeKey, { clearTo = null } = {}) {
    const value = ref(parseIsoDate(store.filters[storeKey]))
    watch(() => store.filters[storeKey], (nuovo) => {
      value.value = parseIsoDate(nuovo)
    })
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

  // Filtro INTERRUTTORE (`FiltroToggle`): il widget e' un booleano, lo store
  // porta il valore che il backend legge — e non e' sempre `true`/`false`.
  // Estratto il 2026-09-19 (regola del 2, ok Tid) da CINQUE siti con TRE forme:
  // un ref + onChange (pratiche), un computed get/set INVERTITO (offerte e
  // preventivi: «mostra storico» acceso ⇔ `solo_ultima_revisione = false`),
  // un computed get/set che scrive `true | null` (disponibilita').
  //
  // `on` / `off` sono i DUE valori dello store: acceso ⇒ `store = on`, spento
  // ⇒ `store = off`, e il widget e' acceso quando `store === on`. Coprono
  // entrambe le divergenze senza un flag `inverti`: offerte passa
  // `{ on: false, off: true }`, disponibilita' i default.
  // ⚠️ `off` e' `null` di default, non `false`: il core manda ogni filtro
  //    `!= null`, e un `false` sul filo sarebbe un parametro che il backend
  //    legge senza che filtri niente. Chi ha `false` come default dello store
  //    (pratiche) lo dichiara.
  // Il `value` e' un computed sullo store, non un ref copiato: un cambio da
  // fuori (reset, logout) si vede da se', senza il watch di sync.
  function bindToggle(storeKey, { on = true, off = null } = {}) {
    const value = computed({
      get: () => store.filters[storeKey] === on,
      set: (acceso) => { store.filters[storeKey] = acceso ? on : off },
    })
    function onChange() {
      applyFilters()
    }
    return { value, onChange }
  }

  // Filtro LOOKUP RICCO (`ArticoloLookup`, `BillingAccountLookup`…): il
  // widget tiene l'OGGETTO scelto (gli serve per mostrarlo), lo store l'id.
  // Estratto il 2026-09-19 (regola del 2, ok Tid) dalle due copie identiche
  // del registro e della disponibilita' di magazzino.
  //
  // Verso widget → store: `onChange` alla scelta o al clear (i lookup ricchi
  // emettono `update:modelValue` in entrambi i casi), `store = obj[idField]`.
  // ⚠️ Nel template `v-model` PRECEDE `@update:model-value`: Vue accoda i
  //    listener nell'ordine in cui sono scritti, e `onChange` legge il ref
  //    che il `v-model` ha appena aggiornato — come per `bindSelect` con
  //    `@update:model-value`.
  // Verso store → widget: SOLO l'azzeramento. Un id NON null messo da fuori
  // non si rende: il widget vuole l'oggetto e da un id non lo si ricostruisce
  // senza una lettura by-id. Oggi nessun deep-link lo fa; il giorno che
  // servira' e' un'opzione `risolvi(id) -> Promise<obj>` qui, non un watch
  // nel chiamante.
  function bindLookup(storeKey, { idField = 'id' } = {}) {
    const value = ref(null)
    watch(() => store.filters[storeKey], (id) => {
      if (id == null) value.value = null
    })
    function onChange() {
      store.filters[storeKey] = value.value?.[idField] ?? null
      applyFilters()
    }
    return { value, onChange }
  }

  return { bindSelect, bindDate, bindToggle, bindLookup }
}
