<script setup>
// Scopo: pagina audit log globale modifiche permessi.
// DataTable paginata con lazy loading e sort server-side, filtri per tipo tabella.
// Sola lettura — nessun drawer.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { getAuditLog } from '../api/amministrazione'
import { displayTimestamp, toDateString } from '../../core/utils/date'
import { buildAuditTabellaOptions, getAuditOpSeverity } from '../constants'
import { PAGINATION, DATE_FORMAT, READONLY_DOMAINS } from '../../core/constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)

const loading = ref(false)
const events = ref([])
const totalCount = ref(0)
const first = ref(0)
const rows = ref(PAGINATION.DEFAULT_ROWS)
let fetchSeq = 0

// Ordinamento
const sortField = ref('timestamp')
const sortOrder = ref(-1)

const tabellaFilter = ref(null)
const tabellaOptions = buildAuditTabellaOptions(t)

// Filtro data: default ultimo mese
const defaultDa = new Date()
defaultDa.setMonth(defaultDa.getMonth() - 1)
const dataDaFilter = ref(defaultDa)
const dataAFilter = ref(null)

function onDataDaChange() {
  first.value = 0
  fetchData()
}
function onDataAChange() {
  first.value = 0
  fetchData()
}

async function fetchData() {
  const seq = ++fetchSeq
  loading.value = true
  try {
    const params = { limit: rows.value, offset: first.value }
    if (dataDaFilter.value) params.data_da = toDateString(dataDaFilter.value)
    if (dataAFilter.value) params.data_a = toDateString(dataAFilter.value)
    if (tabellaFilter.value) params.tabella = tabellaFilter.value
    if (sortField.value) {
      params.order_by = sortField.value
      params.order_dir = sortOrder.value === 1 ? 'ASC' : 'DESC'
    }
    const res = await getAuditLog(params)
    if (seq !== fetchSeq) return
    const data = res.data?.data || {}
    events.value = data.results || []
    totalCount.value = data.count || 0
  } finally {
    if (seq === fetchSeq) loading.value = false
  }
}

onMounted(fetchData)

function onPage(event) {
  first.value = event.first
  rows.value = event.rows
  fetchData()
}

function onSort(event) {
  sortField.value = event.sortField
  sortOrder.value = event.sortOrder
  first.value = 0
  fetchData()
}

function applyFilters() {
  first.value = 0
  fetchData()
}

// Scopo: Estrae un riepilogo leggibile dallo snapshot JSON.
// Lo snapshot puo' arrivare come oggetto o stringa JSON.
function snapshotSummary(snapshot) {
  let obj = snapshot
  if (typeof obj === 'string') {
    try { obj = JSON.parse(obj) } catch { return '' }
  }
  if (!obj || typeof obj !== 'object') return ''
  const keys = ['auth_user_id', 'area_id', 'azione_id', 'unita_organizzativa_id',
    'livello', 'abilitata', 'ruolo_sistema', 'emittente_fiscale_id']
  return keys
    .filter(k => obj[k] !== undefined && obj[k] !== null)
    .map(k => `${k}: ${obj[k]}`)
    .join(', ')
}
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <Select
          v-model="tabellaFilter"
          :options="tabellaOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amm.audit_col_tipo')"
          @change="applyFilters"
        />
        <DatePicker
          v-model="dataDaFilter"
          :placeholder="t('common.data_da')"
          :dateFormat="DATE_FORMAT"
          showIcon showButtonBar
          style="width: 150px;"
          @date-select="onDataDaChange"
          @clear-click="onDataDaChange"
        />
        <DatePicker
          v-model="dataAFilter"
          :placeholder="t('common.data_a')"
          :dateFormat="DATE_FORMAT"
          showIcon showButtonBar
          style="width: 150px;"
          @date-select="onDataAChange"
          @clear-click="onDataAChange"
        />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="fetchData" />
      </div>
    </div>

    <DataTable
      :value="events"
      :loading="loading"
      :totalRecords="totalCount"
      :rows="rows"
      :first="first"
      :rowsPerPageOptions="PAGINATION.ROWS_OPTIONS"
      lazy
      paginator
      paginatorPosition="top"
      paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown CurrentPageReport"
      currentPageReportTemplate="{currentPage}/{totalPages}"
      striped-rows
      scrollable
      scrollHeight="flex"
      removable-sort
      :sortField="sortField"
      :sortOrder="sortOrder"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
    >
      <Column field="timestamp" :header="t('amm.audit_col_data')" sortable style="width: 12rem">
        <template #body="{ data }">
          {{ displayTimestamp(data.timestamp) }}
        </template>
      </Column>
      <Column field="user_modifica" :header="t('amm.audit_col_chi')" sortable style="width: 10rem" />
      <Column field="tabella" :header="t('amm.audit_col_tipo')" sortable style="width: 14rem">
        <template #body="{ data }">
          <Tag :value="data.tabella" severity="secondary" />
        </template>
      </Column>
      <Column field="tipo_operazione" :header="t('amm.audit_col_operazione')" sortable style="width: 8rem">
        <template #body="{ data }">
          <Tag :value="data.tipo_operazione" :severity="getAuditOpSeverity(data.tipo_operazione)" />
        </template>
      </Column>
      <Column :header="t('amm.audit_col_dettaglio')">
        <template #body="{ data }">
          <span class="text-sm">{{ snapshotSummary(data.snapshot) }}</span>
        </template>
      </Column>
    </DataTable>
  </div>
</template>
