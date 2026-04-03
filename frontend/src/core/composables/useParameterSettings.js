// Scopo: Composable generico per gestione parametri di sistema con override.
// Carica la lista completa dei parametri con i livelli di scope
// (default, emittente, gruppo, utente) e fornisce metodi per CRUD override.
//
// Uso:
//   const { parameters, loading, load, saveOverride, removeOverride } = useParameterSettings()
//   await load()

import { ref } from 'vue'
import { fetchParameterSettings, upsertParameterOverride, deleteParameterOverride } from '../apiCore'

export function useParameterSettings() {
  const parameters = ref([])
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const res = await fetchParameterSettings()
      parameters.value = res.data.data || []
    } finally {
      loading.value = false
    }
  }

  async function saveOverride(parameterCode, value) {
    const res = await upsertParameterOverride(parameterCode, value)
    return res.data.data
  }

  async function removeOverride(overrideId) {
    const res = await deleteParameterOverride(overrideId)
    return res.data.data
  }

  return { parameters, loading, load, saveOverride, removeOverride }
}
