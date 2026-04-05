<script setup>
// Scopo: DataTable conversioni UoM. Dataset piccolo caricato tutto,
// paginazione/sort client-side, layout standard via useSearchTable.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConversioniUomStore } from '../stores/conversioniUom'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useConversioniUomStore()
const { searchText, onPage, onSort, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'uom_from_descrizione'
})

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, 'conversioni_uom')
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('catalogo.conv_search_placeholder')" />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('catalogo.nuova_conversione')" @click="emit('new')" />
      </div>
    </div>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy removable-sort striped-rows scrollable scrollHeight="flex"
      class="app-datatable"
      @page="onPage" @sort="onSort" @row-click="onRowClick"
      selection-mode="single" data-key="id"
    >
      <Column field="uom_from_codice" :header="t('catalogo.col_uom_da')" sortable style="width: 140px;" />
      <Column field="uom_from_descrizione" :header="t('catalogo.col_desc_da')" sortable style="min-width: 180px;" />
      <Column field="uom_to_codice" :header="t('catalogo.col_uom_a')" sortable style="width: 140px;" />
      <Column field="uom_to_descrizione" :header="t('catalogo.col_desc_a')" style="min-width: 180px;" />
      <Column field="fattore" :header="t('catalogo.col_fattore')" sortable style="width: 120px;">
        <template #body="{ data }">
          <span class="font-mono">{{ data.fattore }}</span>
        </template>
      </Column>
      <Column field="attivo" :header="t('catalogo.col_attivo')" style="width: 90px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.font-mono { font-family: monospace; }
</style>
