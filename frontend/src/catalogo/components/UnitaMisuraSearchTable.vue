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
import NewButton from '../../core/components/NewButton.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'

const emit = defineEmits(['new', 'row-click', 'manage-conversioni'])
const { t } = useI18n()
const store = useUnitaMisuraStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'descrizione'
})

const attivoFilter = ref(true)
const boolOptions = buildBoolOptions(t)

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

// Scopo: azioni di riga UoM (apre sub-drawer conversioni).
function buildRowActions(data) {
  return [
    {
      key: 'manage-conversioni',
      label: t('catalogo.gestisci_conversioni'),
      icon: MANAGE_ICONS.CONVERSIONI,
      command: () => emit('manage-conversioni', data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.UNITA_MISURA)
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('catalogo.uom_search_placeholder')" />
        <Select v-model="attivoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" style="width: 120px;" />
      </div>
      <div class="app-page-actions">
        <ReadonlyBadge />
        <ReloadButton @click="reload" />
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
      <Column field="tipo_uom_codice" :header="t('catalogo.uom_tipo')" style="width: 150px;" />
      <Column field="descrizione_fattura" :header="t('catalogo.col_desc_fattura')" style="min-width: 200px;" />
      <Column field="attivo" :header="t('catalogo.col_attivo')" style="width: 90px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
