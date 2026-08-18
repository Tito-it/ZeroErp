<script setup>
// Scopo: Lista unita' di misura configurabile
//        (`<ListaConfigurabile codice="catalogo.unita_misura">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro
//        dinamico e personalizzazione per utente. Nessun export: il dominio non
//        ha endpoint (lo scaffolding omette l'azione da se').
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUnitaMisuraStore } from '../stores/unitaMisura'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'

const emit = defineEmits(['new', 'row-click', 'manage-conversioni'])
const { t } = useI18n()
const store = useUnitaMisuraStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'catalogo.nuova_uom',
  onNew: () => emit('new'),
  // Allineato al preset default del seed (`codice asc`) e al filtro dello
  // store: la lista parte ordinata per codice.
  searchTableOptions: { defaultSortField: 'codice' },
})

const attivoFilter = ref(true)
const boolOptions = buildBoolOptions(t)

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

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
      <div class="app-page-filters" :inert="perimetroBloccato">
        <InputText v-model="searchText" :placeholder="t('catalogo.uom_search_placeholder')" />
        <Select v-model="attivoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" style="width: 120px;" />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="catalogo.unita_misura"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      @config-loaded="onConfigLoaded"
    >
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>

      <template #actions="{ data, compact }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" :force-compact="compact" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>
