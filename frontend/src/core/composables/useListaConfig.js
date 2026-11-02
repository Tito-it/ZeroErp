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
// Idempotency-Key: l'`Idempotency-Key` la mette l'interceptor di `core/api.js` (§A5, 2026-10-20).

import { ref, computed } from 'vue'
import { useApiHandler } from './useApiHandler'
import {
  getListaConfig,
  getListaCatalogo,
  putListaPreferenza,
  deleteListaPreferenza,
  ignorePresetUpdate as apiIgnorePresetUpdate,
} from '../api/ui-api'
import { chiaviScelte } from '../preferenzaPerChiave'

/**
 * Composable per una singola lista identificata da `codice`.
 *
 * @param {string} codice - codice stabile della lista (es. 'anagrafiche.clienti')
 * @param {object} [opzioni]
 * @param {Function|string|number} [opzioni.emittenteEsplicito] - l'emittente
 *   gia' fissato dal contesto che apre la lista (getter o valore). Viaggia
 *   verso il backend, che ne ricava `richiede_scelta_emittente`.
 * @returns {{
 *   config, catalogo, dirty, loading, savedSnapshot,
 *   load, ensureCatalogo, applyChange, save, reset
 * }}
 */
export function useListaConfig(codice, opzioni = {}) {
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

  // Scopo: Fetch della configurazione corrente + catalogo colonne in
  //        parallelo. Il catalogo era originariamente lazy (caricato solo
  //        all'apertura della modale di personalizzazione), ma e' tornato
  //        load-eager perche' l'header colonna (etichetta + i18n key) e
  //        il `campo_sorgente` da cui estrarre i dati di riga vivono nel
  //        catalogo. Senza catalogo le colonne renderizzano `codice` come
  //        header e cercano `data[codice]` invece di `data[campo_sorgente]`,
  //        risultando in label/dati sbagliati al primo render
  //        (sintomo: lista clienti che mostra "ragione_sociale" come
  //        header e usa il campo errato per estrarre la ragione sociale).
  //        Reset di dirty + snapshot. Ritorna la config se ok, null se
  //        fallita (errore gia' notificato; il catalogo e' best-effort:
  //        un suo fallimento isolato non azzera la config).
  // Scopo: l'emittente esplicito al momento della fetch. Si accetta un GETTER
  //        oltre al valore: nel drawer l'id puo' arrivare dopo il primo render,
  //        e un valore letto una volta sola resterebbe quello di allora.
  // ⚠️ Qui non si normalizza niente: cosa valga come «assente» lo decide
  //    `getListaConfig`, che e' il punto in cui il parametro finisce sul filo.
  function _emittenteEsplicito() {
    return typeof opzioni.emittenteEsplicito === 'function'
      ? opzioni.emittenteEsplicito()
      : opzioni.emittenteEsplicito
  }

  async function load() {
    const [configData, catalogoData] = await Promise.all([
      execute(() => getListaConfig(codice, {
        emittenteEsplicito: _emittenteEsplicito(),
      })),
      execute(() => getListaCatalogo(codice)),
    ])
    if (configData) {
      config.value = _deepClone(configData)
      savedSnapshot.value = _deepClone(configData)
      dirty.value = false
    }
    if (catalogoData) {
      catalogo.value = catalogoData
    }
    return configData
  }

  // Scopo: Garantisce che il catalogo sia disponibile (compat per chi
  //        chiamava ensureCatalogo prima del refactor eager-load). Oggi
  //        no-op se `load()` e' gia' stata invocata. Caso d'uso residuo:
  //        chiamanti che invocano openModal senza load preventivo (es.
  //        viste future con config pre-caricata da contesto).
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

  // Scopo: Salva la preferenza corrente. Dopo successo, ricarica la config dal server (per
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
    // ⭐ Per chiave (2026-11-01, BB `preferenzaPerChiave`): solo le chiavi
    //    scelte — gia' della preferenza o toccate —, le altre restano «come lo
    //    standard». Nessuna chiave scelta = nessuna preferenza: DELETE.
    const payload = _extractWritablePayload(
      chiaviScelte(config.value, savedSnapshot.value, _PAYLOAD_ROOT_KEYS),
    )
    if (Object.keys(payload).length === 0) return reset()
    const result = await execute(
      () => putListaPreferenza(codice, payload),
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

  // Computed DEF-2: TRUE quando il preset di base e' stato modificato
  // dall'admin dopo lo snapshot della preferenza utente E l'utente non
  // ha dismissato il banner per quella versione del preset. Calcolato
  // lato DB da `fn_resolve_lista_config`: passthrough qui.
  // `?? false` fallback safe: se il DB non espone ancora il campo
  // (brief team DB non atterrato), il banner FE resta nascosto.
  const presetAggiornato = computed(
    () => config.value?.preset_aggiornato ?? false,
  )

  // Scopo: DEF-2 — "Ignora" banner preset aggiornato. POST tombstone +
  //        reload per riallineare `config.value.preset_aggiornato` a false.
  //        La Idempotency-Key la mette l'interceptor di `core/api.js`. Toast/error gestito da useApiHandler.
  async function ignorePresetUpdate() {
    const result = await execute(
      () => apiIgnorePresetUpdate(codice),
    )
    if (result !== null) {
      await load()
    }
    return result
  }

  return {
    config,
    catalogo,
    savedSnapshot,
    dirty,
    loading,
    colonneNuove,
    presetAggiornato,
    load,
    ensureCatalogo,
    applyChange,
    save,
    reset,
    ignorePresetUpdate,
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
