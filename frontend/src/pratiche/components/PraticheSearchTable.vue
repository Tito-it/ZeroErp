<script setup>
// Scopo: Lista pratiche configurabile
//        (`<ListaConfigurabile codice="pratiche.pratiche">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente. I campi display (stato_descrizione,
//        soggetto_display, ecc.) arrivano dal backend via JOIN; i lookup
//        servono solo a popolare i filtri Select. Nessun export: il dominio non
//        ha endpoint (lo scaffolding omette l'azione da se', non ricevendo
//        `exportFn`).
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePraticheStore } from '../stores/pratiche'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { toDateString } from '../../core/utils/date'
import { statoPraticaSeverity, prioritaPraticaSeverity } from '../../core/utils/severity'
import InputText from 'primevue/inputtext'
import LookupSelect from '../../core/components/LookupSelect.vue'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = usePraticheStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'pratiche.nuova_pratica',
  onNew: () => emit('new'),
  // 'desc' (stringa), NON -1: il contratto di useSearchTable e' 'asc'/'desc'.
  // Il -1 storico era dormiente (lo store preimposta gia' order_by/order_dir,
  // quindi il ramo default non scatta), ma se mai scattasse -1 finirebbe in
  // `order_dir` cosi' com'e': BE in fallback ASC e freccia header spenta.
  searchTableOptions: { defaultSortField: 'data_apertura', defaultSortOrder: 'desc' },
})

// Init dallo store (persistente nella sessione, userScoped): al rientro in
// dashboard i Select devono riflettere i filtri ancora attivi sulla lista
// (stesso pattern di dataDaFilter; prima stato/priorita ripartivano null →
// lista filtrata ma Select visivamente vuoti).
const statoFilter = ref(store.filters.stato ?? null)
const prioritaFilter = ref(store.filters.priorita_id ?? null)
// Filtro tipo prestazione: preimpostabile dal deep-link della home launcher
// (tile "Comincia" → dashboard filtrata sul tipo). Il watch tiene il Select
// allineato quando il deep-link cambia il filtro a componente GIA' montato:
// sotto KeepAlive la dashboard viene ri-attivata senza remount, quindi
// l'init a setup-time da solo non basta.
const tipoPrestazioneFilter = ref(store.filters.tipo_prestazione_id ?? null)
watch(() => store.filters.tipo_prestazione_id, v => { tipoPrestazioneFilter.value = v ?? null })
// Lente di contesto D1 (workflow v2): solo pratiche interne (senza soggetto).
const soloInterneFilter = ref(store.filters.solo_interne || false)

// Filtro data sempre attivo: default inizio mese precedente (dal store)
const dataDaFilter = ref(store.filters.data_da ? new Date(store.filters.data_da + 'T00:00:00') : null)
const dataAFilter = ref(null)

function onStatoChange() {
  // value-field="codice": il BE filtra per codice_interno (param `stato`);
  // per gli stati pratiche codice e codice_interno coincidono (seed).
  store.filters.stato = statoFilter.value
  applyFilters()
}

function onPrioritaChange() {
  store.filters.priorita_id = prioritaFilter.value
  applyFilters()
}

function onTipoPrestazioneChange() {
  store.filters.tipo_prestazione_id = tipoPrestazioneFilter.value
  applyFilters()
}

function onSoloInterneChange() {
  store.filters.solo_interne = soloInterneFilter.value
  applyFilters()
}

function onDataDaChange() {
  store.filters.data_da = dataDaFilter.value ? toDateString(dataDaFilter.value) : null
  applyFilters()
}

function onDataAChange() {
  store.filters.data_a = dataAFilter.value ? toDateString(dataAFilter.value) : null
  applyFilters()
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

useTabFreshness(store, TAB_ENTITIES.PRATICA)

// Lista eager: carica subito col filtro data sempre attivo (default inizio
// mese precedente impostato dallo store). L'altezza di scroll non si calcola
// piu' a mano (ResizeObserver + listener resize rimossi): `<ListaConfigurabile>`
// fissa `scrollable` + `scroll-height="flex"`, che e' la regola del pattern.
onMounted(() => { store.fetchList() })
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('pratiche.search_placeholder')"
        />
        <LookupSelect
          v-model="statoFilter"
          rel="config.stati_pratiche"
          value-field="codice"
          :placeholder="t('pratiche.filtro_stato')"
          show-clear
          @change="onStatoChange"
        />
        <LookupSelect
          v-model="prioritaFilter"
          rel="config.priorita_pratiche"
          :placeholder="t('pratiche.filtro_priorita')"
          show-clear
          @change="onPrioritaChange"
        />
        <LookupSelect
          v-model="tipoPrestazioneFilter"
          rel="pratiche.tipi_prestazione"
          :placeholder="t('pratiche.filtro_tipo_prestazione')"
          show-clear
          @change="onTipoPrestazioneChange"
        />
        <DatePicker
          v-model="dataDaFilter"
          :placeholder="t('common.data_da')"
          date-format="dd/mm/yy"
          show-icon
          show-button-bar
          style="width: 150px;"
          @date-select="onDataDaChange"
          @clear-click="onDataDaChange"
        />
        <DatePicker
          v-model="dataAFilter"
          :placeholder="t('common.data_a')"
          date-format="dd/mm/yy"
          show-icon
          show-button-bar
          style="width: 150px;"
          @date-select="onDataAChange"
          @clear-click="onDataAChange"
        />
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <ToggleSwitch v-model="soloInterneFilter" inputId="pratiche-solo-interne"
            @change="onSoloInterneChange" />
          <label for="pratiche-solo-interne" style="font-size: 0.85rem; cursor: pointer;">
            {{ t('pratiche.filtro_solo_interne') }}
          </label>
        </div>
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
      codice="pratiche.pratiche"
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
      <!-- Le date non hanno slot: il seed dichiara `date_short` /
           `datetime_short` e il formatter di serie le rende gia' cosi'. -->
      <template #cell-priorita="{ data }">
        <Tag v-if="data.priorita_descrizione" :value="data.priorita_descrizione"
          :severity="prioritaPraticaSeverity(data.priorita_codice_interno)" />
      </template>
      <template #cell-stato="{ data }">
        <Tag :value="data.stato_descrizione" :severity="statoPraticaSeverity(data.stato_codice_interno)" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>
