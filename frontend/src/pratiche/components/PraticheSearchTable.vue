<script setup>
// Scopo: DataTable paginata pratiche con search, filtro stato, priorita' e data.
// I campi display (stato_descrizione, soggetto_display, ecc.) arrivano dal backend via JOIN.
// I lookup servono solo per popolare i filtri Select.
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePraticheStore } from '../stores/pratiche'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useLookup } from '../../core/composables/useLookup'
import { lookupCodici } from '../../core/apiCore'
import { displayDate, toDateString } from '../../core/utils/date'
import { statoPraticaSeverity, prioritaPraticaSeverity } from '../../core/utils/severity'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'
import SearchHint from '../../core/components/SearchHint.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = usePraticheStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'data_insert',
  defaultSortOrder: -1
})

// Lookup per popolare i filtri Select (non per le colonne — quelle usano i dati dal backend)
const statiPratica = useLookup(() => lookupCodici('config.stati_pratiche'), { immediate: true })
const prioritaPratica = useLookup(() => lookupCodici('config.priorita_pratiche'), { immediate: true })

const statoFilter = ref(null)
const prioritaFilter = ref(null)

// Filtro data: default anno corrente - 1 (dal store)
const dataDaFilter = ref(store.filters.data_da ? new Date(store.filters.data_da + 'T00:00:00') : null)
const dataAFilter = ref(null)

function onStatoChange() {
  store.filters.stato_id = statoFilter.value
  applyFilters()
}

function onPrioritaChange() {
  store.filters.priorita_id = prioritaFilter.value
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

useTabFreshness(store, 'pratica')
// La lista parte vuota — l'operatore deve cercare o applicare un filtro.

// Scopo: calcolo dinamico altezza scroll DataTable.
// Desktop (>=1280px): calcola altezza dal viewport reale meno area flussi.
// Mobile/tablet (<1280px): niente scroll interno, la pagina scrolla.
const tableContainer = ref(null)
const tableScrollHeight = ref(null)

function recalcScrollHeight() {
  if (window.innerWidth < 1280) {
    // Mobile/tablet: niente scroll interno DataTable, scrolla il container padre
    tableScrollHeight.value = null
    return
  }
  if (!tableContainer.value) return
  const rect = tableContainer.value.getBoundingClientRect()
  const available = window.innerHeight - rect.top - 100 - 240
  tableScrollHeight.value = Math.max(available, 150) + 'px'
}

onMounted(() => {
  recalcScrollHeight()
  window.addEventListener('resize', recalcScrollHeight)
})
onUnmounted(() => { window.removeEventListener('resize', recalcScrollHeight) })
</script>

<template>
  <div ref="tableContainer" class="app-tab-content">
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
        <DatePicker
          v-model="dataDaFilter"
          :placeholder="t('common.data_da')"
          date-format="dd/mm/yy"
          show-icon
          show-button-bar
          style="width: 150px;"
          @date-select="onDataDaChange"
          @clear-click="onDataDaChange"
        />
        <DatePicker
          v-model="dataAFilter"
          :placeholder="t('common.data_a')"
          date-format="dd/mm/yy"
          show-icon
          show-button-bar
          style="width: 150px;"
          @date-select="onDataAChange"
          @clear-click="onDataAChange"
        />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('pratiche.nuova_pratica')" @click="emit('new')" />
      </div>
    </div>

    <!-- Placeholder: nessuna ricerca effettuata -->
    <SearchHint v-if="!store.hasSearched && !store.loading" :message="t('pratiche.eseguire_ricerca')" />

    <DataTable
      v-show="store.hasSearched || store.loading"
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy
      removable-sort
      striped-rows
      :scrollable="!!tableScrollHeight"
      :scrollHeight="tableScrollHeight || undefined"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      selection-mode="single"
      data-key="id"
    >
      <Column field="codice" :header="t('pratiche.col_codice')" sortable style="width: 140px;" />
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
      <Column field="data_apertura" :header="t('pratiche.col_data_apertura')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_apertura) }}</template>
      </Column>
    </DataTable>
  </div>
</template>

