<script setup>
// Scopo: Lista conversioni UoM configurabile
//        (`<ListaConfigurabile codice="catalogo.conversioni_uom">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`. Paginazione,
//        sort e search sono server-side (endpoint allineato alle due sorelle
//        UoM il 2026-08-01). Nessuna colonna azioni: il catalogo non la
//        prevede, la riga si apre col click.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConversioniUomStore } from '../stores/conversioniUom'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import InputText from 'primevue/inputtext'
import AttivoTag from '../../core/components/AttivoTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useConversioniUomStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'catalogo.nuova_conversione',
  onNew: () => emit('new'),
  // `valido_al` DESC: regola di dominio sulle liste con date di validita'
  // (vedi lo store, che porta la stessa scelta e il perche' della direzione).
  searchTableOptions: { defaultSortField: 'valido_al', defaultSortOrder: 'desc' },
})

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

useTabFreshness(store, TAB_ENTITIES.CONVERSIONI_UOM)
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters" :inert="perimetroBloccato">
        <InputText v-model="searchText" :placeholder="t('catalogo.conv_search_placeholder')" />
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
      codice="catalogo.conversioni_uom"
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
      <template #cell-fattore="{ data }">
        <span class="font-mono">{{ data.fattore }}</span>
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>

<style scoped>
.font-mono { font-family: monospace; }
</style>
