// Composable per dialog di conferma standard.
// Usa PrimeVue ConfirmDialog — richiede <ConfirmDialog /> in App.vue.
//
// Uso:
//   const { confirmSave, confirmDelete, confirmAction } = useConfirmAction()
//   confirmSave(onAcceptFn)
//   confirmSave(onAcceptFn, 'Le modifiche impattano tutti gli operatori.')
//   confirmDelete('Mario Rossi', onAcceptFn)

import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import { MANAGE_ICONS } from '../constants'

// Icone standard ConfirmDialog (PrimeVue accetta `acceptIcon` / `rejectIcon`
// nelle opzioni di `useConfirm.require`). Allineate al pattern FormFooter:
//   - reject (Annulla)  -> arrow-left (back-to-list)
//   - accept (Conferma) -> check
//   - accept su delete  -> trash (override sotto)
// Conseguenza: tutti i dialog di conferma globali ereditano automaticamente
// le icone standard senza modificare i call site (es. preventivi onCambiaStato
// con action key='rifiuta', cancellazioni varie, ecc.).
const STANDARD_ACCEPT_ICON = MANAGE_ICONS.CONFIRM
const STANDARD_REJECT_ICON = MANAGE_ICONS.BACK

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
      rejectClass: 'p-button-secondary',
      acceptLabel: t('common.confirm'),
      rejectLabel: t('common.cancel'),
      acceptIcon: MANAGE_ICONS.DELETE,
      rejectIcon: STANDARD_REJECT_ICON,
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
      rejectClass: 'p-button-secondary',
      acceptLabel: acceptLabel || t('common.confirm'),
      rejectLabel: t('common.cancel'),
      acceptIcon: STANDARD_ACCEPT_ICON,
      rejectIcon: STANDARD_REJECT_ICON,
      accept: onAccept
    })
  }

  /**
   * Mostra un dialog di conferma salvataggio.
   * Messaggio standard, sovrascrivibile con parametro opzionale.
   *
   * @param {Function} onAccept - callback eseguita alla conferma
   * @param {string} [message] - messaggio personalizzato (default: confirm.save_message)
   */
  function confirmSave(onAccept, message) {
    confirm.require({
      header: t('confirm.save_title'),
      message: message || t('confirm.save_message'),
      icon: 'pi pi-exclamation-triangle',
      rejectClass: 'p-button-secondary',
      acceptLabel: t('common.confirm'),
      rejectLabel: t('common.cancel'),
      acceptIcon: STANDARD_ACCEPT_ICON,
      rejectIcon: STANDARD_REJECT_ICON,
      accept: onAccept
    })
  }

  return { confirmSave, confirmDelete, confirmAction }
}
