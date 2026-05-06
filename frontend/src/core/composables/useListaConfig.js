// Scopo: Composable di stato per la configurazione di una lista
//        personalizzabile. Gestisce:
//        - fetch della configurazione effettiva (cascata preset+permessi
//          risolta dal BE);
//        - fetch lazy del catalogo colonne arricchito (per la modale);
//        - mutazione locale della config (colonne, ordinamento, filtri,
//          pagina_dimensione) con tracking dirty;
//        - save (PUT preferenza con Idempotency-Key) e reset (DELETE
//          preferenza), entrambi seguiti da reload della config.
//
// Pattern: stato per-istanza (no cache modulo-level). Due tab sulla stessa
// lista fanno 2 fetch indipendenti — accettabile per MVP. Cache user-scoped
// (es. via useGlobalLookup) e' un'evoluzione successiva quando emergeranno
// hot path.
//
// Idempotency-Key: generata via crypto.randomUUID() ad ogni save (pattern
// gia' usato in catalogo.js per i comandi BoM).

import { ref, computed } from 'vue'
import { useApiHandler } from './useApiHandler'
import {
  getListaConfig,
  getListaCatalogo,
  putListaPreferenza,
  deleteListaPreferenza,
} from '../api/ui-api'

/**
 * Composable per una singola lista identificata da `codice`.
 *
 * @param {string} codice - codice stabile della lista (es. 'anagrafiche.clienti')
 * @returns {{
 *   config, catalogo, dirty, loading, savedSnapshot,
 *   load, ensureCatalogo, applyChange, save, reset
 * }}
 */
export function useListaConfig(codice) {
  // Configurazione corrente (mutata localmente da applyChange).
  // Shape allineata al payload accettato da PUT /preferenza/:
  //   {colonne[], ordinamento[], filtri{}, pagina_dimensione}
  // + colonne_nuove (read-only dal BE) per il badge UX.
  const config = ref(null)

  // Snapshot della config restituita dal server al load piu' recente.
  // Serve come baseline: dopo applyChange `dirty` diventa true; dopo
  // save() lo snapshot viene riallineato.
  const savedSnapshot = ref(null)

  // Catalogo colonne arricchito (lazy). Caricato al primo openModal.
  const catalogo = ref(null)

  // Flag locale "modifiche non salvate". Acceso da applyChange,
  // spento da load/save/reset.
  const dirty = ref(false)

  // Loading wrapper centralizzato (notify + extract error).
  const { execute, loading } = useApiHandler()

  // Scopo: Fetch della configurazione corrente. Reset di dirty + snapshot.
  //        Ritorna la config se ok, null se fallito (errore gia' notificato).
  async function load() {
    const data = await execute(() => getListaConfig(codice))
    if (data) {
      config.value = _deepClone(data)
      savedSnapshot.value = _deepClone(data)
      dirty.value = false
    }
    return data
  }

  // Scopo: Fetch del catalogo (lazy). No-op se gia' caricato.
  async function ensureCatalogo() {
    if (catalogo.value) return catalogo.value
    const data = await execute(() => getListaCatalogo(codice))
    if (data) {
      catalogo.value = data
    }
    return data
  }

  // Scopo: Applica una modifica locale alla config. Il chiamante
  //        (modale, toolbar) passa una funzione che muta `next` in place;
  //        il composable garantisce immutabilita' del riferimento esterno
  //        e segna dirty=true.
  //        Esempi:
  //          applyChange(c => { c.pagina_dimensione = 50 })
  //          applyChange(c => { c.colonne = riordinata })
  function applyChange(mutator) {
    if (!config.value) return
    const next = _deepClone(config.value)
    mutator(next)
    config.value = next
    dirty.value = true
  }

  // Scopo: Salva la preferenza corrente. Genera Idempotency-Key per la
  //        request. Dopo successo, ricarica la config dal server (per
  //        riprendere `colonne_nuove=0` e altri side effect).
  //
  // Nota sul reload post-save: se il PUT va a buon fine ma il GET di
  // reload fallisce (rete, timeout transitorio), la preferenza E' stata
  // salvata sul server ma `dirty` resta true e l'utente vede l'errore
  // del GET via toast. Riapertura del componente o refresh manuale
  // riallinea lo stato. Comportamento accettabile: il salvataggio non
  // viene perso, solo lo stato locale e' fuori sync temporaneamente.
  async function save() {
    if (!config.value) return null
    // Estrai solo i campi accettati dal BE (whitelist allineata a
    // ListaPreferenzaService._PAYLOAD_KEYS / _COLONNA_KEYS).
    //
    // Drift risk: questa whitelist FE deve restare sincronizzata con
    // quella BE (apps/ui/services/lista_preferenza_service.py). Se il BE
    // accetta nuove chiavi (es. `vista_compatta`), aggiungerle anche
    // qui — altrimenti il PUT non le invia. Se il BE rimuove chiavi,
    // il PUT le invierebbe ma il PayloadValidator BE le rifiuterebbe
    // con E_UI_PREFERENZA_VALIDAZIONE: errore parlante, no danni.
    const payload = _extractWritablePayload(config.value)
    const idempotencyKey = (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    const result = await execute(
      () => putListaPreferenza(codice, payload, idempotencyKey),
    )
    if (result !== null) {
      // Reload per riallineare lo snapshot con la versione canonica BE.
      await load()
    }
    return result
  }

  // Scopo: Reset preferenza utente. Dopo DELETE ricarica la config: il
  //        BE applichera' la cascata standard (preset di ruolo / emittente
  //        / sistema / catalogo grezzo).
  async function reset() {
    const result = await execute(() => deleteListaPreferenza(codice))
    if (result !== null) {
      await load()
    }
    return result
  }

  // Computed: count delle nuove colonne disponibili (badge UX).
  const colonneNuove = computed(() => config.value?.colonne_nuove ?? 0)

  return {
    config,
    catalogo,
    savedSnapshot,
    dirty,
    loading,
    colonneNuove,
    load,
    ensureCatalogo,
    applyChange,
    save,
    reset,
  }
}

// Scopo: Clona profondo via JSON. Sufficiente per la struttura della
//        config (no Date, no funzioni, no undefined).
function _deepClone(obj) {
  return JSON.parse(JSON.stringify(obj))
}

// Whitelist root del payload BE (allineata a ListaPreferenzaService).
// Sotto-whitelist colonna inline in _extractColonna.
const _PAYLOAD_ROOT_KEYS = ['colonne', 'ordinamento', 'filtri', 'pagina_dimensione']
const _COLONNA_KEYS = ['codice', 'ordine', 'larghezza', 'visibile', 'fissata']

function _extractWritablePayload(config) {
  const out = {}
  for (const k of _PAYLOAD_ROOT_KEYS) {
    if (config[k] !== undefined) out[k] = config[k]
  }
  if (Array.isArray(out.colonne)) {
    out.colonne = out.colonne.map(_extractColonna)
  }
  return out
}

function _extractColonna(c) {
  const out = {}
  for (const k of _COLONNA_KEYS) {
    if (c[k] !== undefined) out[k] = c[k]
  }
  return out
}
