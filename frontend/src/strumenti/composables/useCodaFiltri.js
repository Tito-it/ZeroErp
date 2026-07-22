// Scopo: Filtri comuni dei tab code (Strumenti → Code di lavoro): ambito
//        miei/tutti (gate code_manage), stato dal vocabolario severity e
//        range date con data_da default 01/01 anno-1 (regola di progetto
//        «filtro data obbligatorio su liste»). Estratto alla 2ª copia
//        (regola del 2) da CodaLavoriTab/CodaStampaTab: stato filtri +
//        param-building in un punto solo; la toolbar gemella vive in
//        CodaFiltriToolbar.vue.
import { computed, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { toDateString } from '../../core/utils/date'

export function useCodaFiltri(statoMap) {
  const { t } = useI18n()
  const { isAllowed: canManage } = useActionPermission('code_manage')

  const filtri = reactive({
    ambito: 'miei',
    stato: null,
    // Floor temporale di default (come contratti/ordini: anno-1).
    dataDa: new Date(new Date().getFullYear() - 1, 0, 1),
    dataA: null,
  })

  const statoOptions = computed(() =>
    Object.keys(statoMap).map((k) => ({ value: k, label: k })),
  )
  const ambitoOptions = computed(() => [
    { value: 'miei', label: t('strumenti.code.ambito_miei') },
    { value: 'tutti', label: t('strumenti.code.ambito_tutti') },
  ])

  // Scopo: query param di lista dai filtri correnti + paging del BB.
  function buildParams(paging) {
    const params = {
      limit: paging.page_size,
      offset: (paging.page - 1) * paging.page_size,
    }
    if (filtri.ambito === 'tutti') params.ambito = 'tutti'
    if (filtri.stato) params.stato = filtri.stato
    if (filtri.dataDa) params.data_da = toDateString(filtri.dataDa)
    if (filtri.dataA) params.data_a = toDateString(filtri.dataA)
    return params
  }

  return { filtri, canManage, statoOptions, ambitoOptions, buildParams }
}
