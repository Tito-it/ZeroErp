<script setup>
// Scopo: Tab «Coda stampa» della vista Strumenti (FE-4): lista paginata
//        dell'outbox PDF (vendite.fatture_stampa_coda). SOLA LETTURA: nessuna
//        azione (P-4 — il drainer ritenta da solo); lo scope è per-emittente
//        (JOIN fatture lato BE), quindi niente is_mio/proprietario-utente.
//        «Tutti» (code_manage) allarga agli altri emittenti.
import { computed, nextTick, onActivated, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import { useNotify } from '../../core/composables/useNotify'
import { usePagedDashFetch } from '../../core/composables/usePagedDashFetch'
import { extractApiError } from '../../core/utils/apiError'
import { displayTimestamp } from '../../core/utils/date'
import { statoCodaStampaSeverity, STATO_CODA_STAMPA_MAP } from '../../core/utils/severity'
import { MANAGE_ICONS, PAGINATION } from '../../core/constants'
import { listCodaStampa } from '../../core/api/tracciamento'
import { useCodaFiltri } from '../composables/useCodaFiltri'
import CodaFiltriToolbar from './CodaFiltriToolbar.vue'

const { t } = useI18n()
const notify = useNotify()

// Filtri condivisi dei tab code — composable estratto alla 2ª copia
// (regola del 2); qui «tutti» allarga agli altri emittenti.
const { filtri, canManage, statoOptions, ambitoOptions, buildParams } =
  useCodaFiltri(STATO_CODA_STAMPA_MAP)

// Scopo: fetch di pagina per il BB paginato (filtri correnti in query).
function fetchPage(paging) {
  return listCodaStampa(buildParams(paging))
}

const {
  items, count, page, pageSize, loading, fetch: fetchStampe, applyPageEvent,
} = usePagedDashFetch(fetchPage, { defaultPageSize: PAGINATION.DEFAULT_ROWS })

async function load() {
  try {
    await fetchStampe()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

function onPage(event) {
  applyPageEvent(event)
  load()
}

function onFilterChange() {
  page.value = 1
  load()
}

// Con <Tabs lazy> ogni attivazione del tab è un MOUNT (v. nota gemella in
// CodaLavoriTab): onMounted popola, onActivated copre il rientro rotta,
// il flag scarta il doppione al mount iniziale della rotta.
let primedByMount = false
onMounted(() => {
  primedByMount = true
  load()
  nextTick(() => { primedByMount = false })
})
onActivated(() => {
  if (primedByMount) return
  load()
})

// Scopo: numero fattura leggibile (anno/serie/numero, campi opzionali).
function fatturaLabel(row) {
  if (row.fattura_numero == null) return `#${row.fattura_id}`
  const serie = row.fattura_serie ? `/${row.fattura_serie}` : ''
  return `${row.fattura_anno ?? ''}${serie} n. ${row.fattura_numero}`
}

// Scopo: messaggio sintetico dall'ultimo_errore jsonb (fail-visible in lista).
function erroreLabel(row) {
  const err = row.ultimo_errore
  if (!err) return null
  return err.message || err.code || t('common.error')
}

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: load,
  },
])
</script>

<template>
  <div class="app-tab-content">
    <CodaFiltriToolbar
      :filtri="filtri"
      :stato-options="statoOptions"
      :ambito-options="ambitoOptions"
      :can-manage="canManage"
      :page-actions="pageActions"
      @change="onFilterChange"
    />

    <DataTable
      :value="items"
      :loading="loading"
      :total-records="count"
      :rows="pageSize"
      :first="(page - 1) * pageSize"
      paginator
      paginator-position="top"
      lazy
      :rows-per-page-options="PAGINATION.ROWS_OPTIONS"
      class="app-datatable app-datatable--inner"
      striped-rows
      data-key="id"
      @page="onPage"
    >
      <Column field="id" header="ID" style="width: 80px;" />
      <Column :header="t('strumenti.code.col_fattura')" style="width: 150px;">
        <template #body="{ data }">
          {{ fatturaLabel(data) }}
        </template>
      </Column>
      <Column field="emittente_codice" :header="t('strumenti.code.col_emittente')" style="width: 120px;">
        <template #body="{ data }">
          {{ data.emittente_codice ?? '—' }}
        </template>
      </Column>
      <Column field="lotto_id" :header="t('strumenti.code.col_lotto')" style="width: 90px;">
        <template #body="{ data }">
          {{ data.lotto_id ?? '—' }}
        </template>
      </Column>
      <Column field="stato" :header="t('strumenti.code.col_stato')" style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.stato" :severity="statoCodaStampaSeverity(data.stato)" />
        </template>
      </Column>
      <Column :header="t('strumenti.code.col_tentativi')" style="width: 90px;">
        <template #body="{ data }">
          {{ data.tentativi }}
        </template>
      </Column>
      <Column :header="t('strumenti.code.col_esito')">
        <template #body="{ data }">
          <span v-if="data.documento_id">
            <i class="pi pi-file-pdf" /> {{ t('strumenti.code.esito_documento', { id: data.documento_id }) }}
          </span>
          <span v-else-if="erroreLabel(data)" class="app-code-errore">
            {{ erroreLabel(data) }}
          </span>
          <span v-else>—</span>
        </template>
      </Column>
      <Column field="data_update" :header="t('strumenti.code.col_aggiornato')" style="width: 150px;">
        <template #body="{ data }">
          {{ data.data_update ? displayTimestamp(data.data_update) : '—' }}
        </template>
      </Column>
      <template #empty>
        <div class="app-empty-state">
          <i class="pi pi-print" />
          <p>{{ t('strumenti.code.nessuna_riga') }}</p>
        </div>
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
.app-code-errore {
  color: var(--p-red-500);
  font-size: 0.85em;
}
</style>
