// Pinia store per il log di audit globale (sola lettura, `storico.audit_log`).
//
// Nato con la conversione della pagina a `<ListaConfigurabile>` (2026-08-02):
// prima i filtri e la paginazione vivevano dentro `AuditLogView.vue`, ma lo
// scaffolding `useListaConfigurabilePage` vuole uno store che possieda
// `items`/`totalRecords`/`loading`/`filters`/`fetchList`.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getAuditLog } from '../api/amministrazione'
import { defaultFiltroDataDaString } from '../../core/utils/date'

export const useAuditLogStore = defineStore('amm-audit-log', () => {
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const hasSearched = ref(false)

  // Guard anti-race: la pagina cambia filtro piu' in fretta di quanto torni la
  // fetch (tre filtri tutti a portata di click). Senza, una risposta vecchia
  // puo' sovrascrivere una nuova.
  let fetchSeq = 0

  const filters = ref({
    // ⚠️ `search` esiste solo perche' `useSearchTable` ci scrive dentro: il
    // BE audit NON ha ricerca testuale (`AuditLogView` non legge `search`, e
    // nel seed tutte le colonne hanno `ricercabile_full=f`). Per questo la
    // pagina non mostra la casella di ricerca e `fetchList` non lo invia.
    search: '',
    tabella: null,
    // Floor temporale standard delle liste: oggi-60gg riportato al 1° del mese
    // (`feedback_filtro_data_liste`). Sostituisce il "ultimo mese" calcolato a
    // mano che stava nel .vue — stessa intenzione, ma dalla fonte unica.
    data_da: defaultFiltroDataDaString(),
    data_a: null,
    limit: 25,
    offset: 0,
    // Allineato all'`ordinamento_default` del preset `audit_log_default`
    // (seed `lista_preset`, riga 32): il piu' recente in cima.
    order_by: 'timestamp',
    order_dir: 'desc',
  })

  // Scopo: carica la pagina corrente del log di audit applicando i filtri.
  async function fetchList() {
    const seq = ++fetchSeq
    loading.value = true
    try {
      const f = filters.value
      const params = { limit: f.limit, offset: f.offset }
      if (f.tabella) params.tabella = f.tabella
      if (f.data_da) params.data_da = f.data_da
      if (f.data_a) params.data_a = f.data_a
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'desc'
      }
      const res = await getAuditLog(params)
      if (seq !== fetchSeq) return
      const data = res.data?.data || {}
      items.value = data.results || []
      totalRecords.value = data.count || 0
      hasSearched.value = true
    } finally {
      if (seq === fetchSeq) loading.value = false
    }
  }

  // ⚠️ `hasSearched` non serve a questa pagina — che non ha empty-state e parte
  //    piena — ma lo LEGGE `useSearchTable.onActivated` per decidere il refresh
  //    al rientro sotto KeepAlive: senza, quel rientro non ricarica niente e non
  //    lo dice nessuno. Gli store che passano da `useListaEmptyStateFetch` o
  //    dalle factory lo espongono da se'; questo e' scritto a mano, quindi va
  //    dichiarato qui.
  return { items, totalRecords, loading, hasSearched, filters, fetchList }
}, { userScoped: true })
