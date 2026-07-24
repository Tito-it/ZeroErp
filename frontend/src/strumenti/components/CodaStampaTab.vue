<script setup>
// Scopo: Tab «Coda stampa» della vista Strumenti (FE-4): lista paginata
//        dell'outbox PDF (vendite.fatture_stampa_coda). SOLA LETTURA: nessuna
//        azione (P-4 — il drainer ritenta da solo). Ambito PER-OPERATORE come
//        la coda lavori (2026-07-23, decisione Tid): «Solo i miei» = righe
//        innescate da me (audit user_insert via GUC identità), «Tutti» = di
//        tutti gli operatori. La colonna «Operatore» + tag «mio» rendono
//        leggibile chi ha lanciato; l'emittente resta colonna informativa.
import { computed, ref } from 'vue'
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
import { useLazyTabLoad } from '../../core/composables/useLazyTabLoad'
import { useCodaFiltri } from '../composables/useCodaFiltri'
import CodaFiltriToolbar from './CodaFiltriToolbar.vue'
import CodaWorkerStato from './CodaWorkerStato.vue'

const { t } = useI18n()
const notify = useNotify()

// Filtri condivisi dei tab code — composable estratto alla 2ª copia
// (regola del 2); qui «tutti» allarga agli altri emittenti.
// La coda stampa non ha azioni per-riga né dettaglio: `canManage` non serve
// (le righe sono per-emittente, non per-operatore). Ordinamento default
// «aggiornato» discendente (2026-07-23, richiesta Tid): la riga lavorata più
// di recente in testa.
const {
  filtri, ordinamento, applySortEvent,
  statoOptions, ambitoOptions, buildParams,
} = useCodaFiltri(STATO_CODA_STAMPA_MAP, {
  sortDefault: { field: 'data_update', order: -1 },
})

// Scopo: fetch di pagina per il BB paginato (filtri correnti in query).
function fetchPage(paging) {
  return listCodaStampa(buildParams(paging))
}

const {
  items, count, page, pageSize, loading, fetch: fetchStampe, applyPageEvent,
} = usePagedDashFetch(fetchPage, { defaultPageSize: PAGINATION.DEFAULT_ROWS })

// Stato worker: ricaricato insieme alla lista, così «Ricarica» aggiorna anche
// l'ultimo giro (altrimenti resterebbe fermo al primo ingresso nel tab).
const workerStatoRef = ref(null)

async function load() {
  workerStatoRef.value?.refresh()
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

// Scopo: sort lazy della DataTable — aggiorna lo stato e ricarica da pagina 1
//        (l'ordinamento è server-side: la pagina corrente non ha più senso).
function onSort(event) {
  applySortEvent(event)
  onFilterChange()
}

// Primo popolamento + freshness al rientro, senza doppio fetch iniziale
// (BB estratto alla 3ª copia — la spiegazione del pattern vive lì).
useLazyTabLoad(load)

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
      :page-actions="pageActions"
      @change="onFilterChange"
    />

    <!-- Liveness del drainer: dice se la coda sta girando o è ferma. Il
         conteggio delle sue esecuzioni è volutamente assente (un poller a
         1/2min produce numeri enormi che non informano su nulla). -->
    <CodaWorkerStato ref="workerStatoRef" coda="coda_stampa" />

    <DataTable
      :value="items"
      :loading="loading"
      :total-records="count"
      :rows="pageSize"
      :first="(page - 1) * pageSize"
      paginator
      paginator-position="top"
      lazy
      :sort-field="ordinamento.field"
      :sort-order="ordinamento.order"
      @sort="onSort"
      scrollable
      scroll-height="flex"
      :rows-per-page-options="PAGINATION.ROWS_OPTIONS"
      class="app-datatable app-datatable--inner"
      striped-rows
      data-key="id"
      @page="onPage"
    >
      <Column field="id" header="ID" style="width: 80px;" />
      <!-- `field` serve al sort lazy (chiave whitelistata dal BE): l'ordine è
           per id fattura, la label resta anno/serie/numero componibile. -->
      <Column field="fattura_id" :header="t('strumenti.code.col_fattura')" sortable style="width: 150px;">
        <template #body="{ data }">
          {{ fatturaLabel(data) }}
        </template>
      </Column>
      <Column field="emittente_codice" :header="t('strumenti.code.col_emittente')" style="width: 120px;">
        <template #body="{ data }">
          {{ data.emittente_codice ?? '—' }}
        </template>
      </Column>
      <!-- Operatore che ha innescato il processo (audit user_insert via GUC
           identità), con tag «mio» come la colonna proprietario della coda
           lavori. Sempre visibile: anche in «Solo i miei» dice chi sei. -->
      <Column field="operatore" :header="t('strumenti.code.col_operatore')" style="width: 130px;">
        <template #body="{ data }">
          <span>
            {{ data.operatore ?? '—' }}
            <Tag
              v-if="data.is_mio"
              :value="t('strumenti.code.mio_tag')"
              severity="info"
              class="app-code-mio-tag"
            />
          </span>
        </template>
      </Column>
      <Column field="lotto_id" :header="t('strumenti.code.col_lotto')" sortable style="width: 90px;">
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
      <Column field="data_update" :header="t('strumenti.code.col_aggiornato')" sortable style="width: 150px;">
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
