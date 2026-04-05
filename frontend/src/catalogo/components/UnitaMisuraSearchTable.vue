<script setup>
// Scopo: DataTable paginata unita' di misura con search e filtro attivo.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUnitaMisuraStore } from '../stores/unitaMisura'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'
import { MANAGE_ICONS } from '../../core/constants'

const emit = defineEmits(['new', 'row-click', 'manage-conversioni'])
const { t } = useI18n()
const store = useUnitaMisuraStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'descrizione'
})

const attivoFilter = ref(true)
const boolOptions = [
  { value: null, label: t('common.all') },
  { value: true, label: t('common.yes') },
  { value: false, label: t('common.no') }
]

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, 'unita_misura')
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('catalogo.uom_search_placeholder')" />
        <Select v-model="attivoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" style="width: 120px;" />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('catalogo.nuova_uom')" @click="emit('new')" />
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
      <Column field="codice" :header="t('catalogo.col_codice')" sortable style="width: 140px;" />
      <Column field="descrizione" :header="t('catalogo.col_descrizione')" sortable style="min-width: 250px;" />
      <Column field="descrizione_fattura" :header="t('catalogo.col_desc_fattura')" style="min-width: 200px;" />
      <Column field="attivo" :header="t('catalogo.col_attivo')" style="width: 90px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
      <Column style="width: 50px;">
        <template #body="{ data }">
          <div @click.stop>
            <Button :icon="MANAGE_ICONS.CONVERSIONI" text rounded size="small" class="app-manage-btn"
              v-tooltip.bottom="t('catalogo.gestisci_conversioni')" @click="emit('manage-conversioni', data)" />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</template>
