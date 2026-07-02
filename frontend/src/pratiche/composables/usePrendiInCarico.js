// Scopo: azione "prendi in carico" della coda lavoro, condivisa fra le
// superfici che montano PraticheCodaLavoro (PraticheDashboard, PraticheHome).
// Estratto alla 2ª occorrenza (regola del 2): toast di successo, convenzione
// `result !== null` e ricarica della coda vivono in UN punto solo; il caller
// aggiunge il proprio refresh con `onSuccess` (es. la dashboard ricarica il
// percorso della pratica selezionata).
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { usePraticheStore } from '../stores/pratiche'

export function usePrendiInCarico(onSuccess = null) {
  const { t } = useI18n()
  const { execute } = useApiHandler()
  const store = usePraticheStore()

  // Scopo: prende in carico il flusso dell'item di coda e rinfresca la coda.
  async function prendiInCarico(item) {
    const result = await execute(
      () => store.prendiInCarico(item.flusso_id),
      { successMessage: t('pratiche.preso_in_carico') },
    )
    if (result !== null) {
      await store.loadCodaLavoro()
      if (onSuccess) await onSuccess(item)
    }
  }

  return { prendiInCarico }
}
