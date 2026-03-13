// Scopo: Composable generico per caricare e cachare dati di lookup.
// Supporta caricamento immediato o lazy, reload forzato, e stato loading.
// Cache per-istanza: ogni chiamata ha il proprio stato indipendente.

import { ref, onMounted } from 'vue'

/**
 * @param {Function} fetchFn - Funzione che ritorna una Promise (chiamata API axios)
 * @param {Object} options
 * @param {boolean} options.immediate - Se true, carica al mount (default: false)
 * @param {Function} options.transform - Trasforma la risposta axios in dati
 *   (default: r => r.data.data.results — envelope standard API ZeroERP)
 */
export function useLookup(fetchFn, options = {}) {
  const { immediate = false, transform = r => r.data.data.results } = options

  const items = ref([])
  const loading = ref(false)
  const loaded = ref(false)

  async function _fetch() {
    loading.value = true
    try {
      const res = await fetchFn()
      items.value = transform(res)
      loaded.value = true
    } finally {
      loading.value = false
    }
  }

  async function load() {
    if (loaded.value) return
    return _fetch()
  }

  async function reload() {
    loaded.value = false
    return _fetch()
  }

  if (immediate) {
    onMounted(load)
  }

  return { items, loading, loaded, load, reload }
}
