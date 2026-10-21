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
// ⭐ Quarto consumatore: `CommessaGestioneDrawer` (2026-09-30, regola del 2),
// che aveva questa forma scritta a mano — e che l'aveva gia' vista divergere:
// partiva dalla misura di PAGINA dentro un drawer.
//
// ⭐ FAIL-VISIBLE, dentro il BB (2026-09-30). Le fetch che parte il BB da solo
// — cambio pagina, ordinamento, allineamento al preset — non hanno un
// chiamante che le attenda: un errore li' era una promise rifiutata che
// nessuno guardava, e a video restava la pagina di prima come se niente
// fosse. Ora `carica` lo mostra (toast con il messaggio dell'API) e lascia
// le righe com'erano; non rilancia, cosi' chi la attende insieme ad altro non
// mostra lo stesso errore due volte. Era la regola della copia della
// commessa: «una tabella vuota per errore non deve sembrare "nessuna riga"».
//
// USO:
//   const doc = useListaDrawerPaginata(({ limit, offset, sortBy, sortDir }) =>
//     listaFatture(lottoId, { limit, offset, order_by: sortBy, order_dir: sortDir }))
//   ...
//   <ListaConfigurabile :rows="doc.righe.value" :total="doc.totale.value" ... />
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { USO_MISURA, misuraDefault, misureOpzioni } from '../misurePagina'
import { extractApiError } from '../utils/apiError'
import { useNotify } from './useNotify'

/**
 * @param {Function} fetcher - riceve `{limit, offset, sortBy, sortDir}` e
 *   ritorna la RESPONSE axios della lista. Il composable non sa nulla
 *   dell'endpoint: sa solo che la risposta ha la forma dell'envelope lista.
 *   ⭐ `limit`/`offset` e non `page`/`pageSize` (2026-10-21, un dialetto
 *   solo): la pagina e' lo stato del PAGINATORE, la finestra e' cio' che il
 *   backend legge — la traduzione sta QUI, una volta.
 * @param {Object} opzioni
 * @param {string|null} opzioni.sortBy - ordinamento iniziale (default: nessuno,
 *   cioè l'ordine storico dell'endpoint).
 * @param {number} opzioni.sortDir - 1 asc, -1 desc.
 */
export function useListaDrawerPaginata(fetcher, { sortBy = null, sortDir = 1 } = {}) {
  const notify = useNotify()
  const { t } = useI18n()
  const righe = ref([])
  const totale = ref(0)
  const loading = ref(false)
  const page = ref(1)
  // ⭐ La misura COMPATTA: e' la lista di un drawer (catalogo `ui.misure_pagina`,
  //    decisione di Tid del 2026-09-28). Fino al 2026-09-30 partiva dalla misura
  //    di pagina, contro la regola; il preset della lista, se ne dichiara una,
  //    vince comunque al primo `config-loaded`.
  const pageSize = ref(misuraDefault(USO_MISURA.COMPATTA))
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
        limit: pageSize.value,
        offset: (page.value - 1) * pageSize.value,
        sortBy: sortField.value,
        // ⚠️ Il BE parla `asc`/`desc`, il DataTable 1/-1: la traduzione sta
        // QUI, una volta, invece che in ogni chiamante.
        sortDir: sortOrder.value === -1 ? 'desc' : 'asc',
      })
      const dati = res?.data?.data ?? {}
      righe.value = dati.results ?? []
      totale.value = dati.count ?? 0
    } catch (err) {
      notify.error(extractApiError(err, t('common.error')))
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
    rowsPerPageOptions: misureOpzioni(),
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
