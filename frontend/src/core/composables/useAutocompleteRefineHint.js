// Scopo: hint "affina la ricerca" per gli AutoComplete server-side che
//        limitano i risultati lato BE (B6 2026-06-05, regola del 2). Tiene
//        traccia dell'ultima response per dire a chi guarda che l'elenco NON e'
//        completo. Azzera i metadati su response nulla (query troppo corta o
//        cancellata) per evitare valori stale nel footer.
//
// ⭐ DUE MODI DI SAPERE CHE L'ELENCO E' TAGLIATO, e il composable li serve
//    entrambi (2026-09-10) — perche' a video la domanda e' UNA sola:
//
//    | Cosa manda il backend        | Chi                              | Cosa si puo' dire |
//    | ---------------------------- | -------------------------------- | ----------------- |
//    | `total_count` + `limit`      | billing account, istanze, sogg.  | «mostrati N di M» |
//    | `troncato` + `count`         | lookup articoli (sonda `+1`)     | «i primi N, ce ne sono altri» |
//
// ⛔ La seconda riga NON puo' dire un totale, ed e' voluto: la sonda `+1` costa
//    zero proprio perche' NON conta l'insieme (`fetch_con_sonda`, backend). Chi
//    rende sceglie la frase; qui si risponde solo a «va affinata?».
//
// 🔴 PERCHE' IL SECONDO MODO E' ARRIVATO QUI E NON DENTRO `ArticoloLookup`
//    (2026-09-10): il backend dichiarava `troncato` dal giorno prima e a video
//    non lo leggeva nessuno — campo emesso e non consumato. Cablarlo nel
//    componente avrebbe creato la seconda sede della stessa frase, e il lookup
//    piu' usato dell'app avrebbe detto in un modo suo una cosa che gli altri
//    quattro dicono gia' in un altro.
//
// ⚠️ `daAffinare` esiste perche' la condizione era scritta **tre volte** nei
//    template (`totalCount > limitShown && limitShown > 0`): tre copie di un
//    predicato che ora ha due rami, cioe' tre punti da correggere ogni volta
//    che ne nasce un terzo.
//
// Uso:
//   const { daAffinare, mostrati, totalCount, onResponse } = useAutocompleteRefineHint()
//   const ac = useServerAutocomplete(fetcher, { transform, onResponse })
//   <template #footer v-if="daAffinare">
//     {{ t('...refine_hint', { shown: mostrati, total: totalCount }) }}   // col totale
//     {{ t('common.refine_hint_troncato', { shown: mostrati }) }}         // senza totale
//   </template>

import { computed, ref } from 'vue'

export function useAutocompleteRefineHint() {
  const totalCount = ref(0)
  const limitShown = ref(0)
  const troncato = ref(false)
  const consegnati = ref(0)

  function onResponse(res) {
    if (!res) {
      totalCount.value = 0
      limitShown.value = 0
      troncato.value = false
      consegnati.value = 0
      return
    }
    const data = res.data.data || {}
    totalCount.value = data.total_count || 0
    limitShown.value = data.limit || 0
    // ⚠️ `count` di un lookup e' il numero di righe CONSEGNATE, non il totale
    //    (api.md §«Il `count` non si deriva MAI dalle righe che stai
    //    consegnando»): si usa per dire «i primi N», mai per dire «di M».
    troncato.value = data.troncato === true
    consegnati.value = data.count || 0
  }

  // Quante righe si stanno mostrando: `limit` dichiarato dal backend dove c'e',
  // altrimenti quelle consegnate.
  const mostrati = computed(() => limitShown.value || consegnati.value)

  // L'unica domanda che il footer deve porsi, con i suoi due rami.
  const daAffinare = computed(
    () => troncato.value || (totalCount.value > limitShown.value && limitShown.value > 0),
  )

  return { totalCount, limitShown, troncato, mostrati, daAffinare, onResponse }
}
