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
// PARAMETER_SCOPE.USER              → override personale (default)
// PARAMETER_SCOPE.EMITTENTE         → override aziendale (riservato admin)
// PARAMETER_SCOPE.CATEGORIA_CLIENTE → override per categoria cliente (riservato
//                                     admin, richiede `categoriaClienteId`;
//                                     Phase B 2026-05-19 cascata parametri).
export const PARAMETER_SCOPE = Object.freeze({
  USER: 'user',
  EMITTENTE: 'emittente',
  CATEGORIA_CLIENTE: 'categoria_cliente'
})

export function useParameterSettings() {
  const parameters = ref([])
  const loading = ref(false)
  const store = useParametersStore()

  // Accetta `options.categoria_cliente_id` (esplicito) o
  // `options.billing_account_id` (derivato lato BE) per attivare il livello
  // categoria_cliente nella cascata visualizzata. Default: tutti NULL,
  // colonna categoria_cliente nel display resta vuota.
  async function load(options = {}) {
    loading.value = true
    try {
      const res = await fetchParameterSettings(options)
      parameters.value = res.data.data || []
    } finally {
      loading.value = false
    }
  }

  // Delega allo store: invalidate + broadcast cross-tab automatici.
  // `options.categoriaClienteId` obbligatorio quando scope=CATEGORIA_CLIENTE
  // (il BE ritorna 400 E_PARAMETER_VALIDATION se manca o non positivo).
  async function saveOverride(parameterCode, value, scope = PARAMETER_SCOPE.USER, options = {}) {
    return store.setOverride(parameterCode, value, scope, options)
  }

  async function removeOverride(overrideId, parameterCode = null, scope = PARAMETER_SCOPE.USER, options = {}) {
    return store.removeOverride(overrideId, parameterCode, scope, options)
  }

  return { parameters, loading, load, saveOverride, removeOverride }
}
