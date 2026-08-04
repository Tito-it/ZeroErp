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

export function useCodaFiltri(statoMap) {
  const { t } = useI18n()
  const { isAllowed: canManage } = useActionPermission('code_manage')

  const statoOptions = computed(() =>
    Object.keys(statoMap).map((k) => ({ value: k, label: k })),
  )
  const ambitoOptions = computed(() => [
    { value: 'miei', label: t('strumenti.code.ambito_miei') },
    { value: 'tutti', label: t('strumenti.code.ambito_tutti') },
  ])

  return { canManage, statoOptions, ambitoOptions }
}
