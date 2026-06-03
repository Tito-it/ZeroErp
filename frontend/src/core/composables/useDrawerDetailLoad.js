// Composable: carica il dettaglio di un'entità in un drawer in modo robusto.
//
// Se la fetch del dettaglio fallisce — tipicamente HTTP 404: record
// inesistente, cancellato, oppure FUORI dallo scope emittente dell'operatore
// con la RLS attiva (vedi analisi-attivazione-rls-operatori) — invece di
// lasciare il drawer aperto vuoto/rotto, mostra un toast e CHIUDE il drawer.
//
// Restituisce i dati su successo, `null` su fallimento (il drawer è già stato
// chiuso → il caller deve saltare populate/apply).
//
// Uso:
//   const onClose = useDrawerClose(emit, 'cancelled')
//   const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
//   ...
//   const d = await loadDetailOrClose(() => store.fetchDetail(id))
//   if (d == null) return          // fallita → drawer già chiuso
//   detail.value = d
//   populateFromDetail(d)
import { useI18n } from 'vue-i18n'

import { useNotify } from './useNotify'

// Scopo: factory che lega la gestione "dettaglio non accessibile" alla
//        chiusura del drawer corrente.
// @param {() => void} onClose - handler di chiusura (es. useDrawerClose(emit)).
export function useDrawerDetailLoad(onClose) {
  const notify = useNotify()
  const { t } = useI18n()

  // Scopo: esegue `fetchFn`; su errore avvisa e chiude, ritornando null.
  // @param {() => Promise<any>} fetchFn - la fetch del dettaglio.
  // @param {object} [opts]
  // @param {string} [opts.message] - messaggio toast (default i18n).
  async function loadDetailOrClose(fetchFn, { message } = {}) {
    try {
      return await fetchFn()
    } catch {
      notify.warn(message || t('notifications.detail_non_accessibile'))
      if (typeof onClose === 'function') onClose()
      return null
    }
  }

  return { loadDetailOrClose }
}
