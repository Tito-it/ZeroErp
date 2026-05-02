// Scopo: Composable per la pagina di gestione parametri (admin+self):
// carica la lista completa con tutti i livelli di scope (default,
// emittente, gruppo, utente) e fornisce metodi CRUD override.
//
// Refactor 2026-05-02: gli override save/delete delegano allo
// `useParametersStore` per ottenere invalidation reattiva della cache
// (drawer aperti vedono il nuovo valore senza F5) + cross-tab sync via
// BroadcastChannel.
//
// Uso:
//   const { parameters, loading, load, saveOverride, removeOverride } = useParameterSettings()
//   await load()

import { ref } from 'vue'
import { fetchParameterSettings } from '../apiCore'
import { useParametersStore } from '../../stores/parameters'

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
  const store = useParametersStore()

  async function load() {
    loading.value = true
    try {
      const res = await fetchParameterSettings()
      parameters.value = res.data.data || []
    } finally {
      loading.value = false
    }
  }

  // Delega allo store: invalidate + broadcast cross-tab automatici.
  async function saveOverride(parameterCode, value, scope = PARAMETER_SCOPE.USER) {
    return store.setOverride(parameterCode, value, scope)
  }

  async function removeOverride(overrideId, parameterCode = null, scope = PARAMETER_SCOPE.USER) {
    return store.removeOverride(overrideId, parameterCode, scope)
  }

  return { parameters, loading, load, saveOverride, removeOverride }
}
