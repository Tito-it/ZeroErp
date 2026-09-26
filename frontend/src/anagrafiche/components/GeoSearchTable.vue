<script setup>
// Scopo: lista "semplice" (pre-blocco-D, niente <ListaConfigurabile>) per le
//        tabelle geografiche/anagrafiche di base. Estrazione regola del 2
//        (2026-06-05): 6 SearchTable (Regioni/Province/Stati/Comuni/CodiciPostali/
//        Toponomastica) ripetevano identici lo scaffold useSearchTable +
//        pageActions[reload,new] + useTabFreshness + DataTable. Diventano wrapper
//        ~20 righe. Distinto da useListaConfigurabilePage (per le liste "ricche"
//        con personalizzazione colonne).
//
// Differenze assorbite via props/slot:
//   - rowClickable: Comuni non e' selezionabile (solo "new").
//   - slot `filters` (scoped, espone applyFilters): filtro extra di CodiciPostali.
//   - slot `cell-<field>` (scoped, { data }): cella custom (es. Tag attivo).
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { MANAGE_ICONS } from '../../core/constants'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import FiltriLista from '../../core/components/FiltriLista.vue'

const props = defineProps({
  store: { type: Object, required: true },
  columns: { type: Array, required: true }, // [{ field, headerKey, sortable? }]
  searchPlaceholderKey: { type: String, required: true },
  newTooltipKey: { type: String, required: true },
  tabEntity: { type: String, required: true }, // valore TAB_ENTITIES
  defaultSortField: { type: String, default: 'descrizione' },
  rowClickable: { type: Boolean, default: true },
})
const emit = defineEmits(['row-click', 'new'])

const { t } = useI18n()
const { searchText, onPage, onSort, applyFilters, reloadAction, paginatorProps } =
  useSearchTable(props.store, { defaultSortField: props.defaultSortField })

const pageActions = computed(() => [
  reloadAction(), // include disabled = lista vuota (reattivo)
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t(props.newTooltipKey),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

useTabFreshness(props.store, props.tabEntity)
onMounted(() => { props.store.fetchList() })

function onRowClick(event) {
  if (props.rowClickable) emit('row-click', event.data)
}
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <FiltriLista :store="store">
        <template #sempre>
          <InputText class="app-filter-w-lg" v-model="searchText" :placeholder="t(searchPlaceholderKey)" />
        </template>
        <!-- ⚠️ `v-if` sullo slot, non `<slot>` nudo: uno `<slot>` scritto senza
             condizione E' un default slot per `FiltriLista` anche quando il
             caller non passa `#filters` — l'icona a imbuto comparirebbe su un
             drawer vuoto.
             ⚠️ La taglia la mette il CALLER sul proprio widget: qui non si sa
             che filtro sara'. -->
        <template v-if="$slots.filters" #default>
          <slot name="filters" :apply-filters="applyFilters" />
        </template>
      </FiltriLista>
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
      scroll-height="flex"
      class="app-datatable"
      :selection-mode="rowClickable ? 'single' : undefined"
      data-key="id"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
    >
      <Column
        v-for="col in columns"
        :key="col.field"
        :field="col.field"
        :header="t(col.headerKey)"
        :sortable="col.sortable !== false"
      >
        <template #body="slotProps">
          <slot
            v-if="$slots['cell-' + col.field]"
            :name="'cell-' + col.field"
            v-bind="slotProps"
          />
          <template v-else>{{ slotProps.data[col.field] }}</template>
        </template>
      </Column>
    </DataTable>
  </div>
</template>
