import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { TOAST_DURATION } from '../constants'

export function useNotify() {
  const toast = useToast()
  const { t } = useI18n()

  function success(message) {
    toast.add({
      severity: 'success',
      summary: message || t('notifications.save_success'),
      life: TOAST_DURATION.SUCCESS
    })
  }

  function error(message) {
    toast.add({
      severity: 'error',
      summary: message || t('notifications.generic_error'),
      life: TOAST_DURATION.ERROR
    })
  }

  function systemError(message) {
    toast.add({
      severity: 'error',
      summary: message || t('notifications.generic_error'),
      life: TOAST_DURATION.SYSTEM_ERROR
    })
  }

  return { success, error, systemError }
}
