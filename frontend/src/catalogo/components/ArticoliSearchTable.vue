<script setup>
// Scopo: DataTable paginata articoli con search, filtri e ordinamento.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticoliStore } from '../stores/articoli'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { displayDate } from '../../core/utils/date'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { DATE_FORMAT } from '../../core/constants'
import { toDateString } from '../../core/utils/date'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useArticoliStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'descrizione'
})

const attivoFilter = ref(true)
const compositoFilter = ref(null)
const utilityFilter = ref(null)
const tipologiaFilter = ref(null)
const gruppoFilter = ref(null)
const dataDaFilter = ref(store.filters.data_da ? new Date(store.filters.data_da + 'T00:00:00') : null)
const dataAFilter = ref(null)

const boolOptions = [
  { value: null, label: t('common.all') },
  { value: true, label: t('common.yes') },
  { value: false, label: t('common.no') }
]

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}
function onCompositoChange() {
  store.filters.is_composito = compositoFilter.value
  applyFilters()
}
function onUtilityChange() {
  store.filters.voce_utility = utilityFilter.value
  applyFilters()
}
function onTipologiaChange() {
  store.filters.tipo_voce_id = tipologiaFilter.value
  applyFilters()
}
function onGruppoChange() {
  store.filters.gruppo_voce_id = gruppoFilter.value
  applyFilters()
}
function onDataDaChange() {
  store.filters.data_da = dataDaFilter.value ? toDateString(dataDaFilter.value) : null
  applyFilters()
}
function onDataAChange() {
  store.filters.data_a = dataAFilter.value ? toDateString(dataAFilter.value) : null
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, 'articolo')
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('catalogo.search_placeholder')" />
        <Select v-model="attivoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" style="width: 120px;" />
        <Select v-model="compositoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_composito')" show-clear @change="onCompositoChange" style="width: 140px;" />
        <Select v-model="utilityFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_utility')" show-clear @change="onUtilityChange" style="width: 120px;" />
        <LookupSelect v-model="tipologiaFilter" rel="vendite.articoli_tipologie"
          :placeholder="t('catalogo.filtro_tipologia')" show-clear @change="onTipologiaChange" style="width: 150px;" />
        <LookupSelect v-model="gruppoFilter" rel="vendite.articoli_gruppi"
          :placeholder="t('catalogo.filtro_gruppo')" show-clear @change="onGruppoChange" style="width: 150px;" />
        <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')" :dateFormat="DATE_FORMAT"
          showIcon showButtonBar style="width: 150px;" @date-select="onDataDaChange" @clear-click="onDataDaChange" />
        <DatePicker v-model="dataAFilter" :placeholder="t('common.data_a')" :dateFormat="DATE_FORMAT"
          showIcon showButtonBar style="width: 150px;" @date-select="onDataAChange" @clear-click="onDataAChange" />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('catalogo.nuovo_articolo')" @click="emit('new')" />
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
      <Column field="codice" :header="t('catalogo.col_codice')" sortable style="width: 140px;" />
      <Column field="descrizione" :header="t('catalogo.col_descrizione')" sortable style="min-width: 200px;" />
      <Column field="uom_codice" :header="t('catalogo.col_uom')" sortable style="width: 90px;" />
      <Column field="tipologia_descrizione" :header="t('catalogo.col_tipologia')" style="width: 140px;" />
      <Column field="gruppo_descrizione" :header="t('catalogo.col_gruppo')" style="width: 140px;" />
      <Column field="iva_ref_id" :header="t('catalogo.col_iva')" style="width: 80px;">
        <template #body="{ data }">{{ data.iva_aliquota_iva != null ? `${data.iva_aliquota_iva}%` : '' }}</template>
      </Column>
      <Column field="is_composito" :header="t('catalogo.col_composito')" style="width: 100px;">
        <template #body="{ data }">
          <Tag :value="data.is_composito ? t('common.yes') : t('common.no')" :severity="data.is_composito ? 'info' : 'secondary'" />
        </template>
      </Column>
      <Column field="attivo" :header="t('catalogo.col_attivo')" style="width: 90px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
      <Column field="data_insert" :header="t('catalogo.col_data_insert')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_insert) }}</template>
      </Column>
    </DataTable>
  </div>
</template>
