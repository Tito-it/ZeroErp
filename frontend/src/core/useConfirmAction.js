// Composable per dialog di conferma azioni distruttive.
// Usa PrimeVue ConfirmDialog — richiede <ConfirmDialog /> in App.vue.
//
// Uso:
//   const { confirmDelete } = useConfirmAction()
//   confirmDelete('Mario Rossi', async () => {
//     await execute(() => api.delete(`/anagrafiche/soggetti/${id}/`))
//   })

import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'

export function useConfirmAction() {
  const confirm = useConfirm()
  const { t } = useI18n()

  /**
   * Mostra un dialog di conferma per eliminazione.
   *
   * @param {string} itemName - nome dell'elemento da eliminare (mostrato nel messaggio)
   * @param {Function} onAccept - callback eseguita alla conferma
   */
  function confirmDelete(itemName, onAccept) {
    confirm.require({
      header: t('confirm.delete_title'),
      message: t('confirm.delete_message', { name: itemName }),
      icon: 'pi pi-exclamation-triangle',
      acceptClass: 'p-button-danger',
      acceptLabel: t('common.confirm'),
      rejectLabel: t('common.cancel'),
      accept: onAccept
    })
  }

  /**
   * Mostra un dialog di conferma generico.
   *
   * @param {Object} options
   * @param {string} options.title - titolo del dialog
   * @param {string} options.message - messaggio del dialog
   * @param {string} [options.acceptLabel] - etichetta pulsante conferma
   * @param {boolean} [options.danger] - true = pulsante conferma rosso
   * @param {Function} options.onAccept - callback eseguita alla conferma
   */
  function confirmAction({ title, message, acceptLabel, danger = false, onAccept }) {
    confirm.require({
      header: title,
      message: message,
      icon: 'pi pi-exclamation-triangle',
      acceptClass: danger ? 'p-button-danger' : '',
      acceptLabel: acceptLabel || t('common.confirm'),
      rejectLabel: t('common.cancel'),
      accept: onAccept
    })
  }

  return { confirmDelete, confirmAction }
}
