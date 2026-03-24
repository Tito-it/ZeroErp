<script setup>
// Scopo: DataTable regioni con ricerca e CRUD.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRegioniStore } from '../../anagrafiche/stores/regioni'
import { useSearchTable } from '../composables/useSearchTable'
import { useTabFreshness } from '../composables/useTabFreshness'
import NewButton from './NewButton.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useRegioniStore()
const { searchText, onPage, onSort, reload, paginatorProps } = useSearchTable(store, { defaultSortField: 'descrizione' })

useTabFreshness(store, 'regione')
onMounted(() => { store.fetchList() })

function onRowClick(event) { emit('row-click', event.data) }
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('geo.search_regione')" />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('geo.nuova_regione')" @click="emit('new')" />
      </div>
    </div>
    <DataTable
      :value="store.items" :loading="store.loading" v-bind="paginatorProps"
      lazy removable-sort striped-rows scrollable scrollHeight="flex"
      class="app-datatable" @page="onPage" @sort="onSort"
      @row-click="onRowClick" selection-mode="single" data-key="id"
    >
      <Column field="descrizione" :header="t('geo.col_descrizione')" sortable />
      <Column field="stato_descrizione" :header="t('geo.col_stato')" sortable />
    </DataTable>
  </div>
</template>
