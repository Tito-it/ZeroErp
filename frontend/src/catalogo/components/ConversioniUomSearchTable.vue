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
import FiltriLista from '../../core/components/FiltriLista.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useConversioniUomStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'catalogo.nuova_conversione',
  onNew: () => emit('new'),
  // `valido_al` DESC: regola di dominio sulle liste con date di validita'
  // (vedi lo store, che porta la stessa scelta e il perche' della direzione).
  searchTableOptions: { defaultSortField: 'valido_al', defaultSortOrder: 'desc' },
})

// ⛔ IL FILTRO C'ERA E NON SI VEDEVA (2026-09-23). Lo store dichiara
//    `attivo: true`, quindi questa lista ha SEMPRE mostrato le sole conversioni
//    attive — ma il blocco filtri portava la sola casella di ricerca, quindi
//    l'operatore non aveva nessun gesto per cambiarlo e, non essendoci uno slot
//    di filtri, `FiltriLista` non rendeva nemmeno l'icona: **nessun segno lo
//    diceva**. Una lista ristretta e una lista completa si leggevano uguali, che
//    e' esattamente il difetto per cui il segno dei filtri attivi esiste.
// ⭐ La forma e' quella gia' in uso sulle altre tre liste «attivo» di magazzino
//    (magazzini, lotti, ubicazioni): acceso = `attivo: null` (tutte), spento =
//    `true`. Col neutro a `null` il filtro smette di contare quando non
//    restringe, senza bisogno di dichiararlo.
const { bindToggle } = useStoreFilterBindings(store, applyFilters)
const { value: mostraNonAttive, onChange: onMostraNonAttiveChange } = bindToggle(
  'attivo', { on: null, off: true },
)

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
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText class="app-filter-w-lg" v-model="searchText" :placeholder="t('catalogo.conv_search_placeholder')" />
        </template>
        <FiltroToggle
          v-model="mostraNonAttive"
          :label="t('catalogo.conv_mostra_non_attive')"
          @change="onMostraNonAttiveChange"
        />
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
        <span class="app-mono">{{ data.fattore }}</span>
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>

<style scoped>
</style>
