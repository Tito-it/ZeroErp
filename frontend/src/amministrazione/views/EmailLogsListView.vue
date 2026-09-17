<script setup>
// Scopo: Lista log email configurabile
//        (`<ListaConfigurabile codice="config.email_log">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente. Lista di sola consultazione: niente
//        "Nuovo", niente click di riga (non c'e' un drawer di dettaglio) e
//        niente export — lo scaffolding omette le azioni da se'.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { useEmailLogsStore } from '../stores/emailLogs'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { getEmailLogStatoSeverity } from '../constants'
import { toDateString } from '../../core/utils/date'
import EmailLogStatoSelect from '../components/EmailLogStatoSelect.vue'

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

// Filtro data: default ultimi 30 giorni
const dataDaFilter = ref(store.filters.data_da ? new Date(store.filters.data_da + 'T00:00:00') : null)
const dataAFilter = ref(null)

function onStatoChange(val) {
  store.filters.stato = val
  store.filters.offset = 0
  store.fetchList()
}

function onDataDaChange() {
  store.filters.data_da = dataDaFilter.value ? toDateString(dataDaFilter.value) : null
  applyFilters()
}

function onDataAChange() {
  store.filters.data_a = dataAFilter.value ? toDateString(dataAFilter.value) : null
  applyFilters()
}

onMounted(() => {
  store.fetchList()
})
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters" :inert="perimetroBloccato">
        <InputText v-model="searchText" :placeholder="t('common.search')" style="width: 250px;" />
        <EmailLogStatoSelect
          :modelValue="store.filters.stato"
          :placeholder="t('amministrazione.email_stato')"
          style="width: 200px;"
          @update:modelValue="onStatoChange"
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
      </div>
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
