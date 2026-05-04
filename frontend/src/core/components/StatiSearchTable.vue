<script setup>
// Scopo: DataTable stati (nazioni) con ricerca e CRUD.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStatiStore } from '../../anagrafiche/stores/stati'
import { useSearchTable } from '../composables/useSearchTable'
import { useTabFreshness } from '../composables/useTabFreshness'
import { TAB_ENTITIES } from '../constants'
import NewButton from './NewButton.vue'
import ReloadButton from './ReloadButton.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useStatiStore()
const { searchText, onPage, onSort, reload, paginatorProps } = useSearchTable(store, { defaultSortField: 'descrizione' })

useTabFreshness(store, TAB_ENTITIES.STATO)
onMounted(() => { store.fetchList() })

function onRowClick(event) { emit('row-click', event.data) }
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('geo.search_stato')" />
      </div>
      <div class="app-page-actions">
        <ReloadButton @click="reload" />
        <NewButton :tooltip="t('geo.nuovo_stato')" @click="emit('new')" />
      </div>
    </div>
    <DataTable
      :value="store.items" :loading="store.loading" v-bind="paginatorProps"
      lazy removable-sort striped-rows scrollable scrollHeight="flex"
      class="app-datatable" @page="onPage" @sort="onSort"
      @row-click="onRowClick" selection-mode="single" data-key="id"
    >
      <Column field="descrizione" :header="t('geo.col_descrizione')" sortable />
      <Column field="codice_iso2" :header="t('geo.col_iso2')" sortable />
      <Column field="codice_iso3" :header="t('geo.col_iso3')" sortable />
      <Column field="continente" :header="t('geo.col_continente')" sortable />
    </DataTable>
  </div>
</template>
