<script setup>
// Scopo: Lista pratiche configurabile
//        (`<ListaConfigurabile codice="pratiche.pratiche">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente. I campi display (stato_descrizione,
//        soggetto_display, ecc.) arrivano dal backend via JOIN; i lookup
//        servono solo a popolare i filtri Select. Nessun export: il dominio non
//        ha endpoint (lo scaffolding omette l'azione da se', non ricevendo
//        `exportFn`).
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePraticheStore } from '../stores/pratiche'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { statoPraticaSeverity, prioritaPraticaSeverity } from '../../core/utils/severity'
import InputText from 'primevue/inputtext'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Tag from 'primevue/tag'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { TAB_ENTITIES } from '../../core/constants'
import FiltroPeriodo from '../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = usePraticheStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'pratiche.nuova_pratica',
  onNew: () => emit('new'),
  // 'desc' (stringa), NON -1: il contratto di useSearchTable e' 'asc'/'desc'.
  // Il -1 storico era dormiente (lo store preimposta gia' order_by/order_dir,
  // quindi il ramo default non scatta), ma se mai scattasse -1 finirebbe in
  // `order_dir` cosi' com'e': BE in fallback ASC e freccia header spenta.
  searchTableOptions: { defaultSortField: 'data_apertura', defaultSortOrder: 'desc' },
})

// ⭐ TUTTI i filtri di questa lista passano dai binder (dal 2026-09-23): ognuno
//    porta con se' il `watch` store → widget, che qui non e' un di piu' — e'
//    cio' che tiene il Select allineato quando il filtro lo cambia QUALCUN
//    ALTRO. Succede in tre modi: al rientro in dashboard (store `userScoped`,
//    i filtri sono ancora attivi sulla lista), dal deep-link della home
//    launcher (la tile «Comincia» atterra col tipo prestazione gia' scelto, e
//    sotto KeepAlive la view si ri-attiva SENZA remount) e dal «Pulisci
//    filtri» del drawer compatto.
//    ⛔ Fino al 2026-09-23 il `watch` c'era a mano per il SOLO tipo prestazione:
//    gli altri tre erano `ref` che spingevano nello store e basta, quindi
//    restavano a mostrare il filtro di prima. Nessun errore, da nessuna parte.
// ⚠️ L'interruttore usa il `null` di default di `bindToggle`: spento, il filtro
//    non va sul filo affatto. Fino al 2026-09-23 scriveva `false` — che il BE
//    legge come «assente» — e il segno lo contava come un filtro acceso su una
//    lista che non stava restringendo.
const { bindSelect, bindToggle, bindPeriodo } = useStoreFilterBindings(store, applyFilters)
// value-field="codice": il BE filtra per codice_interno (param `stato`); per
// gli stati pratiche codice e codice_interno coincidono (seed).
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato')
const { value: prioritaFilter, onChange: onPrioritaChange } = bindSelect('priorita_id')
const { value: tipoPrestazioneFilter, onChange: onTipoPrestazioneChange } = bindSelect('tipo_prestazione_id')
const { value: soloInterneFilter, onChange: onSoloInterneChange } = bindToggle('solo_interne')

// Il periodo e' UN filtro con due estremi: un binding, un componente.
// ⭐ Prima del 2026-09-23 erano due ref scritte a mano, e `data_a` NON leggeva
//    lo store alla nascita (`ref(null)` secco): un valore rimasto nel filtro
//    restava attivo con la casella vuota. Il BB legge entrambi gli estremi,
//    li tiene allineati anche quando li cambia qualcun altro (deep-link,
//    reset) e porta l'invariante «`da > a` non puo' esistere».
const periodo = bindPeriodo()

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
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText
            v-model="searchText"
            class="app-filter-w-lg"
            :placeholder="t('pratiche.search_placeholder')"
          />
        </template>
        <LookupSelect
          v-model="statoFilter"
          class="app-filter-w-md"
          rel="config.stati_pratiche"
          value-field="codice"
          :placeholder="t('pratiche.filtro_stato')"
          show-clear
          @change="onStatoChange"
        />
        <LookupSelect
          v-model="prioritaFilter"
          class="app-filter-w-md"
          rel="config.priorita_pratiche"
          :placeholder="t('pratiche.filtro_priorita')"
          show-clear
          @change="onPrioritaChange"
        />
        <LookupSelect
          v-model="tipoPrestazioneFilter"
          class="app-filter-w-md"
          rel="pratiche.tipi_prestazione"
          :placeholder="t('pratiche.filtro_tipo_prestazione')"
          show-clear
          @change="onTipoPrestazioneChange"
        />
        <FiltroPeriodo :periodo="periodo" />
        <FiltroToggle
          v-model="soloInterneFilter"
          :label="t('pratiche.filtro_solo_interne')"
          @change="onSoloInterneChange"
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
