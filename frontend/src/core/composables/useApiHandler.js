// Composable per chiamate API con gestione automatica errori e notifiche toast.
// Tutti i componenti di dominio devono usare questo invece di chiamare api.js direttamente.
//
// Uso:
//   const { execute, loading } = useApiHandler()
//   const data = await execute(() => api.get('/vendite/fatture/'), {
//     successMessage: t('notifications.save_success'),
//     errorMessage: t('notifications.generic_error')
//   })
//
// Campi in errore (dal 2026-08-08): il backend, quando lo sa, dice QUALI campi
// del form l'operatore deve correggere (envelope `error.fields`, api.md).
//
//   const { execute, campiErrati } = useApiHandler()
//   <InputText v-model="form.codice" :invalid="campiErrati.includes('codice')" />
//
// Prima esisteva solo il messaggio nel toast: l'operatore leggeva «campo
// obbligatorio» e doveva cercarselo. Il nome arriva dal service, quindi vale
// anche per le regole che il frontend non conosce.
// ⚠️ Si azzera a ogni `execute`: descrive l'ultimo errore, non la storia del
// drawer. Un campo resta rosso finche' non si riprova a salvare.
//
// ⭐ BERSAGLI (dal 2026-08-24): l'ALTRA META' della stessa idea. `campiErrati`
// dice quale campo correggere DENTRO la pagina dove l'operatore gia' si trova;
// i bersagli dicono a quale ALTRA cosa deve andare (envelope `error.targets`,
// forma `[{type, id}]`). E la differenza e' tutto il punto: il primo evidenzia
// un input, il secondo fa comparire un GESTO — «Apri la fattura 820».
//
// ⚠️ Il gesto NON va disegnato dal chiamante: lo compone questo composable e lo
// consegna al toast, cosi' che i 122 file che usano `execute` lo abbiano senza
// una riga di modifica. `bersagli` resta esposto per chi ha una superficie
// propria dove metterlo (il pannello degli esiti, l'icona di riga).
// Brief: docs/it/dev/work-in-progress/brief-db-bersaglio-errore.md §7-bis.

import { ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useNotify } from './useNotify'
import { estraiBersagli } from '../bersagli'
import { azioniDaBersagli } from '../bersaglioGesto'

// Codici che NON producono un toast, perche' a video c'e' gia' una schermata
// che dice la stessa cosa meglio: due messaggi identici, di cui uno rosso,
// fanno sembrare guasto quello che e' solo una scelta da fare.
//
// ⚠️ Sopprime il TOAST, non l'errore: `execute` ritorna `null` come sempre e
//    la chiamata resta fallita. Deve restare CORTISSIMA: un codice qui dentro
//    non si vede piu', e se la schermata che lo spiega cambia il rifiuto
//    diventa silenzioso. Presidiata da
//    `apps/core/tests/test_perimetro_emittente_copertura.py` (i codici devono
//    esistere a catalogo).
//
// ⚠️ `Set` e non un oggetto: `MAPPA[codice]` eredita dal prototipo, quindi un
//    codice chiamato `toString` risulterebbe «presente».
const CODICI_SENZA_TOAST = new Set([
  // Cancello di perimetro emittente (P-2b): `<ListaConfigurabile>` mostra gia'
  // il pannello «scegli un emittente» al posto della tabella.
  // ⭐ Si sopprime QUI e non evitando la chiamata nei caller perche' la config
  //    (che porta `richiede_scelta_emittente`) arriva DOPO che la fetch e'
  //    partita — si caricano in parallelo: evitarla del tutto vorrebbe dire
  //    far ASPETTARE ogni lista la config di un componente figlio.
  //    Dalla config in poi la lista si sospende da se'
  //    (`store.fetchSospesa`, in `useListaConfigurabilePage`), quindi qui
  //    passa la PRIMA chiamata e nessun'altra.
  'E_UI_LISTA_EMITTENTE_DA_SCEGLIERE',
])

export function useApiHandler() {
  const loading = ref(false)
  const notify = useNotify()
  // ⚠️ Si legge QUI, nel setup, e non dentro il `catch`: serve al degrado del
  // bersaglio (area BLOCCATA → nessun pulsante), e `useAuthStore()` fuori dal
  // setup dipenderebbe dalla pinia attiva globale.
  const auth = useAuthStore()
  // Campi del form che il backend indica come da correggere (envelope: `fields`),
  // e come suggerisce di reagire (`ui_action`). Si azzerano a ogni chiamata: si
  // riferiscono all'ULTIMO errore, non alla storia del drawer.
  const campiErrati = ref([])
  const azioneUi = ref(null)
  // Su QUALE cosa l'errore e' successo. Stesse regole di `campiErrati`: si
  // azzera a ogni chiamata, si popola anche in `silent`.
  const bersagli = ref([])

  /**
   * Esegue una chiamata API con gestione errori/toast automatica.
   *
   * @param {Function} apiFn - funzione che restituisce la Promise axios (es. () => api.get(...))
   * @param {Object} options
   * @param {string} [options.successMessage] - messaggio toast su successo (null = nessun toast)
   * @param {string} [options.errorMessage] - messaggio fallback se il backend non restituisce dettagli
   * @param {boolean} [options.silent] - true = nessun toast di errore (utile per polling)
   * @returns {*} data interna dall'envelope { data, meta } in caso di successo, null in caso di errore
   */
  async function execute(apiFn, options = {}) {
    loading.value = true
    campiErrati.value = []
    azioneUi.value = null
    bersagli.value = []
    try {
      const response = await apiFn()
      if (options.successMessage) {
        notify.success(options.successMessage)
      }
      // Unwrap dell'envelope standard backend { data: {...}, meta: {...} }.
      // Se apiFn ritorna gia' un payload unwrapped (es. action store),
      // preservalo invece di trattarlo come response Axios.
      const body = response && typeof response === 'object' && 'data' in response
        ? response.data
        : response
      return (body && typeof body === 'object' && 'data' in body) ? body.data : body
    } catch (err) {
      // Prima del toast: i campi da correggere e il suggerimento di reazione.
      // Si leggono anche in modalita' `silent` — il chiamante puo' voler
      // evidenziare senza far comparire un toast.
      campiErrati.value = estraiCampi(err)
      azioneUi.value = err.response?.data?.error?.ui_action ?? null
      bersagli.value = estraiBersagli(err.response?.data?.error)
      const codice = err.response?.data?.error?.code
      if (!options.silent && !CODICI_SENZA_TOAST.has(codice)) {
        const message = extractErrorMessage(err) || options.errorMessage
        const isSystem = isSystemError(err)
        // ⭐ Il gesto, quando c'e' qualcosa da raggiungere. `azioniDaBersagli`
        // scarta da se' i bersagli irraggiungibili (tipo senza destinazione,
        // area bloccata): un array vuoto = toast di prima, nessuna regressione.
        // ⚠️ Un toast CON azioni resta aperto finche' non lo si chiude: un
        // gesto che sparisce dopo cinque secondi non e' un gesto.
        const azioni = azioniDaBersagli(bersagli.value, auth)
        if (isSystem) {
          notify.systemError(message)
        } else if (azioni.length) {
          notify.errorConAzioni(message, azioni)
        } else {
          notify.error(message)
        }
      }
      return null
    } finally {
      loading.value = false
    }
  }

  return { execute, loading, campiErrati, azioneUi, bersagli }
}

// Estrae i nomi dei campi da correggere dall'envelope: { error: { fields: [...] } }.
// Il backend manda i NOMI e mai i valori (api.md §Envelope risposte).
function estraiCampi(err) {
  const campi = err.response?.data?.error?.fields
  return Array.isArray(campi) ? campi.filter(c => typeof c === 'string') : []
}

// Estrae il messaggio di errore dall'envelope backend { error: { code, message } }
function extractErrorMessage(err) {
  const data = err.response?.data
  if (!data) return null

  // Envelope standard: { error: { code, message } }
  if (data.error?.message) return data.error.message

  // Envelope semplificata: { error: "stringa" }
  if (typeof data.error === 'string') return data.error

  // DRF default: { detail: "..." }
  if (data.detail) return data.detail

  return null
}

// Errori di sistema: 500+, network error, timeout
function isSystemError(err) {
  if (!err.response) return true
  return err.response.status >= 500
}
