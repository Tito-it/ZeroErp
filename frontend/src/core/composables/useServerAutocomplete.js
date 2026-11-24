// Scopo: Composable generico per autocomplete con ricerca server-side.
// Gestisce debounce, loading, min length, e trasformazione risposta.
// Lo usano tutti gli autocomplete del progetto: cliente, fornitura, soggetto,
// articolo, fattura, comune, stradario, conto bancario, filiale.
//
// ⭐ 2026-11-24 (brief-be-fe-BB-audit §7.1 F-1, regola del 2, ok Tid): il timer
//    e' quello di `useDebouncedAction`, la guardia anti-race quella di
//    `useFetchVersion`. Fino a quel giorno qui c'era un `setTimeout` scritto a
//    mano, con due difetti che si vedevano a video:
//    · si spegneva solo su `onUnmounted`: una ricerca digitata appena prima di
//      cambiare scheda (KeepAlive) partiva con la scheda in background;
//    · non scartava le risposte superate: la risposta lenta a «ros» poteva
//      arrivare dopo quella a «rossi» e scriverci sopra i suggerimenti.
// ⭐ Il ritardo e' 300 ms, e non `SEARCH_DEBOUNCE_MS` (400, la ricerca di una
//    lista), per scelta (Tid, 2026-11-24, D-6): una tendina risponde a chi sta
//    scegliendo una voce, e aspetta le proposte mentre scrive; una lista si
//    rilegge per intero, e ogni ricerca in meno e' una pagina in meno.

import { ref, onDeactivated, onUnmounted } from 'vue'
import { useDebouncedAction } from './useDebouncedAction'
import { useFetchVersion } from './useFetchVersion'

// Ritardo di un autocomplete (vedi sopra: diverso da SEARCH_DEBOUNCE_MS per scelta).
export const AUTOCOMPLETE_DEBOUNCE_MS = 300

/**
 * @param {Function} searchFn - Funzione che riceve (query) e ritorna Promise axios
 * @param {Object} options
 * @param {number|Function} options.minLength - Lunghezza minima query (default: 2).
 *   Puo' essere una funzione per soglie dinamiche (es. 0 quando il lookup ha
 *   gia' un perimetro contestuale e deve listare al click della tendina).
 * @param {number} options.debounceMs - Debounce in ms (default: AUTOCOMPLETE_DEBOUNCE_MS)
 * @param {Function} options.transform - Trasforma risposta (default: r => r.data.data.results)
 * @param {Function} options.onResponse - Callback opzionale con la response completa (per leggere total_count, meta, ecc.)
 */
export function useServerAutocomplete(searchFn, options = {}) {
  const {
    minLength = 2,
    debounceMs = AUTOCOMPLETE_DEBOUNCE_MS,
    transform = r => r.data.data.results,
    onResponse = null
  } = options

  const suggestions = ref([])
  const loading = ref(false)
  const noResults = ref(false)
  const versione = useFetchVersion()

  // Scopo: la chiamata vera, a debounce scaduto. Una risposta che non e' piu'
  //        quella dell'ultima ricerca si scarta: non scrive i suggerimenti e non
  //        spegne il `loading` di quella che la sostituisce.
  async function cerca(query) {
    const t = versione.tag()
    try {
      const res = await searchFn(query)
      if (!versione.isCurrent(t)) return
      suggestions.value = transform(res)
      if (onResponse) onResponse(res)
      noResults.value = suggestions.value.length === 0
    } catch {
      if (!versione.isCurrent(t)) return
      suggestions.value = []
      noResults.value = true
    } finally {
      if (versione.isCurrent(t)) loading.value = false
    }
  }

  const ricerca = useDebouncedAction(cerca, { delayMs: debounceMs, detailed: true })

  // Scopo: abbandona la ricerca in attesa e quella in volo (query troppo
  //        corta, scheda in background, componente smontato).
  function abbandona() {
    ricerca.cancel()
    versione.invalidate()
    loading.value = false
  }

  function onSearch({ query }) {
    noResults.value = false

    const effectiveMin = typeof minLength === 'function' ? minLength() : minLength
    if ((query || '').length < effectiveMin) {
      abbandona()
      suggestions.value = []
      // Notifica anche sul path "troppo corto" per consentire ai consumer
      // di azzerare metadati stale (es. total_count del footer "affina").
      if (onResponse) onResponse(null)
      return
    }

    // Un tasto nuovo rende vecchia anche la risposta gia' in volo.
    versione.invalidate()
    loading.value = true
    ricerca.run(query)
  }

  function clearNoResults() {
    noResults.value = false
  }

  // `useDebouncedAction` spegne gia' il timer; qui si spegne anche il resto
  // (la risposta in volo e la rotellina).
  onDeactivated(abbandona)
  onUnmounted(abbandona)

  return { suggestions, loading, noResults, clearNoResults, onSearch }
}
