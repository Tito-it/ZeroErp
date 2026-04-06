// Scopo: Composable generico per gestione parametri di sistema con override.
// Carica la lista completa dei parametri con i livelli di scope
// (default, emittente, gruppo, utente) e fornisce metodi per CRUD override.
//
// Uso:
//   const { parameters, loading, load, saveOverride, removeOverride } = useParameterSettings()
//   await load()

import { ref } from 'vue'
import { fetchParameterSettings, upsertParameterOverride, deleteParameterOverride } from '../apiCore'

// Scope override consentiti dal backend (allineati a backend/apps/core/api/views_parameters.py).
// PARAMETER_SCOPE.USER     → override personale (default)
// PARAMETER_SCOPE.EMITTENTE → override aziendale (riservato admin)
export const PARAMETER_SCOPE = Object.freeze({
  USER: 'user',
  EMITTENTE: 'emittente'
})

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

  async function saveOverride(parameterCode, value, scope = PARAMETER_SCOPE.USER) {
    const res = await upsertParameterOverride(parameterCode, value, scope)
    return res.data.data
  }

  async function removeOverride(overrideId, scope = PARAMETER_SCOPE.USER) {
    const res = await deleteParameterOverride(overrideId, scope)
    return res.data.data
  }

  return { parameters, loading, load, saveOverride, removeOverride }
}
