// Composable condiviso per il caricamento dettaglio row expansion nella ricerca universale.
// Usato da ClienteDetail, FornitoreDetail e GenericDetail per evitare duplicazione.

import { ref, watch } from 'vue'
import { dettaglioRicercaSoggetto } from '../api/ricerca'
import { useApiHandler } from './useApiHandler'

// Scopo: gestisce il caricamento lazy del dettaglio soggetto per tipo ruolo
// dal backend (fn_get_search_detail). Ritorna detailRows reattivi e stato loading.
export function useSearchDetail(props) {
  const { execute, loading } = useApiHandler()
  const detailRows = ref([])

  async function loadDetail() {
    if (!props.row?.soggetto_id) return
    const params = { tipo_ruolo_id: props.row.tipo_ruolo_id }
    const data = await execute(
      () => dettaglioRicercaSoggetto(props.row.soggetto_id, params),
      { silent: true }
    )
    if (data?.righe) {
      detailRows.value = data.righe
    }
  }

  watch(() => props.row?.soggetto_id, (val) => { if (val) loadDetail() }, { immediate: true })

  return { detailRows, loading }
}
