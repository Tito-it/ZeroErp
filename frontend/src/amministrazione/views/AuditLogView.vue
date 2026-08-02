<script setup>
// Scopo: pagina del log di audit globale
//        (`<ListaConfigurabile codice="storico.audit_log">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente. Sola consultazione: niente "Nuovo",
//        niente click di riga (non c'e' un drawer), niente export — lo
//        scaffolding omette da se' le azioni senza handler.
//
// Niente casella di ricerca: l'endpoint audit non ha ricerca testuale e nel
// seed tutte le colonne sono `ricercabile_full=f`. Il filtro e' per sorgente
// (`tabella`) e per intervallo di date.
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useAuditLogStore } from '../stores/auditLog'
import { lookupAuditSources } from '../api/amministrazione'
import { parseIsoDate, toDateString } from '../../core/utils/date'
import { getAuditOpSeverity } from '../constants'
import { DATE_FORMAT, READONLY_DOMAINS } from '../../core/constants'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
const store = useAuditLogStore()

const {
  onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  searchTableOptions: {
    // Allineato al preset del seed (`timestamp desc`). Va detto in entrambi i
    // posti: quando lo store preimposta `order_by` questo resta dormiente, ma
    // lasciarlo indietro fa divergere i due se un domani lo store cambia.
    defaultSortField: 'timestamp',
    defaultSortOrder: 'desc',
  },
})

// Lookup sorgenti audit dal BE (single source of truth: `script.vw_audit_sources`).
// Cache modulo-level via useGlobalLookup; transform perche' l'endpoint ritorna
// una lista nuda, non l'envelope paginato.
const auditSourcesLookup = useGlobalLookup(
  'amm.audit_sources',
  lookupAuditSources,
  { immediate: true, transform: (r) => r.data.data },
)

// Options del Select: voce "Tutti" + i codici dal BE. `label_key` arriva come
// chiave i18n e va risolta con t(); `value` e' il `code` del BE.
const tabellaOptions = computed(() => [
  { label: t('amministrazione.audit_tabella_tutti'), value: null },
  ...auditSourcesLookup.items.value.map((s) => ({
    label: t(s.label_key),
    value: s.code,
  })),
])

// I DatePicker lavorano su Date, lo store su stringhe ISO: la conversione passa
// per parseIsoDate/toDateString (locale-safe, niente shift di fuso).
const dataDaFilter = ref(parseIsoDate(store.filters.data_da))
const dataAFilter = ref(parseIsoDate(store.filters.data_a))

function onTabellaChange() {
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

// `summary` arriva gia' calcolato dal BE in `data.audit.summary`
// (`script.fn_audit_summary`): nessun parsing dello snapshot lato client. Il
// dettaglio per campo resta disponibile in `data.audit.diff`.
function rowSummary(data) {
  return data?.audit?.summary || ''
}

onMounted(() => {
  store.fetchList()
})
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <Select
          v-model="store.filters.tabella"
          :options="tabellaOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.audit_col_tipo')"
          style="width: 220px;"
          @change="onTabellaChange"
        />
        <DatePicker
          v-model="dataDaFilter"
          :placeholder="t('common.data_da')"
          :date-format="DATE_FORMAT"
          show-icon
          show-button-bar
          style="width: 150px;"
          @date-select="onDataDaChange"
          @clear-click="onDataDaChange"
        />
        <DatePicker
          v-model="dataAFilter"
          :placeholder="t('common.data_a')"
          :date-format="DATE_FORMAT"
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
      codice="storico.audit_log"
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
      <!-- `timestamp` non ha slot: il seed dichiara `datetime_short` e il
           formatter del catalogo la rende gia' cosi'. Mettere uno slot qui
           salterebbe il formatter e toccherebbe formattare a mano. -->
      <template #cell-tabella="{ data }">
        <Tag :value="data.tabella" severity="secondary" />
      </template>
      <template #cell-tipo_operazione="{ data }">
        <Tag :value="data.tipo_operazione" :severity="getAuditOpSeverity(data.tipo_operazione)" />
      </template>
      <!-- Colonna calcolata lato FE: nel seed ha `campo_sorgente` vuoto, quindi
           il valore puo' arrivare solo da qui. -->
      <template #cell-dettaglio="{ data }">
        <span class="text-sm">{{ rowSummary(data) }}</span>
      </template>
    </ListaConfigurabile>
  </div>
</template>
