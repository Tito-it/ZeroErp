// Scopo: Store Pinia globale per i parametri di sistema (config.parameters)
// con risoluzione override utente. Sostituisce la cache per-istanza del
// composable `useParameterDefaults` con una cache condivisa cross-drawer.
//
// Benefici architetturali rispetto al composable per-istanza:
//   1. Coalescing: 4 drawer che chiedono lo stesso parametro → 1 sola fetch
//   2. Invalidation reattiva: dopo upsert/delete override, tutte le istanze
//      che leggono il parametro si aggiornano automaticamente
//   3. Cross-tab sync via BroadcastChannel: admin cambia override in tab A,
//      drawer in tab B (stesso utente) vede subito il nuovo valore
//   4. Reset al logout: `userScoped: true` + autoResetPlugin azzera la cache
//      per evitare leak cross-user sullo stesso browser
//
// API:
//   const params = useParametersStore()
//   await params.ensure(['DEFAULT_IVA_ID'])    // fetch dei codici mancanti (single-flight)
//   const v = params.get('DEFAULT_IVA_ID')      // sync getter, null se non caricato
//   params.invalidate(['DEFAULT_IVA_ID'])       // forza refetch alla prossima ensure
//   await params.setOverride(code, value, scope)
//   await params.removeOverride(overrideId, code, scope)

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  fetchParameterDefaults,
  upsertParameterOverride,
  deleteParameterOverride,
} from '../core/apiCore'

// Nome canale BroadcastChannel cross-tab. Costante per evitare typo silenziosi
// tra producer (postMessage) e consumer (onmessage).
const BC_CHANNEL = 'zeroerp-parameters'

// BroadcastChannel: sync cross-tab degli invalidate. Lazy init per
// non rompere SSR/test environment senza BroadcastChannel API.
function makeBroadcastChannel() {
  if (typeof BroadcastChannel === 'undefined') return null
  try {
    return new BroadcastChannel(BC_CHANNEL)
  } catch {
    return null
  }
}

export const useParametersStore = defineStore('parameters', () => {
  // Cache reattiva: { [code]: value | null }. Una chiave presente ma null
  // significa "code richiesto al BE che ha ritornato nessun valore" — non
  // ri-fetchiamo. Una chiave assente significa "mai richiesto".
  const cache = ref({})

  // Coordina il single-flight per code: se un fetch e' in volo per X,
  // chiamate successive per X aspettano la stessa promise. Plain Map (non
  // reattivo: usato solo come coordination primitive nelle action).
  const inFlightByCode = new Map()

  // Session token: incrementato a ogni clearUserState (logout). Le fetch
  // in volo che risolvono dopo un logout vengono scartate per non popolare
  // la cache dell'utente successivo (cross-user data leak).
  let sessionToken = 0

  // BroadcastChannel cross-tab. Lazy.
  let bc = null
  function ensureBroadcast() {
    if (bc !== null) return bc
    bc = makeBroadcastChannel()
    if (bc) {
      bc.onmessage = (e) => {
        if (e.data?.type === 'invalidate' && Array.isArray(e.data.codes)) {
          // Invalida senza ri-broadcast (eviterebbe loop infinito tra tab).
          invalidate(e.data.codes, { broadcast: false })
        }
      }
    }
    return bc
  }

  // Scopo: sync getter del valore risolto per `code`. Ritorna null sia se
  // il code non e' stato richiesto (cache miss) sia se e' stato richiesto e
  // il BE ha ritornato no-value. Per distinguere usare `has(code)`.
  function get(code) {
    return cache.value[code] ?? null
  }

  function has(code) {
    return code in cache.value
  }

  // Scopo: garantisce che i `codes` siano caricati in cache. Esegue una
  // sola fetch per i codes mancanti, condividendo le promise in volo cosi'
  // chiamate concorrenti convergono. Errore di rete: silente, lascia i
  // codes assenti dalla cache (la prossima ensure ritenta).
  async function ensure(codes) {
    if (!codes || codes.length === 0) return
    const codesToFetch = []
    const promisesToWait = []

    for (const c of codes) {
      if (has(c)) continue
      const inFlight = inFlightByCode.get(c)
      if (inFlight) {
        promisesToWait.push(inFlight)
      } else {
        codesToFetch.push(c)
      }
    }

    if (codesToFetch.length > 0) {
      // Snapshot del session token al momento del fetch: se nel frattempo
      // arriva un clearUserState (logout) il token bumpa e i risultati
      // vengono scartati prima di scrivere sulla cache dell'utente nuovo.
      const myToken = sessionToken
      const promise = (async () => {
        try {
          const res = await fetchParameterDefaults(codesToFetch)
          if (myToken !== sessionToken) return  // logout in flight: discard
          const data = res.data?.data || {}
          // Settiamo TUTTI i codes richiesti, anche quelli senza valore
          // (BE non li ritorna): null in cache evita refetch ripetuti.
          // Spread per triggerare reattivita' su consumer che leggono
          // computed(() => store.get(code)).
          const next = { ...cache.value }
          for (const c of codesToFetch) {
            next[c] = c in data ? data[c] : null
          }
          cache.value = next
        } catch {
          // Silent: i codes mancano dalla cache → la prossima ensure
          // ritenta. Coerente col composable originale (default non
          // bloccanti per l'apertura del form).
        } finally {
          // Solo se siamo nello stesso ciclo di sessione, altrimenti la
          // Map e' gia' stata svuotata da clearUserState.
          if (myToken === sessionToken) {
            for (const c of codesToFetch) inFlightByCode.delete(c)
          }
        }
      })()
      for (const c of codesToFetch) inFlightByCode.set(c, promise)
      promisesToWait.push(promise)
    }

    await Promise.all(promisesToWait)
  }

  // Scopo: rimuove i `codes` dalla cache forzando il refetch alla prossima
  // ensure. Default broadcast=true: notifica le altre tab dello stesso
  // browser/utente cosi' anche loro invalidano. Override interno
  // broadcast=false e' usato dall'handler BroadcastChannel per evitare
  // loop di rebroadcast.
  function invalidate(codes, { broadcast = true } = {}) {
    if (!codes || codes.length === 0) return
    const next = { ...cache.value }
    for (const c of codes) delete next[c]
    cache.value = next
    if (broadcast) {
      const channel = ensureBroadcast()
      if (channel) {
        try {
          channel.postMessage({ type: 'invalidate', codes })
        } catch {
          // BroadcastChannel chiuso: ignora, non e' bloccante.
        }
      }
    }
  }

  // Scopo: upsert override + invalidate del code. La cache verra'
  // ripopolata al prossimo `ensure`. Lo scope ('user' | 'emittente') segue
  // la convenzione BE (apps/core/api/views_parameters.py).
  async function setOverride(parameterCode, value, scope = 'user') {
    const res = await upsertParameterOverride(parameterCode, value, scope)
    invalidate([parameterCode])
    return res.data?.data
  }

  // Scopo: delete override + invalidate. Il caller passa anche `code`
  // per invalidare la cache (l'API delete prende solo l'id override).
  async function removeOverride(overrideId, parameterCode, scope = 'user') {
    const res = await deleteParameterOverride(overrideId, scope)
    if (parameterCode) invalidate([parameterCode])
    return res.data?.data
  }

  // Scopo: contratto autoResetPlugin (vedi core/pinia-plugins/auto-reset.js).
  // Al logout azzera la cache, bumpa il session token (le fetch in volo
  // che risolvono dopo questo punto scartano i loro risultati), cancella
  // le promise in volo, chiude il BroadcastChannel (re-istanziato al
  // prossimo ensure).
  function clearUserState() {
    sessionToken++
    cache.value = {}
    inFlightByCode.clear()
    if (bc) {
      try { bc.close() } catch { /* noop */ }
      bc = null
    }
  }

  return {
    cache,
    get, has, ensure, invalidate,
    setOverride, removeOverride,
    clearUserState,
  }
}, {
  // Reset automatico al logout (autoResetPlugin in core/pinia-plugins/
  // auto-reset.js): la cache parametri puo' contenere override personali
  // dell'utente loggato. Niente leak cross-user.
  userScoped: true,
})
