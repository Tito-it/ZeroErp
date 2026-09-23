<script setup>
// Scopo: Lista log email configurabile
//        (`<ListaConfigurabile codice="config.email_log">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente. Lista di sola consultazione: niente
//        "Nuovo", niente click di riga (non c'e' un drawer di dettaglio) e
//        niente export — lo scaffolding omette le azioni da se'.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { useEmailLogsStore } from '../stores/emailLogs'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { getEmailLogStatoSeverity } from '../constants'
import EmailLogStatoSelect from '../components/EmailLogStatoSelect.vue'
import FiltroPeriodo from '../../core/components/FiltroPeriodo.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import FiltriLista from '../../core/components/FiltriLista.vue'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
const store = useEmailLogsStore()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  searchTableOptions: {
    defaultSortField: 'data_insert',
    // 'desc', NON -1: il contratto di useSearchTable e' 'asc'/'desc' (il -1
    // era dormiente solo perche' lo store preimposta gia' order_by/order_dir).
    defaultSortOrder: 'desc',
  },
})

// Email logs e' read-only (nessun create/update/delete) quindi non serve
// ascoltare eventi cross-tab: nessuno store emette EMAIL_LOGS.

// Fase 5 — il filtro stato usa EmailLogStatoSelect, lookup BE cached con
// useGlobalLookup. Sostituisce buildEmailLogStatoOptions hardcoded.
// `getEmailLogStatoSeverity` resta locale (puro mapping CSS, non semantico).

// Il periodo e' UN filtro con due estremi: un binding, un componente.
// ⭐ Prima del 2026-09-23 i due estremi erano due ref scritte a mano, e
//    `data_a` NON leggeva lo store alla nascita (`ref(null)` secco): un valore
//    rimasto nel filtro restava attivo con la casella vuota. Il BB legge
//    entrambi gli estremi dallo store, li tiene allineati anche quando li
//    cambia qualcun altro, e porta l'invariante `da <= a`.
const { bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const periodo = bindPeriodo()

function onStatoChange(val) {
  store.filters.stato = val
  store.filters.offset = 0
  store.fetchList()
}

onMounted(() => {
  store.fetchList()
})
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText v-model="searchText" class="app-filter-w-lg" :placeholder="t('common.search')" />
        </template>
        <EmailLogStatoSelect
          class="app-filter-w-sm"
          :modelValue="store.filters.stato"
          :placeholder="t('amministrazione.email_stato')"
          @update:modelValue="onStatoChange"
        />
        <FiltroPeriodo :periodo="periodo" />
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="config.email_log"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @config-loaded="onConfigLoaded"
    >
      <!-- La data non ha slot: il seed dichiara `datetime_short` e il formatter
           di serie la rende gia' cosi'. -->
      <template #cell-errore="{ data }">
        <span v-if="data.errore" style="font-size: 0.85rem;">{{ data.errore }}</span>
      </template>
      <template #cell-stato="{ data }">
        <Tag :value="data.stato" :severity="getEmailLogStatoSeverity(data.stato)" />
      </template>
    </ListaConfigurabile>
  </div>
</template>
