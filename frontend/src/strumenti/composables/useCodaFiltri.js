// Scopo: Filtri comuni dei tab code (Strumenti → Code di lavoro): ambito
//        miei/tutti (aperto a tutti gli operatori — la lista è visibilità,
//        `canManage` resta esportato per il gate delle AZIONI nei tab),
//        stato dal vocabolario severity e
//        range date con data_da default 01/01 anno-1 (regola di progetto
//        «filtro data obbligatorio su liste»). Estratto alla 2ª copia
//        (regola del 2) da CodaLavoriTab/CodaStampaTab: stato filtri +
//        param-building in un punto solo; la toolbar gemella vive in
//        CodaFiltriToolbar.vue.
import { computed, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { toDateString } from '../../core/utils/date'

// Opzioni per-tab (2026-07-23, richiesta Tid):
//  - `statoDefault`: stato preselezionato all'apertura (lavori → 'IN_CORSO':
//    il tab risponde prima di tutto a «cosa sta girando ora»; azzerabile con
//    lo show-clear del Select per le consultazioni storiche);
//  - `sortDefault`: { field, order } iniziale (order: -1 = DESC, convenzione
//    PrimeVue). Le colonne ordinabili differiscono per coda: la whitelist
//    autorevole vive nel BE, qui solo lo stato UI.
// L'ambito «Solo i miei / Tutti» è PER-OPERATORE su ENTRAMBE le code
// (2026-07-23, decisione Tid): «miei» = lanciati da me, «tutti» = di tutti
// gli operatori. Stessa parola, stesso comportamento — una semantica diversa
// per coda (la stampa filtrava per emittente) si leggeva come filtro rotto.
export function useCodaFiltri(
  statoMap,
  { statoDefault = null, sortDefault = null } = {},
) {
  const { t } = useI18n()
  const { isAllowed: canManage } = useActionPermission('code_manage')

  const filtri = reactive({
    ambito: 'miei',
    stato: statoDefault,
    // Floor temporale di default (come contratti/ordini: anno-1).
    dataDa: new Date(new Date().getFullYear() - 1, 0, 1),
    dataA: null,
  })

  // Ordinamento lazy della DataTable (server-side): campo + direzione.
  const ordinamento = reactive({
    field: sortDefault?.field ?? null,
    order: sortDefault?.order ?? -1,
  })

  // Scopo: applica l'evento @sort della DataTable allo stato ordinamento.
  function applySortEvent(event) {
    ordinamento.field = event.sortField
    ordinamento.order = event.sortOrder
  }

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
    if (ordinamento.field) {
      params.sort_by = ordinamento.field
      params.sort_dir = ordinamento.order === 1 ? 'ASC' : 'DESC'
    }
    return params
  }

  return {
    filtri, ordinamento, applySortEvent,
    canManage, statoOptions, ambitoOptions, buildParams,
  }
}
