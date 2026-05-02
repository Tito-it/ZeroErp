// Scopo: Composable convenience-layer per leggere parametri default da
// `useParametersStore` (cache condivisa cross-drawer). API identica alla
// versione pre-refactor 2026-05-02 — i 6 chiamanti esistenti non cambiano.
//
// Internamente delega tutto allo store globale: cache, single-flight,
// invalidation, cross-tab sync, reset al logout. Vedi
// `src/stores/parameters.js`.
//
// Uso:
//   const { defaults, loading, load } = useParameterDefaults(['DEFAULT_IVA_ID'])
//   await load()
//   form.iva_id = defaults.value.DEFAULT_IVA_ID  // string — convertire se serve
//
// Per casi che richiedono invalidation/setOverride o reactivity esplicita
// per code, importare direttamente `useParametersStore`.

import { ref, computed } from 'vue'
import { useParametersStore } from '../../stores/parameters'

/**
 * @param {string[]} codes - Codici parametro da risolvere
 * @returns {{ defaults: ComputedRef<Object>, loading: Ref<boolean>, loaded: ComputedRef<boolean>, load: Function }}
 */
export function useParameterDefaults(codes) {
  const store = useParametersStore()

  // defaults reattivo: snapshot dei valori in cache per i codes richiesti.
  // Compatibile con il pattern legacy `paramDefaults.value.MY_CODE`. I codes
  // non ancora in cache appaiono come undefined (i consumer fanno gia'
  // controlli del tipo `if (paramDefaults.value.X)` o `?? fallback`).
  const defaults = computed(() => {
    const out = {}
    for (const c of codes) {
      const v = store.cache[c]
      if (v != null) out[c] = v
    }
    return out
  })

  // loaded = tutti i codes sono presenti in cache (anche con valore null,
  // che significa "BE non ha valore per questo code"). Reattivo: se lo
  // store invalida un code (es. broadcast cross-tab dopo override admin),
  // loaded torna a false e una nuova load() ri-fetcha.
  const loaded = computed(() => codes.every((c) => store.has(c)))

  // loading: per-istanza, true solo mentre la load() di QUESTA istanza
  // e' awaitata. Indipendente dallo stato dello store (che dedup le fetch
  // concorrenti). Pre-load() iniziale: false.
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      await store.ensure(codes)
    } finally {
      loading.value = false
    }
  }

  return { defaults, loading, loaded, load }
}
