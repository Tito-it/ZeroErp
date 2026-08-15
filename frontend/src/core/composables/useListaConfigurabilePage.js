// Scopo: scaffolding condiviso delle pagine lista basate su
// <ListaConfigurabile>. Estratto 2026-06-02 (regola del 2): le SearchTable
// di clienti/soggetti/fornitori/contratti ripetevano identici useSearchTable +
// ref alla lista (dirty/colonneNuove/configReady) + wiring export
// (useFileDownload/ExportDialog) + le 4 pageActions standard
// (reload/personalizza/export/new) + onConfigLoaded. Qui vivono una volta
// sola; il componente mantiene solo i propri filtri, slot e azioni di riga.
//
// Uso tipico:
//   const {
//     searchText, onPage, onSort, applyFilters, reload, paginatorProps,
//     tablePage, listaRef, dirty, configReady,
//     exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded,
//     pageActions,
//   } = useListaConfigurabilePage(store, {
//     exportFn: exportFornitori,
//     getExportParams: (fmt) => buildExportParams(fmt),
//     newTooltipKey: 'anagrafiche.fornitori.nuovo_fornitore',
//     onNew: () => emit('new'),
//     searchTableOptions: { defaultSortField: 'ragione_sociale_completa' },
//   })
//
// `getExportParams` e' invocata SOLO al click di export (lazy): puo' quindi
// riferire `searchText`/ref dei filtri definiti nel componente DOPO il
// destructuring (closure lazy). `extraActions` (opzionale) inserisce azioni
// utility custom prima di "Nuovo". `onReload` (opzionale) sostituisce il
// comando del pulsante "Ricarica" per le pagine che devono ricaricare anche
// altro insieme alla lista (il caller richiama `reload` dentro il proprio
// handler).

import { computed, ref, unref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSearchTable } from './useSearchTable'
import { useListaAzioni } from './useListaAzioni'
import { MANAGE_ICONS } from '../constants'

export function useListaConfigurabilePage(
  store,
  {
    exportFn,
    getExportParams = () => ({}),
    newTooltipKey,
    onNew,
    searchTableOptions = {},
    extraActions = null,
    onReload = null,
  } = {},
) {
  const { t } = useI18n()
  const search = useSearchTable(store, searchTableOptions)

  // Stato della lista configurabile + le due azioni di utility
  // (personalizza/export): vivono in `useListaAzioni`, sede unica condivisa
  // coi cruscotti, che non possono usare questo scaffolding (store diverso).
  const listaRef = ref(null)
  const {
    dirty, colonneNuove, configReady,
    exportDialogVisible, exportLoading, onExportConfirm,
    azioniLista,
  } = useListaAzioni(() => listaRef.value, { exportFn, getExportParams })

  // Allinea store.filters.limit alla pagina_dimensione risolta dal BE (una volta).
  const configAligned = ref(false)
  function onConfigLoaded(config) {
    if (configAligned.value) return
    configAligned.value = true
    const newLimit = config?.pagina_dimensione
    if (newLimit && newLimit !== store.filters.limit) {
      store.filters.limit = newLimit
      if (store.hasSearched) store.fetchList()
    }
  }

  const pageActions = computed(() => {
    const rawExtras =
      typeof extraActions === 'function'
        ? extraActions()
        : (extraActions?.value ?? extraActions ?? [])
    const extras = Array.isArray(rawExtras) ? rawExtras : []
    // `export` e `new` sono CONDIZIONATE al proprio handler: senza `exportFn`
    // il dialog si aprirebbe e `onExportConfirm` uscirebbe subito (pulsante
    // che non fa nulla), e senza `onNew` il comando sarebbe `undefined`.
    // Prima erano incondizionate e i caller senza "Nuovo" filtravano a mano —
    // stesso `filter(a => a.key !== 'new')` ripetuto in 3 file: la condizione
    // vive qui una volta sola (2026-07-31). La condizione su `exportFn` e' ora
    // dentro `useListaAzioni`, che produce le due azioni di lista.
    const conNew = typeof onNew === 'function'
    return [
      {
        key: 'reload',
        kind: 'utility',
        label: t('common.reload_list'),
        icon: MANAGE_ICONS.RELOAD,
        // `onReload` (opzionale) SOSTITUISCE il reload di lista quando la
        // pagina deve ricaricare anche altro insieme alla lista — es. il tab
        // BA emittente, dove il summary e' indipendente dalla pagina corrente
        // e senza di lui il pulsante "default" resta disallineato. Il caller
        // richiama `reload` (esposto qui sotto) dentro il proprio handler.
        command: onReload ?? search.reload,
      },
      ...azioniLista.value,
      ...extras,
      ...(conNew ? [{
        key: 'new',
        kind: 'primary',
        label: t('common.new'),
        tooltip: newTooltipKey ? t(newTooltipKey) : t('common.new'),
        icon: MANAGE_ICONS.ADD,
        hideWhenReadonly: true,
        command: onNew,
      }] : []),
    ]
  })

  // Pagina 1-based per <ListaConfigurabile :page>, con guard su rows>0
  // (evita Infinity/NaN se il limit fosse mai nullish). `paginatorProps` di
  // useSearchTable e' un ComputedRef: va unwrappato con `unref` (dentro JS non
  // c'e' l'auto-unwrap del template), altrimenti `.rows`/`.first` sono
  // undefined e la pagina resta bloccata a 1 (paginazione rotta).
  const tablePage = computed(() => {
    const pp = unref(search.paginatorProps)
    return pp?.rows ? pp.first / pp.rows + 1 : 1
  })

  return {
    ...search,
    tablePage,
    listaRef,
    dirty,
    colonneNuove,
    configReady,
    exportDialogVisible,
    exportLoading,
    onExportConfirm,
    onConfigLoaded,
    pageActions,
  }
}
