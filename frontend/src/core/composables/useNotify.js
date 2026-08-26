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

  // ⛔ ESISTEVA GIÀ CHI LA CHIAMAVA, e non c'era (2026-08-26). Quattro punti
  // facevano `notify.info(...)` — due nel cockpit di competenza («il giro era
  // già in corso», «l'ha fatturato un altro giro») e due nella numerazione su
  // selezione — e tutti e quattro sollevavano `notify.info is not a function`
  // invece di mostrare il messaggio. Nessun test la copriva, e un toast che non
  // compare non si distingue da un toast che non è stato chiesto.
  // ⚠️ Un informativo NON è un avviso: dice che una cosa è successa, non che
  // c'è qualcosa da guardare. Riusare `warn` avrebbe colorato di giallo
  // messaggi tranquilli, insegnando a ignorare il giallo.
  function info(message) {
    toast.add({
      severity: 'info',
      summary: message || t('notifications.generic_info'),
      life: TOAST_DURATION.INFO
    })
  }

  function warn(message) {
    toast.add({
      severity: 'warn',
      summary: message || t('notifications.generic_warn'),
      life: TOAST_DURATION.WARN
    })
  }

  function error(message) {
    toast.add({
      severity: 'error',
      summary: message || t('notifications.generic_error'),
      life: TOAST_DURATION.ERROR
    })
  }

  // ⭐ L'ERRORE CHE PORTA UN GESTO (2026-08-24). Quando il backend dice su
  // QUALE cosa l'errore e' successo (envelope `error.targets`), il toast non
  // porta piu' solo la frase: porta anche il modo di arrivarci — «Apri la
  // fattura 820». All'operatore non serve il NOME del record, gli serve
  // ARRIVARCI: un identificativo dentro una frase resta una cosa da ricopiare a
  // mano in un campo di ricerca.
  //
  // ⛔ PERSISTENTE, e non e' un dettaglio: un gesto che sparisce dopo cinque
  // secondi non e' un gesto. `life: 0` = chiusura manuale, come `systemError`.
  //
  // ⚠️ Le azioni le compone `useApiHandler`, non il chiamante: il gesto deve
  // arrivare ai 122 file che usano `execute` senza che nessuno lo scriva.
  // ⚠️ `group` dedicato: la resa con i pulsanti sta nel `<Toast group="azioni">`
  // di `App.vue`, e il toast normale resta esattamente com'era.
  function errorConAzioni(message, azioni) {
    if (!azioni?.length) {
      error(message)
      return
    }
    toast.add({
      severity: 'error',
      summary: message || t('notifications.generic_error'),
      group: 'azioni',
      life: TOAST_DURATION.AZIONI,
      // Il payload che il template del gruppo rende come pulsanti.
      azioni
    })
  }

  function systemError(message) {
    toast.add({
      severity: 'error',
      summary: message || t('notifications.generic_error'),
      life: TOAST_DURATION.SYSTEM_ERROR
    })
  }

  return { success, info, warn, error, errorConAzioni, systemError }
}
