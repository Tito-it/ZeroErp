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

  // ⭐ LA FORMA COMUNE DEI TRE TOAST D'ERRORE, in un posto solo (2026-09-09).
  // I tre — normale, di sistema, col gesto — condividono severita', ripiego del
  // messaggio e il `detail` che porta la SOLUZIONE; divergono solo per `life` e
  // per cio' che il gruppo dedicato si porta dietro.
  // ⛔ Prima erano tre copie di due righe, e la terza l'ha aggiunta il campo
  //    `soluzione`: e' il momento in cui una ripetizione smette di essere
  //    tollerabile — al quarto campo sarebbero tre punti da ricordarsi.
  //
  // ⚠️ La soluzione va nel `detail` di PrimeVue e non concatenata al `summary`:
  //    sono DUE frasi con due ruoli — cosa e' successo, e cosa fare — e il tema
  //    le rende una sotto l'altra con pesi diversi. Unirle produrrebbe un
  //    periodo unico in cui l'istruzione si perde dentro la diagnosi.
  // ⚠️ `undefined` e non stringa vuota: una chiave presente e vuota farebbe
  //    disegnare al tema una seconda riga che non contiene niente.
  function _toastErrore(message, soluzione, extra) {
    toast.add({
      severity: 'error',
      summary: message || t('notifications.generic_error'),
      detail: soluzione || undefined,
      ...extra
    })
  }

  // ⭐ L'ERRORE CHE DICE ANCHE COSA FARE (2026-09-09). Il secondo argomento e'
  // la `soluzione` che il team DB scrive a catalogo per il codice sollevato:
  // viaggia dal database (canale HINT dell'eccezione) fino a `error.hint`
  // nell'envelope, ed e' l'UNICA frase che dice all'operatore cosa fare adesso.
  // Fino a quel giorno il database la scriveva, il backend la trasportava con
  // cinque punti di traduzione allineati, e lo schermo la buttava.
  //
  // ⚠️ La durata cambia col TESTO, non con la gravita': con la soluzione c'e' il
  //    doppio da leggere (`ERROR_CON_SOLUZIONE`).
  function error(message, soluzione) {
    _toastErrore(message, soluzione, {
      life: soluzione ? TOAST_DURATION.ERROR_CON_SOLUZIONE : TOAST_DURATION.ERROR
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
  // ⚠️ La `soluzione` arriva anche qui, e l'ordine a video e' quello del
  // ragionamento: cosa e' successo → cosa fare → il pulsante che lo fa. Il
  // template del gruppo (`App.vue`) la rende fra il testo e i pulsanti.
  function errorConAzioni(message, azioni, soluzione) {
    if (!azioni?.length) {
      error(message, soluzione)
      return
    }
    _toastErrore(message, soluzione, {
      group: 'azioni',
      life: TOAST_DURATION.AZIONI,
      // Il payload che il template del gruppo rende come pulsanti.
      azioni
    })
  }

  // ⚠️ Anche il toast di sistema porta la soluzione quando c'e', ed e' meno
  // raro di quanto sembri: `_apply_policy` la toglie sui TRE codici tecnici
  // (`E_DATABASE`, `E_PIPELINE`, `E_GENERICO`) ma la lascia sui codici di
  // classe `TECNICO` registrati a catalogo — dove la frase e' proprio quella
  // che serve a chi legge un 500 («segnalare al supporto citando il
  // request_id»).
  // ⛔ Qui la durata non cambia: e' gia' persistente (`life: 0`).
  function systemError(message, soluzione) {
    _toastErrore(message, soluzione, { life: TOAST_DURATION.SYSTEM_ERROR })
  }

  return { success, info, warn, error, errorConAzioni, systemError }
}
