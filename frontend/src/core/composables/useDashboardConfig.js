// Scopo: Composable di stato per una dashboard configurabile (card KPI).
//        Gemello di `useListaConfig` per le liste. Gestisce:
//        - fetch della configurazione effettiva (cascata preset+permessi
//          risolta dalla fn DB);
//        - fetch dei contatori KPI in un solo giro (batch);
//        - mutazione locale della config con tracking dirty;
//        - save (PUT preferenza con Idempotency-Key) e reset (DELETE),
//          entrambi seguiti da reload.
//
// Differenza dalle liste: non esiste un endpoint "catalogo" separato.
// La fn DB arricchisce gia' ogni widget coi campi freschi del catalogo e
// include quelli non visibili (merge dei widget nuovi con visibile=false),
// quindi `config.widget` E' il pool selezionabile della modale — gia'
// depurato dai widget che l'utente non puo' vedere.
//
// Contatori: fetch separata e NON bloccante rispetto alla config. La
// griglia deve poter renderizzare le card (etichette, layout) anche se i
// numeri tardano o falliscono: un KPI degradato non deve lasciare la home
// bianca.

import { ref, computed } from 'vue'
import { useApiHandler } from './useApiHandler'
import {
  getDashboardConfig,
  getDashboardContatori,
  putDashboardPreferenza,
  deleteDashboardPreferenza,
  ignoreDashboardPresetUpdate as apiIgnorePresetUpdate,
} from '../api/ui-api'
import { chiaviScelte } from '../preferenzaPerChiave'

/**
 * Composable per una singola dashboard identificata da `codice`.
 *
 * @param {string} codice - codice stabile della dashboard (es. 'home')
 * @returns {{
 *   config, contatori, loaded, dirty, loading, widgetNuovi, presetAggiornato,
 *   widgetVisibili, dimensioneMax,
 *   load, loadContatori, applyChange, save, reset, ignorePresetUpdate,
 *   contatoreDi
 * }}
 */
export function useDashboardConfig(codice) {
  // Configurazione corrente (mutata localmente da applyChange).
  const config = ref(null)

  // Snapshot della config restituita dal server al load piu' recente.
  const savedSnapshot = ref(null)

  // Mappa {contatore_key: {valore, ok}} dall'endpoint batch.
  const contatori = ref({})

  // TRUE dopo il primo load andato a buon fine. Serve all'empty-state
  // "onesto": non dichiarare "nessun widget" prima di aver saputo davvero
  // che la fetch e' riuscita (stesso principio di DashEmptyState).
  const loaded = ref(false)

  // Flag locale "modifiche non salvate".
  const dirty = ref(false)

  const { execute, loading } = useApiHandler()

  // Scopo: Fetch della configurazione della dashboard. Reset di dirty +
  //        snapshot. Ritorna la config se ok, null se fallita (errore
  //        gia' notificato da useApiHandler).
  async function load() {
    const data = await execute(() => getDashboardConfig(codice))
    if (data) {
      config.value = _deepClone(data)
      savedSnapshot.value = _deepClone(data)
      dirty.value = false
      loaded.value = true
    }
    return data
  }

  // Scopo: Fetch batch dei contatori KPI. Volutamente separata da load():
  //        la griglia si disegna con la config, i numeri arrivano dopo.
  //        Un fallimento qui lascia le card senza numero, non senza card.
  async function loadContatori() {
    const data = await execute(() => getDashboardContatori(codice))
    if (data) {
      contatori.value = data.contatori || {}
    }
    return data
  }

  // Scopo: Carica config e contatori. I contatori partono solo dopo la
  //        config perche' il BE calcola le key dei widget visibili: senza
  //        una config risolta non ci sarebbe niente da contare.
  async function loadAll() {
    const data = await load()
    if (data) await loadContatori()
    return data
  }

  // Scopo: Applica una modifica locale alla config (selezione/ordine dei
  //        widget). Il chiamante passa una funzione che muta `next` in
  //        place; il composable garantisce immutabilita' del riferimento
  //        esterno e segna dirty=true.
  //        Esempio: applyChange(c => { c.widget = riordinati })
  function applyChange(mutator) {
    if (!config.value) return
    const next = _deepClone(config.value)
    mutator(next)
    config.value = next
    dirty.value = true
  }

  // Scopo: Salva la preferenza corrente e ricarica config + contatori
  //        (la selezione puo' essere cambiata, quindi anche le key da
  //        contare).
  //
  // Drift risk: la whitelist FE deve restare allineata a
  // DashboardPreferenzaService._PAYLOAD_KEYS / _WIDGET_KEYS. Se il BE
  // accetta nuove chiavi, aggiungerle anche qui; se ne rimuove, il PUT
  // le invierebbe e il PayloadValidator risponderebbe con
  // E_UI_PREFERENZA_VALIDAZIONE — errore parlante, nessun danno.
  async function save() {
    if (!config.value) return null
    // ⭐ Per chiave (2026-11-01, BB `preferenzaPerChiave`): solo le chiavi
    //    scelte — gia' della preferenza o toccate —, le altre restano «come lo
    //    standard». Nessuna chiave scelta = nessuna preferenza: DELETE.
    const payload = _extractWritablePayload(
      chiaviScelte(config.value, savedSnapshot.value, _PAYLOAD_ROOT_KEYS),
    )
    if (Object.keys(payload).length === 0) return reset()
    const result = await execute(
      () => putDashboardPreferenza(codice, payload),
    )
    if (result !== null) {
      await loadAll()
    }
    return result
  }

  // Scopo: Reset preferenza utente. Dopo DELETE ricarica: il BE applica
  //        la cascata standard (preset ruolo / emittente / sistema /
  //        catalogo grezzo).
  async function reset() {
    const result = await execute(() => deleteDashboardPreferenza(codice))
    if (result !== null) {
      await loadAll()
    }
    return result
  }

  // Scopo: "Ignora" banner preset aggiornato + reload per riallineare.
  async function ignorePresetUpdate() {
    const result = await execute(
      () => apiIgnorePresetUpdate(codice),
    )
    if (result !== null) {
      await load()
    }
    return result
  }

  // Scopo: Contatore di un widget. Ritorna null se il widget non ha una
  //        contatore_key (es. card di benvenuto) o se il valore non e'
  //        ancora arrivato; `{valore, ok}` altrimenti.
  function contatoreDi(widget) {
    const key = widget?.contatore_key
    if (!key) return null
    return contatori.value[key] ?? null
  }

  // Cap di card mostrabili, dal preset risolto. Fallback 8 allineato al
  // default DB (`ui.dashboard_preset.dimensione_max`).
  // Dichiarata PRIMA di widgetVisibili che la consuma: i computed sono
  // lazy e reggerebbero comunque, ma l'ordine corretto evita la classe
  // di TDZ silenziosa che morde con i watch immediate.
  const dimensioneMax = computed(() => config.value?.dimensione_max ?? 8)

  // Widget effettivamente da mostrare in griglia: solo i visibili,
  // ordinati, e tagliati a `dimensione_max`. Il taglio e' qui e non nel
  // template perche' e' una regola di configurazione, non di layout.
  const widgetVisibili = computed(() => {
    const tutti = config.value?.widget || []
    const visibili = tutti
      .filter(w => w.visibile)
      .slice()
      .sort((a, b) => (a.ordine ?? 0) - (b.ordine ?? 0))
    const max = dimensioneMax.value
    return max > 0 ? visibili.slice(0, max) : visibili
  })

  // Count dei widget nuovi apparsi in catalogo dopo l'ultimo salvataggio
  // dell'utente (badge UX "ci sono nuove card disponibili").
  const widgetNuovi = computed(() => config.value?.widget_nuovi ?? 0)

  // TRUE quando il pool stesso e' vuoto: nessun widget disponibile per il
  // profilo dell'utente (la fn DB li ha filtrati tutti per permessi).
  // Distinto da "nessuna card VISIBILE": in quel caso l'utente ne ha da
  // scegliere e va invitato a farlo, qui no — dirgli "usa l'ingranaggio"
  // sarebbe una bugia, perche' non troverebbe nulla da attivare.
  const poolVuoto = computed(() => (config.value?.widget || []).length === 0)

  // TRUE quando il preset di base e' cambiato dopo lo snapshot della
  // preferenza utente e il banner non e' stato dismissato. Calcolato
  // lato DB: passthrough. `?? false` = banner nascosto se il campo manca.
  const presetAggiornato = computed(
    () => config.value?.preset_aggiornato ?? false,
  )

  return {
    config,
    contatori,
    savedSnapshot,
    loaded,
    dirty,
    loading,
    widgetNuovi,
    presetAggiornato,
    widgetVisibili,
    dimensioneMax,
    poolVuoto,
    load,
    loadContatori,
    loadAll,
    applyChange,
    save,
    reset,
    ignorePresetUpdate,
    contatoreDi,
  }
}

// Scopo: Clona profondo via JSON. Sufficiente per la struttura della
//        config (no Date, no funzioni, no undefined).
function _deepClone(obj) {
  return JSON.parse(JSON.stringify(obj))
}

// Whitelist root del payload BE (allineata a DashboardPreferenzaService).
const _PAYLOAD_ROOT_KEYS = ['widget', 'dimensione_max']
const _WIDGET_KEYS = ['codice', 'ordine', 'visibile']

function _extractWritablePayload(config) {
  const out = {}
  for (const k of _PAYLOAD_ROOT_KEYS) {
    if (config[k] !== undefined) out[k] = config[k]
  }
  if (Array.isArray(out.widget)) {
    out.widget = out.widget.map(_extractWidget)
  }
  return out
}

function _extractWidget(w) {
  const out = {}
  for (const k of _WIDGET_KEYS) {
    if (w[k] !== undefined) out[k] = w[k]
  }
  return out
}
