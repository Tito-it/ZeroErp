// Store Pinia dell'elenco «fondi fattura da decidere» (lista configurabile
// `vendite.fondi_fattura_da_decidere`, ui.lista_definizione id 44 — seedata il
// 2026-08-15 e rimasta SENZA consumatore frontend fino al 2026-08-22).
//
// Interfaccia useSearchTable-compatibile (items/totalRecords/loading/filters/
// fetchList/hasSearched), la stessa che pretende `useListaConfigurabilePage`.
//
// ⭐ Semantica CODA DI LAVORO, non lista storica: `alwaysFetch: true` e NESSUN
// floor temporale di default. Il floor standard delle liste (oggi-60gg al 1°
// del mese, `defaultFiltroDataDa`) qui nasconderebbe proprio il lavoro
// arretrato — e una riga «da decidere» vecchia di tre mesi e' quella che pesa
// di piu', non quella che conta meno. Stessa scelta delle due code resi e
// delle due code Strumenti.
//
// userScoped: reset al logout (memoria feedback_pinia_userscoped) — lo stato
// di filtri e pagina e' dell'operatore, non del browser.

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { listFondiFatturaDaDecidere } from '../api/fondiFattura'

// Scopo: mappa i filtri dello store nei query param dell'endpoint.
//
// ⚠️ L'endpoint e' PAGE-BASED (`page`/`page_size`), mentre `useSearchTable`
// governa `limit`/`offset`: la conversione sta QUI, una volta, invece che nel
// componente. `Math.floor` con guard sul limit: un `limit` a 0 produrrebbe una
// divisione per zero e una `page` NaN, che il backend rifiuterebbe con un 400
// incomprensibile.
//
// ⚠️ La `search` NON si inoltra: questo endpoint non ha ricerca testuale.
// Passarla sarebbe un parametro ignorato in silenzio — l'operatore digiterebbe
// e vedrebbe la lista intera, convinto di aver cercato. Il campo di ricerca
// infatti non e' montato nella pagina.
function buildParams(f) {
  const pageSize = f.limit > 0 ? f.limit : 25
  const p = {
    page: Math.floor((f.offset || 0) / pageSize) + 1,
    page_size: pageSize,
  }
  if (f.motivo) p.motivo = f.motivo
  if (f.order_by) {
    p.order_by = f.order_by
    p.order_dir = f.order_dir || 'desc'
  }
  return p
}

export const useFondiFatturaDaDecidereStore = defineStore(
  'vendite-fondi-fattura-da-decidere',
  () => {
    const filters = ref({
      // Vocabolario chiuso dei quattro motivi (null = tutti).
      motivo: null,
      limit: 25,
      offset: 0,
      // Default `data desc`, lo stesso che applica il backend quando non gli
      // si dice nulla: la lista non si riordina sotto gli occhi
      // dell'operatore al primo caricamento.
      order_by: 'data',
      order_dir: 'desc',
    })

    const { items, totalRecords, loading, hasSearched, fetchList } =
      useListaEmptyStateFetch({
        filters,
        buildParams,
        fetchPage: listFondiFatturaDaDecidere,
        alwaysFetch: true,
      })

    return { items, totalRecords, loading, hasSearched, filters, fetchList }
  },
  { userScoped: true },
)
