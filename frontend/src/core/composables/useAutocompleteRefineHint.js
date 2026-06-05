// Scopo: hint "affina la ricerca" per gli AutoComplete server-side che
//        limitano i risultati lato BE (B6 2026-06-05, regola del 2). Tiene
//        traccia di `total_count`/`limit` dell'ultima response per mostrare il
//        footer "mostrati N di M" quando il totale supera il limite. Azzera i
//        metadati su response nulla (query troppo corta o cancellata) per
//        evitare valori stale nel footer.
//
// Pattern identico in BillingAccountLookup + IstanzaUtilityLookup.
//
// Uso:
//   const { totalCount, limitShown, onResponse } = useAutocompleteRefineHint()
//   const ac = useServerAutocomplete(fetcher, { transform, onResponse })
//   <template #footer v-if="totalCount > limitShown && limitShown > 0">
//     {{ t('...refine_hint', { shown: limitShown, total: totalCount }) }}
//   </template>

import { ref } from 'vue'

export function useAutocompleteRefineHint() {
  const totalCount = ref(0)
  const limitShown = ref(0)

  function onResponse(res) {
    if (!res) {
      totalCount.value = 0
      limitShown.value = 0
      return
    }
    const data = res.data.data || {}
    totalCount.value = data.total_count || 0
    limitShown.value = data.limit || 0
  }

  return { totalCount, limitShown, onResponse }
}
