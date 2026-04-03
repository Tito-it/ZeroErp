// Scopo: Composable per caricare valori default da config.parameters
// con risoluzione override utente via API /api/v1/core/parameters/defaults/.
// Riusabile da qualsiasi drawer/form che necessita di default di sistema.
//
// Uso:
//   const { defaults, loading, load } = useParameterDefaults(['DEFAULT_IVA_ID'])
//   await load()
//   form.iva_id = defaults.value.DEFAULT_IVA_ID  // stringa — convertire se serve

import { ref } from 'vue'
import { fetchParameterDefaults } from '../apiCore'

/**
 * @param {string[]} codes - Codici parametro da risolvere
 * @returns {{ defaults: Ref<Object>, loading: Ref<boolean>, loaded: Ref<boolean>, load: Function }}
 */
export function useParameterDefaults(codes) {
  const defaults = ref({})
  const loading = ref(false)
  const loaded = ref(false)

  async function load() {
    if (loaded.value) return
    if (!codes || codes.length === 0) return
    loading.value = true
    try {
      const res = await fetchParameterDefaults(codes)
      defaults.value = res.data.data || {}
      loaded.value = true
    } catch {
      // Errore silenzioso: i default non sono bloccanti per l'apertura del form.
      // Il campo resta vuoto e l'operatore puo' selezionare manualmente.
    } finally {
      loading.value = false
    }
  }

  return { defaults, loading, loaded, load }
}
