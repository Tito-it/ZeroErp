// Scopo: Composable per caricare limiti L2 variazione prezzo (cascata
//        estesa 2026-05-15: max_sconto_pct + max_maggiorazione_pct risolti
//        con user -> categoria_cliente -> group -> emittente -> default).
//
//        Cache modulo-level **per chiave BA** (oppure per default senza BA):
//        la cascata BE include il livello categoria del BA destinatario,
//        quindi clienti con categoria diversa hanno limiti diversi. La cache
//        deve essere chiave dal BA per evitare di mostrare i limiti del
//        cliente precedente a un cliente nuovo.
//
// Uso tipico (drawer riga preventivo):
//   const { limiti, load } = useLimitiPricing()
//   watch(() => testata.billing_account_id, load, { immediate: true })
//   // in template: sconto_max_pct = Number(limiti.value.max_sconto_pct)
//
// Rationale cache: i limiti cambiano raramente (config server-side) ma
// dipendono dal BA destinatario. Evitiamo refetch quando l'operatore torna
// sullo stesso BA, refresh forzato via invalidate() post-override admin.

import { ref } from 'vue'
import { getLimitiPricingUtente } from '../api/listini'
import { registerUserScopedResetter } from '../../core/pinia-plugins/auto-reset'

// Codici errore L2 emessi dal BE preventivi_service quando l'override
// prezzo supera il limite. Il FE li intercetta per banner inline (vs toast
// standard). Allineati con apps/vendite/services/pricing_service.L2_ERROR_CODES.
// Freeze per prevenire mutazioni accidentali.
const L2_ERROR_CODES = Object.freeze([
  'E_PRICING_SCONTO_ECCESSIVO',
  'E_PRICING_MAGGIORAZIONE_ECCESSIVA',
])

const _DEFAULT = { max_sconto_pct: '0', max_maggiorazione_pct: '0' }

// `_limiti` espone i limiti CORRENTI (ultimo BA richiesto). I valori per BA
// sono memoizzati in `_cache` mappato per chiave (BA id o '__user__' per
// chiamata senza BA).
const _limiti = ref({ ..._DEFAULT })
const _loading = ref(false)
const _cache = new Map() // key -> { max_sconto_pct, max_maggiorazione_pct }
const _inflight = new Map() // key -> Promise (dedup thundering herd per key)

function _cacheKey(baId) {
  return baId != null && baId !== '' ? `ba:${baId}` : '__user__'
}

// Scopo: Carica i limiti per il BA fornito (cascata BE include categoria
//        cliente). Idempotente per chiave: se gia' cached, restituisce
//        subito dalla cache senza round-trip. Se senza BA, cascata "generica"
//        utente. `baId` puo' essere null/undefined.
async function load(baId = null) {
  const key = _cacheKey(baId)
  // Cache hit: imposta i limiti correnti e ritorna.
  if (_cache.has(key)) {
    _limiti.value = _cache.get(key)
    return
  }
  // Dedup richieste concorrenti per la stessa chiave.
  if (_inflight.has(key)) return _inflight.get(key)
  _loading.value = true
  const promise = getLimitiPricingUtente(baId)
    .then(res => {
      const data = res.data?.data || { ..._DEFAULT }
      _cache.set(key, data)
      _limiti.value = data
    })
    .catch(() => {
      // Errore silenzioso: fallback default '0' (safe — il BE blocchera'
      // comunque l'override se non ammesso).
      _cache.set(key, { ..._DEFAULT })
      _limiti.value = { ..._DEFAULT }
    })
    .finally(() => {
      _loading.value = false
      _inflight.delete(key)
    })
  _inflight.set(key, promise)
  return promise
}

// Scopo: Forza il reset della cache (es. post-cambio override admin oppure
//        logout/login). Resetta tutte le chiavi e i limiti correnti.
function invalidate(reload = false) {
  _cache.clear()
  _inflight.clear()
  _limiti.value = { ..._DEFAULT }
  if (reload) return load()
}

// Cache module-level NON user-scoped per default: registriamo l'invalidate
// nel resetter centrale Pinia cosi' al logout (resetAllUserScopedStores)
// la cache viene azzerata. Senza questo, login successivo come altro
// utente vedeva i limiti del precedente.
registerUserScopedResetter(() => invalidate(false))

export function useLimitiPricing() {
  return {
    limiti: _limiti,
    loading: _loading,
    load,
    invalidate,
    L2_ERROR_CODES,
  }
}
