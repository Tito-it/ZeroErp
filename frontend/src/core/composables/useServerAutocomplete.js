// Scopo: Composable generico per autocomplete con ricerca server-side.
// Gestisce debounce, loading, min length, e trasformazione risposta.
// Usato da ComuneAutocomplete e StradarioAutocomplete.

import { ref, onUnmounted } from 'vue'

/**
 * @param {Function} searchFn - Funzione che riceve (query) e ritorna Promise axios
 * @param {Object} options
 * @param {number} options.minLength - Lunghezza minima query (default: 2)
 * @param {number} options.debounceMs - Debounce in ms (default: 300)
 * @param {Function} options.transform - Trasforma risposta (default: r => r.data.data.results)
 */
export function useServerAutocomplete(searchFn, options = {}) {
  const {
    minLength = 2,
    debounceMs = 300,
    transform = r => r.data.data.results
  } = options

  const suggestions = ref([])
  const loading = ref(false)
  const noResults = ref(false)
  let debounceTimer = null

  function onSearch({ query }) {
    clearTimeout(debounceTimer)
    noResults.value = false

    if (!query || query.length < minLength) {
      suggestions.value = []
      return
    }

    loading.value = true
    debounceTimer = setTimeout(async () => {
      try {
        const res = await searchFn(query)
        suggestions.value = transform(res)
        noResults.value = suggestions.value.length === 0
      } catch {
        suggestions.value = []
        noResults.value = true
      } finally {
        loading.value = false
      }
    }, debounceMs)
  }

  function clearNoResults() {
    noResults.value = false
  }

  onUnmounted(() => clearTimeout(debounceTimer))

  return { suggestions, loading, noResults, clearNoResults, onSearch }
}
