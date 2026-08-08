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

import { ref } from 'vue'
import { useNotify } from './useNotify'

export function useApiHandler() {
  const loading = ref(false)
  const notify = useNotify()
  // Campi del form che il backend indica come da correggere (envelope: `fields`),
  // e come suggerisce di reagire (`ui_action`). Si azzerano a ogni chiamata: si
  // riferiscono all'ULTIMO errore, non alla storia del drawer.
  const campiErrati = ref([])
  const azioneUi = ref(null)

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
      if (!options.silent) {
        const message = extractErrorMessage(err) || options.errorMessage
        const isSystem = isSystemError(err)
        if (isSystem) {
          notify.systemError(message)
        } else {
          notify.error(message)
        }
      }
      return null
    } finally {
      loading.value = false
    }
  }

  return { execute, loading, campiErrati, azioneUi }
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
