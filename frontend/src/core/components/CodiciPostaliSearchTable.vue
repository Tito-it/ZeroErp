<script setup>
// Scopo: DataTable codici postali con ricerca, filtro comune e CRUD.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCodiciPostaliStore } from '../../anagrafiche/stores/codiciPostali'
import { useSearchTable } from '../composables/useSearchTable'
import { useTabFreshness } from '../composables/useTabFreshness'
import ComuneAutocomplete from './ComuneAutocomplete.vue'
import NewButton from './NewButton.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useCodiciPostaliStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, { defaultSortField: 'comune_descrizione' })

const comuneFilter = ref(null)

useTabFreshness(store, 'codice_postale')
onMounted(() => { store.fetchList() })

function onComuneChange(id) {
  comuneFilter.value = id
  store.filters.comune_id = id
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('indirizzi.search_cap')" />
        <ComuneAutocomplete :model-value="comuneFilter" @update:model-value="onComuneChange" />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('indirizzi.nuovo_cap')" @click="emit('new')" />
      </div>
    </div>
    <DataTable
      :value="store.items" :loading="store.loading" v-bind="paginatorProps"
      lazy removable-sort striped-rows scrollable scrollHeight="flex"
      class="app-datatable" @page="onPage" @sort="onSort"
      @row-click="onRowClick" selection-mode="single" data-key="id"
    >
      <Column field="codice" :header="t('indirizzi.col_cap')" sortable />
      <Column field="comune_descrizione" :header="t('indirizzi.col_comune')" sortable />
    </DataTable>
  </div>
</template>
