// Scopo: ⭐ LO STATO DI UNA LISTA CONFIGURABILE DENTRO UN DRAWER — pagina,
// ordinamento, righe, totale — con i tre gestori che `<ListaConfigurabile>`
// si aspetta (`@page`, `@sort`, `@config-loaded`).
//
// ⚠️ NON è `useListaConfigurabilePage`: quello è costruito su `useSearchTable`
// e pretende uno store con la forma «ricerca testuale + sort + limit», che è la
// forma di una PAGINA lista. Qui le righe sono pilotate dal drawer (un id
// padre, i suoi filtri) e lo store non c'è. È lo stesso caso per cui era stato
// estratto `useListaAzioni`, che infatti si usa insieme a questo.
//
// ⭐ ESTRATTO alla terza copia nello stesso file (drawer del lotto di
// fatturazione, 2026-08-22): i suoi tre tab sono tre liste, e scrivere tre
// volte lo stesso `onPage`/`onSort`/`paginatorOptions` significa tre occasioni
// di dimenticare l'azzeramento della pagina al cambio ordinamento — un difetto
// che non si vede finché qualcuno non ordina stando a pagina 3 e trova un
// elenco vuoto.
// 📌 Quarto consumatore naturale: `CommessaGestioneDrawer`, che ha esattamente
// questa forma scritta a mano.
//
// USO:
//   const doc = useListaDrawerPaginata(({ page, pageSize, sortBy, sortDir }) =>
//     listaFatture(lottoId, { page, page_size: pageSize, sort_by: sortBy, sort_dir: sortDir }))
//   ...
//   <ListaConfigurabile :rows="doc.righe.value" :total="doc.totale.value" ... />
import { computed, ref } from 'vue'
import { PAGINATION } from '../constants'

/**
 * @param {Function} fetcher - riceve `{page, pageSize, sortBy, sortDir}` e
 *   ritorna la RESPONSE axios della lista. Il composable non sa nulla
 *   dell'endpoint: sa solo che la risposta ha la forma dell'envelope lista.
 * @param {Object} opzioni
 * @param {string|null} opzioni.sortBy - ordinamento iniziale (default: nessuno,
 *   cioè l'ordine storico dell'endpoint).
 * @param {number} opzioni.sortDir - 1 asc, -1 desc.
 */
export function useListaDrawerPaginata(fetcher, { sortBy = null, sortDir = 1 } = {}) {
  const righe = ref([])
  const totale = ref(0)
  const loading = ref(false)
  const page = ref(1)
  const pageSize = ref(PAGINATION.DEFAULT_ROWS)
  const sortField = ref(sortBy)
  const sortOrder = ref(sortDir)
  // La dimensione pagina risolta dal BE si applica UNA volta sola: dopo, il
  // valore lo governa l'operatore dal paginatore, e riapplicare il preset gli
  // annullerebbe la scelta a ogni ricarica.
  const configAllineata = ref(false)

  async function carica() {
    loading.value = true
    try {
      const res = await fetcher({
        page: page.value,
        pageSize: pageSize.value,
        sortBy: sortField.value,
        // ⚠️ Il BE parla `asc`/`desc`, il DataTable 1/-1: la traduzione sta
        // QUI, una volta, invece che in ogni chiamante.
        sortDir: sortOrder.value === -1 ? 'desc' : 'asc',
      })
      const dati = res?.data?.data ?? {}
      righe.value = dati.results ?? []
      totale.value = dati.count ?? 0
    } finally {
      loading.value = false
    }
  }

  function onPage(event) {
    page.value = Math.floor(event.first / event.rows) + 1
    pageSize.value = event.rows
    carica()
  }

  function onSort(event) {
    sortField.value = event.sortField ?? null
    sortOrder.value = event.sortOrder ?? 1
    // ⚠️ Si torna a pagina 1: ordinare stando a pagina 3 lascerebbe l'operatore
    // in mezzo a un elenco che non è più quello che stava guardando.
    page.value = 1
    carica()
  }

  function onConfigLoaded(config) {
    if (configAllineata.value) return
    configAllineata.value = true
    const nuovo = config?.pagina_dimensione
    if (nuovo && nuovo !== pageSize.value) {
      pageSize.value = nuovo
      page.value = 1
      carica()
    }
  }

  // Prop del paginatore composte dallo stato del drawer: qui non c'è
  // `useSearchTable` a fornirle.
  const paginatorOptions = computed(() => ({
    totalRecords: totale.value,
    rows: pageSize.value,
    first: (page.value - 1) * pageSize.value,
    rowsPerPageOptions: PAGINATION.ROWS_OPTIONS,
  }))

  // Scopo: riporta la lista allo stato iniziale (riapertura del drawer su un
  //        altro padre). ⚠️ Azzera anche `configAllineata`: il preset della
  //        lista va riapplicato, perché la scelta dell'operatore valeva per la
  //        sessione precedente.
  function reset() {
    righe.value = []
    totale.value = 0
    page.value = 1
    sortField.value = sortBy
    sortOrder.value = sortDir
    configAllineata.value = false
  }

  return {
    righe, totale, loading, page, pageSize, sortField, sortOrder,
    paginatorOptions, carica, reset, onPage, onSort, onConfigLoaded,
  }
}
