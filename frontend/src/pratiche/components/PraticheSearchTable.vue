<script setup>
// Scopo: DataTable paginata pratiche con search, filtro stato e priorita'.
// Pattern standard: useSearchTable + NewButton + useTabFreshness.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePraticheStore } from '../stores/pratiche'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useLookup } from '../../core/composables/useLookup'
import { lookupCodici } from '../../core/apiCore'
import { displayDate } from '../../core/utils/date'
import { statoPraticaSeverity, prioritaPraticaSeverity } from '../../core/utils/severity'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = usePraticheStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'date_insert',
  defaultSortOrder: -1
})

// Lookup filtri
const statiPratica = useLookup(() => lookupCodici('config.stati_pratiche'), { immediate: true })
const prioritaPratica = useLookup(() => lookupCodici('config.priorita_pratiche'), { immediate: true })

const statoFilter = ref(null)
const prioritaFilter = ref(null)

function onStatoChange() {
  store.filters.stato_id = statoFilter.value
  applyFilters()
}

function onPrioritaChange() {
  store.filters.priorita_id = prioritaFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, 'pratica')
onMounted(() => { store.fetchList() })
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('pratiche.search_placeholder')"
        />
        <Select
          v-model="statoFilter"
          :options="statiPratica.items.value"
          :loading="statiPratica.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('pratiche.filtro_stato')"
          show-clear
          @change="onStatoChange"
        />
        <Select
          v-model="prioritaFilter"
          :options="prioritaPratica.items.value"
          :loading="prioritaPratica.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('pratiche.filtro_priorita')"
          show-clear
          @change="onPrioritaChange"
        />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('pratiche.nuova_pratica')" @click="emit('new')" />
      </div>
    </div>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy
      removable-sort
      striped-rows
      scrollable
      scrollHeight="flex"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      selection-mode="single"
      data-key="id"
    >
      <Column field="codice" :header="t('pratiche.col_codice')" sortable style="width: 130px;" />
      <Column field="tipo_prestazione_descrizione" :header="t('pratiche.col_tipo_prestazione')" sortable style="width: 160px;" />
      <Column field="soggetto_display" :header="t('pratiche.col_soggetto')" sortable style="width: 200px;" />
      <Column field="stato_descrizione" :header="t('pratiche.col_stato')" sortable style="width: 110px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoPraticaSeverity(data.stato_codice_interno)" />
        </template>
      </Column>
      <Column field="priorita_descrizione" :header="t('pratiche.col_priorita')" sortable style="width: 110px;">
        <template #body="{ data }">
          <Tag v-if="data.priorita_descrizione" :value="data.priorita_descrizione" :severity="prioritaPraticaSeverity(data.priorita_codice_interno)" />
        </template>
      </Column>
      <Column field="risorsa_umana_display" :header="t('pratiche.col_assegnata_a')" sortable style="width: 160px;" />
      <Column field="data_scadenza" :header="t('pratiche.col_data_scadenza')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_scadenza) }}</template>
      </Column>
      <Column field="date_insert" :header="t('pratiche.col_data_apertura')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.date_insert) }}</template>
      </Column>
    </DataTable>
  </div>
</template>
