// Scopo: Helper UI comuni dei tab code (Strumenti → Code di lavoro): opzioni
//        stato dal vocabolario severity, opzioni ambito miei/tutti (aperto a
//        tutti gli operatori — la lista è visibilità, `canManage` resta
//        esportato per il gate delle AZIONI nei tab).
//
//        Estratto alla 2ª copia (regola del 2) da CodaLavoriTab/CodaStampaTab;
//        la toolbar gemella vive in CodaFiltriToolbar.vue. Con la conversione
//        a <ListaConfigurabile> (7° lotto, 2026-08-03) lo STATO dei filtri e
//        dell'ordinamento è migrato negli store Pinia
//        (stores/codeJobs.js, interfaccia useSearchTable-compatibile): qui
//        restano solo le opzioni e il permesso, che sono UI pura.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useActionPermission } from '../../core/composables/useActionPermission'

// Azione di processo che governa le code. ⚠️ FONTE UNICA lato FE: la usano il
// gate delle azioni di questi tab e `useCodaArchiviazione`, e un codename
// scritto in due posti e' un cancello che smette di essere lo stesso al primo
// rename — in silenzio, perche' un permesso che non esiste risponde `false` e
// l'azione sparisce senza errore.
export const AZIONE_CODE_MANAGE = 'code_manage'

export function useCodaFiltri(statoMap) {
  const { t } = useI18n()
  const { isAllowed: canManage } = useActionPermission(AZIONE_CODE_MANAGE)

  const statoOptions = computed(() =>
    Object.keys(statoMap).map((k) => ({ value: k, label: k })),
  )
  const ambitoOptions = computed(() => [
    { value: 'miei', label: t('strumenti.code.ambito_miei') },
    { value: 'tutti', label: t('strumenti.code.ambito_tutti') },
  ])

  return { canManage, statoOptions, ambitoOptions }
}
