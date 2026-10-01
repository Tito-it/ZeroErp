// Composable per dialog di conferma standard.
// Usa PrimeVue ConfirmDialog — richiede <ConfirmDialog /> in App.vue.
//
// Uso:
//   const { confirmSave, confirmDelete, confirmAction } = useConfirmAction()
//   confirmSave(onAcceptFn)
//   confirmSave(onAcceptFn, 'Le modifiche impattano tutti gli operatori.')
//   confirmDelete('Mario Rossi', onAcceptFn)
//   confirmAction({ header: t('...azione'), message: t('...'), onAccept })
//
// ⭐ IL CHROME STA IN UN PUNTO SOLO (`richiedi`, 2026-09-18): icone ←/✓,
//    classi, ESC. Le tre funzioni pubbliche aggiungono solo cio' che le
//    distingue — titolo, messaggio, coppia label/icona del bottone accept.
//    Un cambio di layout e' una riga qui (o in DIALOG_CHROME), non un giro
//    sui 66 chiamanti.
//
// ⛔ `header` E' OBBLIGATORIO, e si chiama `header` — come in AppDialog e in
//    PrimeVue. Fino al 2026-09-18 la chiave era `title`, e SETTE chiamanti
//    avevano scritto `header:`, ignorato in silenzio (JS non avvisa su una
//    chiave sconosciuta): il dialog usciva senza titolo, e un Dialog PrimeVue
//    senza titolo rende comunque la riga di testa — con l'unico figlio (la X)
//    a sinistra. Era la «X a sinistra» vista in-app. Uno dei sette l'aveva
//    persino scoperto e annotato sul sito invece di correggere la sorgente.
//    Presidio: scripts/check-dialog-chrome.mjs rifiuta ogni chiamata senza
//    `header` e ogni `title:`.
//    Il titolo e' IL NOME DELL'AZIONE che ha aperto la conferma: l'operatore
//    legge la stessa parola sul pulsante e sulla dialog.
//
// ⚠️ La X non si spegne da qui: `closable` non e' un'opzione di
//    `confirm.require` (PrimeVue 4 non la inoltra al Dialog). Sta sul tag
//    <ConfirmDialog> in App.vue, letta da DIALOG_CHROME. E li' sta anche ESC
//    (`pt.root`): il listener `document` di PrimeVue si spegne da qui
//    (`closeOnEscape: false`) perche' convive con quello del Drawer sotto, e
//    un ESC li chiudeva entrambi.

import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import { MANAGE_ICONS, STATUS_ICONS } from '../constants'

// Icone standard ConfirmDialog (PrimeVue accetta `acceptIcon` / `rejectIcon`
// nelle opzioni di `useConfirm.require`). Allineate al pattern FormFooter:
//   - reject (Annulla)         -> arrow-left (back-to-list)
//   - accept (Conferma)        -> check
//   - accept con danger=true   -> cestino + label "Elimina" (default coppia
//                                 destructive: label e icona devono sempre
//                                 stare insieme — "Elimina" senza cestino o
//                                 "Conferma" con cestino sono inconsistenze
//                                 visive). Caller possono sovrascrivere
//                                 passando acceptLabel/acceptIcon espliciti.
const STANDARD_ACCEPT_ICON = MANAGE_ICONS.CONFIRM
const STANDARD_REJECT_ICON = MANAGE_ICONS.BACK

export function useConfirmAction() {
  const confirm = useConfirm()
  const { t } = useI18n()

  // Scopo: l'unico punto che parla con `confirm.require`. Applica il chrome
  //        standard (icona di testa, classe e icona del reject, ESC) e lascia
  //        al chiamante solo header/message e la coppia label/icona/classe
  //        dell'accept.
  // ⚠️ `onReject` scatta su «Annulla» E sulla chiusura senza scelta (ESC:
  //    `onHide`), perche' per chi aspetta una risposta sono lo stesso «no».
  function richiedi({ header, message, acceptLabel, acceptIcon, acceptClass, onAccept, onReject }) {
    confirm.require({
      header,
      message,
      icon: STATUS_ICONS.ERRORE,
      // ⛔ Spento di proposito: ESC lo gestisce la radice della ConfirmDialog
      //    in App.vue (chiude SOLO la conferma). Questo e' il listener su
      //    `document`, che si chiuderebbe insieme al Drawer sotto.
      closeOnEscape: false,
      acceptClass,
      rejectClass: 'p-button-secondary',
      acceptLabel,
      rejectLabel: t('common.cancel'),
      acceptIcon,
      rejectIcon: STANDARD_REJECT_ICON,
      accept: onAccept,
      reject: onReject,
      onHide: onReject,
    })
  }

  /**
   * Mostra un dialog di conferma per eliminazione.
   *
   * @param {string} itemName - nome dell'elemento da eliminare (mostrato nel messaggio)
   * @param {Function} onAccept - callback eseguita alla conferma
   */
  function confirmDelete(itemName, onAccept) {
    richiedi({
      header: t('confirm.delete_title'),
      message: t('confirm.delete_message', { name: itemName }),
      // Coppia coerente: label "Elimina" + icona cestino (non "Conferma").
      acceptLabel: t('common.delete'),
      acceptIcon: MANAGE_ICONS.DELETE,
      acceptClass: 'p-button-danger',
      onAccept,
    })
  }

  /**
   * Mostra un dialog di conferma generico.
   *
   * Coppia label/icona del bottone accept:
   *   - default (non-danger): "Conferma" + check
   *   - danger=true: "Elimina" + cestino (coppia destructive coerente)
   * Il caller puo' sovrascrivere passando acceptLabel e/o acceptIcon
   * espliciti — restano vincolati a stare coerenti tra loro.
   *
   * @param {Object} options
   * @param {string} options.header - titolo del dialog: il nome dell'azione (OBBLIGATORIO)
   * @param {string} options.message - messaggio del dialog
   * @param {string} [options.acceptLabel] - etichetta pulsante conferma (override)
   * @param {string} [options.acceptIcon] - icona pulsante conferma (override)
   * @param {boolean} [options.danger] - true = pulsante rosso + default "Elimina" + cestino
   * @param {Function} options.onAccept - callback eseguita alla conferma
   * @param {Function} [options.onReject] - callback su «Annulla» o chiusura senza scelta
   */
  function confirmAction({ header, message, acceptLabel, acceptIcon, danger = false, onAccept, onReject }) {
    richiedi({
      header,
      message,
      acceptLabel: acceptLabel || (danger ? t('common.delete') : t('common.confirm')),
      acceptIcon: acceptIcon || (danger ? MANAGE_ICONS.DELETE : STANDARD_ACCEPT_ICON),
      acceptClass: danger ? 'p-button-danger' : '',
      onAccept,
      onReject,
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
    richiedi({
      header: t('confirm.save_title'),
      message: message || t('confirm.save_message'),
      acceptLabel: t('common.confirm'),
      acceptIcon: STANDARD_ACCEPT_ICON,
      acceptClass: '',
      onAccept,
    })
  }

  return { confirmSave, confirmDelete, confirmAction }
}
