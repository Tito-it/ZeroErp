// Scopo: Composable degli OVERRIDE della pagina di gestione parametri
// (admin+self): `saveOverride` / `removeOverride` e gli scope ammessi.
// ⛔ Dal 2026-10-31 non carica piu' la lista: la lista e' a catalogo
//    (`config.parametri_impostazioni`), letta dallo store-lista
//    `useImpostazioniStore` con pagina e ricerca lato server. Prima qui c'era
//    il `load()` della lista intera, filtrata poi nel browser.
//
// Refactor 2026-05-02: gli override save/delete delegano allo
// `useParametersStore` per ottenere invalidation reattiva della cache
// (drawer aperti vedono il nuovo valore senza F5) + cross-tab sync via
// BroadcastChannel.
//
// Uso:
//   const { saveOverride, removeOverride } = useParameterSettings()

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
  const store = useParametersStore()

  // Delega allo store: invalidate + broadcast cross-tab automatici.
  // `options.categoriaClienteId` obbligatorio quando scope=CATEGORIA_CLIENTE
  // (il BE ritorna 400 E_PARAMETER_VALIDATION se manca o non positivo).
  async function saveOverride(parameterCode, value, scope = PARAMETER_SCOPE.USER, options = {}) {
    return store.setOverride(parameterCode, value, scope, options)
  }

  async function removeOverride(overrideId, parameterCode = null, scope = PARAMETER_SCOPE.USER, options = {}) {
    return store.removeOverride(overrideId, parameterCode, scope, options)
  }

  return { saveOverride, removeOverride }
}
