<script setup>
// Scopo: DataTable paginata soggetti con search e filtro tipo.
// Riusabile da: SoggettiView, futuro ricerca soggetti in altri domini.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSoggettiStore } from '../stores/soggetti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useLookup } from '../../core/composables/useLookup'
import { lookupTipiSoggettoDettaglio } from '../../core/apiCore'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import NewButton from '../../core/components/NewButton.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useSoggettiStore()
const { searchText, onPage, onSort, applyFilters, paginatorProps } = useSearchTable(store)

const tipiSoggetto = useLookup(lookupTipiSoggettoDettaglio, { immediate: true })
const tipoFilter = ref(null)

function onTipoChange() {
  store.filters.tipo_soggetto_dettaglio_id = tipoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, 'soggetto')
onMounted(() => { store.fetchList() })
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('soggetti.search_placeholder')"
        />
        <Select
          v-model="tipoFilter"
          :options="tipiSoggetto.items.value"
          :loading="tipiSoggetto.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('soggetti.filtro_tipo')"
          show-clear
          @change="onTipoChange"
        />
      </div>
      <NewButton :tooltip="t('soggetti.nuovo_soggetto')" @click="emit('new')" />
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
      <Column field="ragione_sociale_completa" :header="t('soggetti.col_ragione_sociale')" sortable />
      <Column field="codice_fiscale" :header="t('common.codice_fiscale')" sortable />
      <Column field="partita_iva" :header="t('common.partita_iva')" sortable />
      <Column field="tipo_descrizione" :header="t('soggetti.col_tipo')" sortable />
    </DataTable>
  </div>
</template>
