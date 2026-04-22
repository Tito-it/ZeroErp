// Scopo: Composable per caricare limiti L2 variazione prezzo dell'utente
//        corrente (max_sconto_pct + max_maggiorazione_pct).
//        Cache modulo-level: la prima view che lo invoca fa la fetch,
//        le successive riusano stessa reference reattiva. Un invalidate()
//        permette di ricaricare post-override admin.
//
// Uso tipico (drawer riga preventivo):
//   const { limiti, load } = useLimitiPricing()
//   onMounted(load)
//   // in template: sconto_max_pct = Number(limiti.value.max_sconto_pct)
//
// Rationale cache modulo: i limiti cambiano raramente (config server-side)
// e servono in piu' drawer diversi — evitiamo N round-trip.

import { ref } from 'vue'
import { getLimitiPricingUtente } from '../api/listini'

// Codici errore L2 emessi dal BE preventivi_service quando l'override
// prezzo supera il limite. Il FE li intercetta per banner inline (vs toast
// standard). Allineati con apps/vendite/services/pricing_service.L2_ERROR_CODES.
// Freeze per prevenire mutazioni accidentali.
const L2_ERROR_CODES = Object.freeze([
  'E_PREV_SCONTO_ECCESSIVO',
  'E_PREV_MAGGIORAZIONE_ECCESSIVA',
])

const _limiti = ref({ max_sconto_pct: '0', max_maggiorazione_pct: '0' })
const _loaded = ref(false)
const _loading = ref(false)
let _inflight = null

// Scopo: Carica i limiti se non ancora caricati (idempotente + dedup
//        thundering herd: consumer simultanei condividono la Promise).
async function load() {
  if (_loaded.value) return
  if (_inflight) return _inflight
  _loading.value = true
  _inflight = getLimitiPricingUtente()
    .then(res => {
      _limiti.value = res.data.data || _limiti.value
      _loaded.value = true
    })
    .catch(() => {
      // Errore silenzioso: in fallback usiamo i default '0' (safe,
      // il BE blocchera' l'override se non ammesso).
    })
    .finally(() => {
      _loading.value = false
      _inflight = null
    })
  return _inflight
}

// Scopo: Forza il ricarico dei limiti (es. post-cambio override admin
//        oppure logout/login). Reset cache + re-fetch opzionale.
function invalidate(reload = false) {
  _loaded.value = false
  _limiti.value = { max_sconto_pct: '0', max_maggiorazione_pct: '0' }
  if (reload) return load()
}

export function useLimitiPricing() {
  return {
    limiti: _limiti,
    loading: _loading,
    loaded: _loaded,
    load,
    invalidate,
    L2_ERROR_CODES,
  }
}
