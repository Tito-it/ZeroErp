<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { useEmailLogsStore } from '../stores/emailLogs'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { buildEmailLogStatoOptions, getEmailLogStatoSeverity } from '../constants'
import { displayTimestamp, toDateString } from '../../core/utils/date'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
const store = useEmailLogsStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'data_insert',
  defaultSortOrder: -1
})

// Email logs e' read-only (nessun create/update/delete) quindi non serve
// ascoltare eventi cross-tab: nessuno store emette EMAIL_LOGS.

const statoOptions = buildEmailLogStatoOptions(t)

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
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('common.search')" style="width: 250px;" />
        <Select
          :modelValue="store.filters.stato"
          :options="statoOptions"
          optionLabel="label"
          optionValue="value"
          :placeholder="t('amm.email_stato')"
          style="width: 160px;"
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
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
      </div>
    </div>

    <DataTable
      v-bind="paginatorProps"
      :value="store.items"
      :loading="store.loading"
      :totalRecords="store.totalRecords"
      lazy
      removable-sort
      striped-rows
      scrollable
      scrollHeight="flex"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
    >
      <Column field="data_insert" :header="t('amm.email_inviato_at')" sortable style="width: 150px;">
        <template #body="{ data }">{{ displayTimestamp(data.data_insert) }}</template>
      </Column>
      <Column field="destinatario" :header="t('amm.email_destinatario')" sortable style="width: 200px;" />
      <Column field="oggetto" :header="t('amm.email_oggetto')" sortable style="width: 220px;" />
      <Column field="template_codice" :header="t('amm.email_template')" style="width: 150px;" />
      <Column field="account_codice" :header="t('amm.email_account')" style="width: 110px;" />
      <Column field="errore" :header="t('amm.email_errore')">
        <template #body="{ data }">
          <span v-if="data.errore" class="text-red-500" style="font-size: 0.85rem;">{{ data.errore }}</span>
        </template>
      </Column>
      <Column field="stato" :header="t('amm.email_stato')" sortable style="width: 100px;">
        <template #body="{ data }">
          <Tag :value="data.stato" :severity="getEmailLogStatoSeverity(data.stato)" />
        </template>
      </Column>
    </DataTable>
  </div>
</template>
