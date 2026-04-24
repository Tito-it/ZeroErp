// Scopo: Cache di lookup modulo-level, condivisa fra tutte le istanze Vue
//        del processo. Evita fetch duplicate quando piu' SearchTable / Drawer
//        richiedono la stessa tabella codici (tipologie, stati, tipi_indirizzi...).
//
//        Differenze vs useLookup:
//        - cache per-chiave string -> tutti i consumer dello stesso key
//          condividono lo stesso items/loading/loaded
//        - primo consumer fa la fetch, i successivi attendono la stessa
//          Promise in volo (no thundering herd)
//        - `invalidate(key)` esportato per refresh mirato dopo CRUD admin
//        - `invalidateAll()` per logout / switch tenant
//
//        Riferimento: sviluppo-listini-v6.md §2.1 (V6-F1).
//
// Uso tipico:
//
//   import { useGlobalLookup, invalidateLookup } from '@/core/composables/useGlobalLookup'
//   import { lookupCodici } from '@/core/apiCore'
//
//   const { items, loading, load, reload } = useGlobalLookup(
//     'config.listini_tipologie',
//     () => lookupCodici('config.listini_tipologie'),
//     { immediate: true }
//   )
//
//   // dopo una mutation admin della tabella sorgente:
//   invalidateLookup('config.listini_tipologie')

import { ref, onMounted } from 'vue'
import { registerUserScopedResetter } from '../pinia-plugins/auto-reset'

// Struttura cache: Map<string, {
//   itemsRef: Ref<any[]>,           // lista reattiva condivisa
//   loadingRef: Ref<boolean>,       // flag loading condiviso
//   loadedRef: Ref<boolean>,        // true dopo prima fetch completata
//   errorRef: Ref<Error | null>,    // ultimo errore fetch (condiviso)
//   inFlight: Promise<void> | null, // promise corrente (dedup concorrenza)
//   fetchFn: Function,              // funzione di fetch registrata (per reload)
//   transform: Function,            // trasformazione risposta
// }>
const _cache = new Map()

// Default envelope ZeroERP: `response.data.data.results`.
const _defaultTransform = (r) => r.data.data.results

// Scopo: Accede o crea l'entry di cache per la chiave. Registra la fetchFn
//        e il transform al primo accesso; non li sovrascrive per accessi
//        successivi (il primo consumer "vince" — evita cambiamenti silenziosi
//        se due callsite passano funzioni leggermente diverse).
function _getEntry(key, fetchFn, transform) {
  let entry = _cache.get(key)
  if (!entry) {
    entry = {
      itemsRef: ref([]),
      loadingRef: ref(false),
      loadedRef: ref(false),
      errorRef: ref(null),
      inFlight: null,
      fetchFn,
      transform,
    }
    _cache.set(key, entry)
  }
  return entry
}

// Scopo: Esegue la fetch per la chiave indicata; se una fetch e' gia' in
//        volo, riusa la stessa promise (dedup). Aggiorna gli stati reattivi.
//        In caso di errore: `errorRef` viene valorizzato (visibile a tutti i
//        consumer reattivi), `loadedRef` resta false. La promise rigetta e
//        viene azzerata: il prossimo load() riprova. Niente retry automatico.
function _fetchEntry(entry) {
  if (entry.inFlight) return entry.inFlight
  entry.loadingRef.value = true
  entry.errorRef.value = null
  entry.inFlight = (async () => {
    try {
      const res = await entry.fetchFn()
      entry.itemsRef.value = entry.transform(res)
      entry.loadedRef.value = true
    } catch (err) {
      // Propaga l'errore ai consumer reattivi (non solo a chi ha await-ato).
      entry.errorRef.value = err
      throw err
    } finally {
      entry.loadingRef.value = false
      entry.inFlight = null
    }
  })()
  return entry.inFlight
}

/**
 * Composable lookup con cache modulo-level condivisa per-chiave.
 *
 * @param {string} key - chiave cache (tipicamente nome tabella: 'config.listini_tipologie')
 * @param {Function} fetchFn - funzione che ritorna una Promise axios
 * @param {Object} options
 * @param {boolean} options.immediate - se true, carica al mount (default: false)
 * @param {Function} options.transform - trasforma la risposta (default envelope ZeroERP)
 */
export function useGlobalLookup(key, fetchFn, options = {}) {
  const { immediate = false, transform = _defaultTransform } = options
  // IMPORTANTE: `key` viene letto al setup e legato all'istanza. Se il
  // consumer passa un prop reattivo che puo' cambiare (es. rel dinamico
  // in un Select), deve re-mountare il componente via `:key` sul template
  // o migrare alla versione con watch esterna. Questa limitazione e'
  // deliberata: la cache e' per-chiave stabile, non per-istanza.
  const entry = _getEntry(key, fetchFn, transform)

  // Espongo direttamente le ref del cache store: sono gia' reattive e
  // stabili per-chiave. Il computed che usavo prima era ridondante
  // (nessuna trasformazione, solo aliasing) — review.
  const items = entry.itemsRef
  const loading = entry.loadingRef
  const loaded = entry.loadedRef
  const error = entry.errorRef

  // Scopo: Carica la lista se non gia' caricata (no-op se loaded o in volo).
  //        Non re-tenta automaticamente dopo errore: il consumer decide.
  async function load() {
    if (entry.loadedRef.value) return
    return _fetchEntry(entry)
  }

  // Scopo: Forza un re-fetch ignorando lo stato loaded. Usato quando si
  //        sa che la sorgente e' cambiata (es. post-mutation) o per
  //        recovery manuale dopo errore.
  async function reload() {
    entry.loadedRef.value = false
    entry.errorRef.value = null
    return _fetchEntry(entry)
  }

  if (immediate) {
    // onMounted non propaga rejection — chi usa `immediate: true` non
    // await-a il risultato, quindi attach un `.catch` silente che scrive
    // solo in errorRef (gia' fatto da _fetchEntry) per evitare
    // unhandled-promise warnings in console.
    onMounted(() => {
      load().catch(() => { /* errore gia' in errorRef */ })
    })
  }

  return { items, loading, loaded, error, load, reload }
}

/**
 * Invalidazione mirata della cache per una chiave. Marca l'entry come
 * non-caricata: il prossimo consumer che chiama load() rifa la fetch.
 * Non triggera un re-fetch automatico (i consumer gia' montati vedranno
 * gli items vecchi finche' qualcuno non chiama reload).
 *
 * @param {string} key
 */
export function invalidateLookup(key) {
  const entry = _cache.get(key)
  if (!entry) return
  entry.loadedRef.value = false
  entry.errorRef.value = null
  entry.inFlight = null
}

/**
 * Reset completo della cache. Da chiamare al logout o su switch utente
 * per evitare che i lookup del precedente utente restino visibili.
 */
export function invalidateAllLookups() {
  _cache.forEach((entry) => {
    entry.loadedRef.value = false
    entry.errorRef.value = null
    entry.inFlight = null
    entry.itemsRef.value = []
  })
  _cache.clear()
}

// Scopo: Esposizione solo per test o introspection debug. NON usare
//        in codice applicativo — considerato API privata.
export const _internalCache = _cache

// Registrazione al reset centralizzato del logout: la cache lookup puo'
// contenere dati filtrati per permessi dell'utente loggato (es. emittenti
// fiscali visibili, utilities abilitate, ecc.), quindi va svuotata al
// cambio utente per evitare leak cross-user. Registrata una sola volta
// al caricamento del modulo.
registerUserScopedResetter(invalidateAllLookups)
