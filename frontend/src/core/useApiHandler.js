// Composable per chiamate API con gestione automatica errori e notifiche toast.
// Tutti i componenti di dominio devono usare questo invece di chiamare api.js direttamente.
//
// Uso:
//   const { execute, loading } = useApiHandler()
//   const data = await execute(() => api.get('/vendite/fatture/'), {
//     successMessage: t('notifications.save_success'),
//     errorMessage: t('notifications.generic_error')
//   })

import { ref } from 'vue'
import { useNotify } from './useNotify'

export function useApiHandler() {
  const loading = ref(false)
  const notify = useNotify()

  /**
   * Esegue una chiamata API con gestione errori/toast automatica.
   *
   * @param {Function} apiFn - funzione che restituisce la Promise axios (es. () => api.get(...))
   * @param {Object} options
   * @param {string} [options.successMessage] - messaggio toast su successo (null = nessun toast)
   * @param {string} [options.errorMessage] - messaggio fallback se il backend non restituisce dettagli
   * @param {boolean} [options.silent] - true = nessun toast di errore (utile per polling)
   * @returns {*} response.data in caso di successo, null in caso di errore
   */
  async function execute(apiFn, options = {}) {
    loading.value = true
    try {
      const response = await apiFn()
      if (options.successMessage) {
        notify.success(options.successMessage)
      }
      return response.data
    } catch (err) {
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

  return { execute, loading }
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
