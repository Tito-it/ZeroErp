<script setup>
// Scopo: DataTable conversioni UoM. Dataset piccolo caricato tutto,
// paginazione/sort client-side, layout standard via useSearchTable.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConversioniUomStore } from '../stores/conversioniUom'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import AttivoTag from '../../core/components/AttivoTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useConversioniUomStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'uom_from_descrizione'
})
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
    tooltip: t('catalogo.nuova_conversione'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, TAB_ENTITIES.CONVERSIONI_UOM)
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('catalogo.conv_search_placeholder')" />
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
          <AttivoTag :active="data.attivo" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>

<style scoped>
.font-mono { font-family: monospace; }
</style>
