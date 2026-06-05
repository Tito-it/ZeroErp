// Scopo: orchestrazione save + richiedi-approvazione con gate L2 (B12
//        2026-06-05, regola del 2). I pezzi atomici (classifyL2Error,
//        L2ErrorBanner, useLimitiPricing/L2_ERROR_CODES) erano già condivisi in
//        vendite/_shared/pricing/, ma l'ORCHESTRAZIONE era copia-incollata 3
//        volte (PreventiviRigaForm, ContrattoRigheDrawer, OffertaEccezioniDrawer):
//        reset banner → loading → persist(buildPayload()) → success+sideEffects
//        → catch classify (banner L2 vs toast) → finally; + retry con
//        `richiesta_approvazione=true` (toast, niente classify).
//
// Solo la macchina classify/retry/reset è condivisa. I side-effect di successo
// divergono (emit('saved') vs loadPreview+emit+close vs reload+close) → iniettati
// via `onSuccess(result)`. `l2Error` e `loading` sono ref del chiamante (l2Error
// è legato al template L2ErrorBanner + eventuale watch di reset su cambio campo).
//
// Parametri:
//   persist(payload)            → Promise (store action già-unwrappata)
//   buildPayload(extras = {})   → payload; in retry riceve { richiesta_approvazione: true }
//   onSuccess(result)           → side-effect di dominio (opzionale, può essere async)
//   messages { success, approvalRequested, error }
//     - success: FUNZIONE () => string (il messaggio dipende da create/edit)
//     - approvalRequested, error: string
//   l2Error                     ref del chiamante (banner)
//   loading                     ref del chiamante (disabilita form/bottoni)
//   l2ErrorCodes                Set/array codici L2 (da useLimitiPricing)
//
// Ritorna: { save, richiediApprovazione }

import { useNotify } from '../../../core/composables/useNotify'
import { extractApiError } from '../../../core/utils/apiError'
import { classifyL2Error } from './classifyL2Error'

export function useL2SaveFlow({
  persist,
  buildPayload,
  onSuccess,
  messages,
  l2Error,
  loading,
  l2ErrorCodes,
}) {
  const notify = useNotify()

  // `messages.success` può essere una funzione (messaggio dinamico create/edit)
  // o una stringa: risolviamo tollerante per non sorprendere chi ha un messaggio
  // statico (gli altri messaggi sono stringhe).
  const resolveSuccess = () =>
    typeof messages.success === 'function' ? messages.success() : messages.success

  async function save() {
    l2Error.value = null
    loading.value = true
    try {
      const result = await persist(buildPayload())
      notify.success(resolveSuccess())
      await onSuccess?.(result)
    } catch (err) {
      // Banner inline su violazione L2 (BB condiviso); altrimenti toast standard.
      const l2 = classifyL2Error(err, { fallbackMessage: messages.error, l2ErrorCodes })
      if (l2) l2Error.value = l2
      else notify.error(extractApiError(err, messages.error))
    } finally {
      loading.value = false
    }
  }

  async function richiediApprovazione() {
    l2Error.value = null
    loading.value = true
    try {
      const result = await persist(buildPayload({ richiesta_approvazione: true }))
      notify.success(messages.approvalRequested)
      await onSuccess?.(result)
    } catch (err) {
      notify.error(extractApiError(err, messages.error))
    } finally {
      loading.value = false
    }
  }

  return { save, richiediApprovazione }
}
