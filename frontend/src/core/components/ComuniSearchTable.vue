<script setup>
// Scopo: componente riutilizzabile — DataTable comuni con ricerca e creazione.
// Riusabile da: tab Comuni in IndirizziView, futuro filtri clienti/fornitori.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useComuniStore } from '../../anagrafiche/stores/comuni'
import { useSearchTable } from '../composables/useSearchTable'
import { useTabFreshness } from '../composables/useTabFreshness'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import NewButton from './NewButton.vue'
import Button from 'primevue/button'

const emit = defineEmits(['new'])
const { t } = useI18n()
const store = useComuniStore()
const { searchText, onPage, onSort, reload, paginatorProps } = useSearchTable(store, { defaultSortField: 'descrizione' })

useTabFreshness(store, 'comune')
onMounted(() => { store.fetchList() })
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('indirizzi.search_comune')"
        />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('indirizzi.nuovo_comune')" @click="emit('new')" />
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
      data-key="id"
    >
      <Column field="descrizione" :header="t('indirizzi.col_comune')" sortable />
      <Column field="provincia_sigla" :header="t('indirizzi.col_provincia')" sortable />
      <Column field="regione_descrizione" :header="t('indirizzi.col_regione')" sortable />
    </DataTable>
  </div>
</template>
