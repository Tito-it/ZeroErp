<script setup>
// Scopo: Lista resi di vendita configurabile. Nasce direttamente
// <ListaConfigurabile codice="vendite.resi"> (seed DB id 9): ritiro dinamico
// colonne + personalizzazione. Scaffolding centralizzato in
// useListaConfigurabilePage; qui restano filtri custom e slot. Righe dalla
// vista canonica `vw_resi_lista` (destinatario, ba_codice, id fiscale, DDT di
// origine, emittente). Clone ridotto di DdtSearchTable (brief §11): NIENTE
// azione "Nuovo" (il reso nasce SOLO dal pannello nel drawer DDT) e niente
// export (endpoint BE rimandato) — le due azioni standard sono filtrate via.
import { onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import ListaConfigurabile from '../../../core/components/ListaConfigurabile.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { DATE_FORMAT, TAB_ENTITIES } from '../../../core/constants'
import { statoResoSeverity } from '../../../core/utils/severity'
import { useResiStore } from '../stores/resi'

const emit = defineEmits(['row-click'])
const { t } = useI18n()
const store = useResiStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// Niente "Nuovo" (il reso nasce dal DDT consegnato) ne' export (endpoint BE
// rimandato): si filtrano le due azioni standard dello scaffolding.
const resiPageActions = computed(
  () => pageActions.value.filter(a => a.key !== 'new' && a.key !== 'export'),
)

// --- Filtri custom (toolbar caller) — binding store via BB ---
const { bindSelect, bindDate } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_codice_interno')
const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da')
const { value: dataAlFilter, onChange: onDataAlChange } = bindDate('data_a')

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

useTabFreshness(store, TAB_ENTITIES.RESO)

// Lista con filtro data_da default anno-1: auto-load al mount (lo store guard
// hasFilters considera data_da come filtro attivo).
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- Toolbar UNICA esterna (pattern lista standard). -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="searchText" :placeholder="t('vendite.resi.search_placeholder')" style="width: 260px;" />
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_reso"
            value-field="codice_interno"
            :placeholder="t('vendite.resi.filtro_stato')"
            show-clear
            :filter="false"
            style="width: 160px;"
            @change="onStatoChange"
          />
          <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
            :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
            @date-select="onDataDaChange" @clear-click="onDataDaChange" />
          <DatePicker v-model="dataAlFilter" :placeholder="t('common.data_a')"
            :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
            @date-select="onDataAlChange" @clear-click="onDataAlChange" />
        </div>
        <PageActionsBar :actions="resiPageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <ListaConfigurabile
        ref="listaRef"
        codice="vendite.resi"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        @page="onPage"
        @sort="onSort"
        @row-click="onRowClick"
        @config-loaded="onConfigLoaded"
      >
        <!-- Numero: NULL in DRAFT (assegnato solo a CONFERMATO) → mostra "—". -->
        <template #cell-numero="{ data }">
          {{ data.numero || '—' }}
        </template>

        <!-- Stato: Tag severity data-driven (statoResoSeverity). -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoResoSeverity(data.stato_codice_interno)" />
        </template>
      </ListaConfigurabile>
    </template>
  </div>
</template>
