<script setup>
// Scopo: DataTable paginata preventivi vendita con search, filtri stato/data, empty state.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreventiviStore } from '../stores/preventivi'
import { useSearchTable } from '../../../core/composables/useSearchTable'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { statoPreventiveSeverity } from '../../../core/utils/severity'
import { displayDate, toDateString } from '../../../core/utils/date'
import { formatCurrency } from '../../../core/utils/format'
import { DATE_FORMAT, TAB_ENTITIES } from '../../../core/constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import NewButton from '../../../core/components/NewButton.vue'
import SearchHint from '../../../core/components/SearchHint.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import ReloadButton from '../../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = usePreventiviStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'data',
  defaultSortOrder: 'desc'
})

// --- Filtri ---
const statoFilter = ref(null)
const dataDaFilter = ref(store.filters.data_da ? new Date(store.filters.data_da + 'T00:00:00') : null)
const dataAlFilter = ref(null)

function onStatoChange() {
  store.filters.stato = statoFilter.value
  applyFilters()
}

function onDataDaChange() {
  store.filters.data_da = dataDaFilter.value ? toDateString(dataDaFilter.value) : null
  applyFilters()
}

function onDataAlChange() {
  store.filters.data_a = dataAlFilter.value ? toDateString(dataAlFilter.value) : null
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, TAB_ENTITIES.PREVENTIVO)

// Lista preventivi: ha filtro data_da con default anno-1 (frontend-standards
// "Filtro data standard"), quindi auto-load al mount. Lo store guard
// hasFilters considera data_da come filtro attivo: non rischiamo di tirar
// giu' "tutti i preventivi senza limiti" perche' il default e' di per se'
// un filtro temporale.
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('preventivi.search_placeholder')" style="width: 260px;" />
        <LookupSelect v-model="statoFilter" rel="config.stati_doc_preventivi" value-field="codice_interno"
          :placeholder="t('preventivi.filtro_stato')" show-clear @change="onStatoChange" style="width: 160px;" />
        <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
          :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
          @date-select="onDataDaChange" @clear-click="onDataDaChange" />
        <DatePicker v-model="dataAlFilter" :placeholder="t('common.data_a')"
          :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
          @date-select="onDataAlChange" @clear-click="onDataAlChange" />
      </div>
      <div class="app-page-actions">
        <ReadonlyBadge />
        <ReloadButton @click="reload" />
        <NewButton :tooltip="t('preventivi.nuovo_preventivo')" @click="emit('new')" />
      </div>
    </div>

    <SearchHint v-if="!store.hasSearched && !store.loading" />

    <DataTable
      v-show="store.hasSearched || store.loading"
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy removable-sort striped-rows scrollable scrollHeight="flex"
      class="app-datatable"
      @page="onPage" @sort="onSort" @row-click="onRowClick"
      selection-mode="single" data-key="id"
    >
      <Column field="numero" :header="t('preventivi.col_numero')" sortable style="width: 130px;" />
      <Column field="rev" :header="t('preventivi.col_rev')" style="width: 60px;" />
      <Column field="data" :header="t('preventivi.col_data')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data) }}</template>
      </Column>
      <Column field="cliente_denominazione" :header="t('preventivi.col_cliente')" sortable style="min-width: 200px;" />
      <Column field="utility_descrizione" :header="t('preventivi.col_utility')" sortable style="min-width: 140px;" />
      <Column field="stato_descrizione" :header="t('preventivi.col_stato')" sortable style="width: 130px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoPreventiveSeverity(data.stato_codice_interno)" />
        </template>
      </Column>
      <Column field="totale_documento" :header="t('preventivi.col_totale')" style="width: 130px;">
        <template #body="{ data }">{{ formatCurrency(data.totale_documento) }}</template>
      </Column>
      <Column field="validita_al" :header="t('preventivi.col_validita')" style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.validita_al) }}</template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
