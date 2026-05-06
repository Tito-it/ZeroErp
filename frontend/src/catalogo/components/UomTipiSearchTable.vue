<script setup>
// Scopo: DataTable paginata tipologie UoM con search e filtro attivo.
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUomTipiStore } from '../stores/uomTipi'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useUomTipiStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'descrizione'
})

const attivoFilter = ref(true)
const boolOptions = buildBoolOptions(t)
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
    tooltip: t('catalogo.nuovo_uom_tipo'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, TAB_ENTITIES.UOM_TIPI)
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('catalogo.uom_tipi_search_placeholder')" />
        <Select v-model="attivoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" style="width: 120px;" />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
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
      <Column field="codice" :header="t('catalogo.col_codice')" sortable style="width: 150px;" />
      <Column field="codice_interno" :header="t('catalogo.col_codice_interno')" sortable style="width: 180px;" />
      <Column field="descrizione" :header="t('catalogo.col_descrizione')" sortable style="min-width: 260px;" />
      <Column field="attivo" :header="t('catalogo.col_attivo')" style="width: 90px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
