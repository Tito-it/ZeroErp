<script setup>
// Scopo: DataTable province con ricerca e CRUD.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useProvinceStore } from '../../anagrafiche/stores/province'
import { useSearchTable } from '../composables/useSearchTable'
import { useTabFreshness } from '../composables/useTabFreshness'
import { MANAGE_ICONS, TAB_ENTITIES } from '../constants'
import PageActionsBar from './PageActionsBar.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useProvinceStore()
const { searchText, onPage, onSort, reload, paginatorProps } = useSearchTable(store, { defaultSortField: 'descrizione' })
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: reload,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('geo.nuova_provincia'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

useTabFreshness(store, TAB_ENTITIES.PROVINCIA)
onMounted(() => { store.fetchList() })

function onRowClick(event) { emit('row-click', event.data) }
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('geo.search_provincia')" />
      </div>
      <PageActionsBar :actions="pageActions" />
    </div>
    <DataTable
      :value="store.items" :loading="store.loading" v-bind="paginatorProps"
      lazy removable-sort striped-rows scrollable scrollHeight="flex"
      class="app-datatable" @page="onPage" @sort="onSort"
      @row-click="onRowClick" selection-mode="single" data-key="id"
    >
      <Column field="sigla" :header="t('geo.col_sigla')" sortable />
      <Column field="descrizione" :header="t('geo.col_descrizione')" sortable />
      <Column field="regione_descrizione" :header="t('geo.col_regione')" sortable />
    </DataTable>
  </div>
</template>
