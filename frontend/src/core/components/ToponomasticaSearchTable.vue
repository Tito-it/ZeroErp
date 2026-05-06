<script setup>
// Scopo: componente riutilizzabile — DataTable toponomastica con ricerca e CRUD.
// Riusabile da: tab Toponomastica in IndirizziView, futuro gestione stradario.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToponomasticaStore } from '../../anagrafiche/stores/toponomastica'
import { useSearchTable } from '../composables/useSearchTable'
import { useTabFreshness } from '../composables/useTabFreshness'
import { MANAGE_ICONS, TAB_ENTITIES } from '../constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import PageActionsBar from './PageActionsBar.vue'
import Tag from 'primevue/tag'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useToponomasticaStore()
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
    tooltip: t('indirizzi.nuova_toponomastica'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

useTabFreshness(store, TAB_ENTITIES.TOPONOMASTICA)
onMounted(() => { store.fetchList() })

function onRowClick(event) {
  emit('row-click', event.data)
}
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('indirizzi.search_toponomastica')"
        />
      </div>
      <PageActionsBar :actions="pageActions" />
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
      <Column field="descrizione" :header="t('indirizzi.col_descrizione')" sortable />
      <Column field="attivo" :header="t('indirizzi.col_attivo')" sortable>
        <template #body="{ data }">
          <Tag
            :value="data.attivo ? t('indirizzi.attivo') : t('indirizzi.non_attivo')"
            :severity="data.attivo ? 'success' : 'warn'"
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>
