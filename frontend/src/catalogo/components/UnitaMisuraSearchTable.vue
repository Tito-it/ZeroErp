<script setup>
// Scopo: Lista unita' di misura configurabile
//        (`<ListaConfigurabile codice="catalogo.unita_misura">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro
//        dinamico e personalizzazione per utente. Nessun export: il dominio non
//        ha endpoint (lo scaffolding omette l'azione da se').
import { onMounted } from 'vue'
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
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'

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

// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const boolOptions = buildBoolOptions(t)

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
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText class="app-filter-w-lg" v-model="searchText" :placeholder="t('catalogo.uom_search_placeholder')" />
        </template>
        <Select v-model="attivoFilter" :options="boolOptions" option-label="label" option-value="value"
          class="app-filter-w-sm"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" />
      </FiltriLista>
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

      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>
