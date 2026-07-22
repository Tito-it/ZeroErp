<script setup>
// Scopo: Tab «Coda lavori» della vista Strumenti (FE-4/FE-5): lista paginata
//        dei job di dbops.coda_lavori. Righe proprie = azionabili (annulla su
//        PENDING, requeue su IN_CORSO/ERRORE); righe altrui = sola lettura con
//        colonna proprietario (visibili solo con «Tutti», permesso
//        code_manage). `is_mio` arriva dal BE (P-5: il FE non confronta
//        identità). Gate stato sui CODICI stabili (I-2), enforcement vero nel
//        BE (I-3: qui si nasconde, là si blinda).
import { ref, computed, nextTick, onActivated, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useNotify } from '../../core/composables/useNotify'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { usePagedDashFetch } from '../../core/composables/usePagedDashFetch'
import { extractApiError } from '../../core/utils/apiError'
import { displayTimestamp } from '../../core/utils/date'
import { statoCodaLavoriSeverity, STATO_CODA_LAVORI_MAP } from '../../core/utils/severity'
import { MANAGE_ICONS, PAGINATION } from '../../core/constants'
import { annullaCodaLavoro, listCodaLavori, requeueCodaLavoro } from '../../core/api/tracciamento'
import { useCodaFiltri } from '../composables/useCodaFiltri'
import CodaFiltriToolbar from './CodaFiltriToolbar.vue'
import JobDettaglioDrawer from './JobDettaglioDrawer.vue'

const { t } = useI18n()
const notify = useNotify()
const { execute, loading: azioneLoading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()

// Filtri condivisi dei tab code (ambito gate code_manage, stato, date con
// default anno-1) — composable estratto alla 2ª copia (regola del 2).
const { filtri, canManage, statoOptions, ambitoOptions, buildParams } =
  useCodaFiltri(STATO_CODA_LAVORI_MAP)

// Scopo: fetch di pagina per il BB paginato (filtri correnti in query).
function fetchPage(paging) {
  return listCodaLavori(buildParams(paging))
}

const {
  items, count, page, pageSize, loading, fetch: fetchJobs, applyPageEvent,
} = usePagedDashFetch(fetchPage, { defaultPageSize: PAGINATION.DEFAULT_ROWS })

async function load() {
  try {
    await fetchJobs()
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

// Con <Tabs lazy> ogni attivazione del tab è un MOUNT (il TabPanel rende il
// contenuto con v-if su active): il primo popolamento vive in onMounted —
// il solo onActivated lascerebbe il tab vuoto al cambio tab (l'hook
// `activated` di un discendente montato DOPO l'attivazione della rotta
// scatta solo alla prossima riattivazione KeepAlive). onActivated resta per
// il rientro rotta; al mount iniziale della rotta scatterebbero entrambi →
// il flag scarta il doppione (mounted e activated girano nello stesso flush,
// PRIMA della nextTick).
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

// Drawer dettaglio (FE-6).
const dettaglioVisible = ref(false)
const dettaglioJobId = ref(null)

function apriDettaglio(row) {
  dettaglioJobId.value = row.id
  dettaglioVisible.value = true
}

// Scopo: annulla un job PENDING proprio (conferma esplicita, poi reload).
function annullaJob(row) {
  confirmAction({
    title: t('strumenti.code.annulla_header'),
    message: t('strumenti.code.annulla_conferma', { id: row.id, tipo: row.job_type }),
    danger: true,
    onAccept: async () => {
      const res = await execute(() => annullaCodaLavoro(row.id))
      if (res !== null) {
        notify.success(t('strumenti.code.annulla_esito'))
        load()
      }
    },
  })
}

// Scopo: requeue/sblocco di un job IN_CORSO o ERRORE (alza max_tentativi).
function requeueJob(row) {
  confirmAction({
    title: t('strumenti.code.requeue_header'),
    message: t('strumenti.code.requeue_conferma', { id: row.id, tipo: row.job_type }),
    onAccept: async () => {
      const res = await execute(() => requeueCodaLavoro(row.id))
      if (res !== null) {
        notify.success(t('strumenti.code.requeue_esito'))
        load()
      }
    },
  })
}

// Scopo: azioni riga — dettaglio sempre; annulla/requeue solo su righe
//        azionabili (mie o code_manage) fuori readonly, gate sui codici stato.
function buildRowActions(row) {
  const azionabile = (row.is_mio === true || canManage.value) && !isReadonly.value
  return [
    {
      key: 'dettaglio',
      label: t('strumenti.code.azione_dettaglio'),
      icon: 'pi pi-search',
      command: () => apriDettaglio(row),
    },
    {
      key: 'annulla',
      label: t('strumenti.code.azione_annulla'),
      icon: 'pi pi-ban',
      severity: 'danger',
      visible: azionabile && row.stato === 'PENDING',
      command: () => annullaJob(row),
    },
    {
      key: 'requeue',
      label: t('strumenti.code.azione_requeue'),
      icon: 'pi pi-replay',
      severity: 'warn',
      visible: azionabile && (row.stato === 'IN_CORSO' || row.stato === 'ERRORE'),
      command: () => requeueJob(row),
    },
  ]
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
      :loading="loading || azioneLoading"
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
      @row-click="({ data }) => apriDettaglio(data)"
    >
      <Column field="id" header="ID" style="width: 80px;" />
      <Column field="job_type" :header="t('strumenti.code.col_tipo')">
        <template #body="{ data }">
          <span class="app-code-tipo">{{ data.job_type }}</span>
        </template>
      </Column>
      <Column field="stato" :header="t('strumenti.code.col_stato')" style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.stato" :severity="statoCodaLavoriSeverity(data.stato)" />
        </template>
      </Column>
      <Column
        v-if="filtri.ambito === 'tutti'"
        field="proprietario"
        :header="t('strumenti.code.col_proprietario')"
        style="width: 140px;"
      >
        <template #body="{ data }">
          <span>
            {{ data.proprietario ?? '—' }}
            <Tag
              v-if="data.is_mio"
              :value="t('strumenti.code.mio_tag')"
              severity="info"
              class="app-code-mio-tag"
            />
          </span>
        </template>
      </Column>
      <Column :header="t('strumenti.code.col_tentativi')" style="width: 100px;">
        <template #body="{ data }">
          {{ data.tentativi }}/{{ data.max_tentativi }}
        </template>
      </Column>
      <Column field="started_at" :header="t('strumenti.code.col_avviato')" style="width: 150px;">
        <template #body="{ data }">
          {{ data.started_at ? displayTimestamp(data.started_at) : '—' }}
        </template>
      </Column>
      <Column field="ended_at" :header="t('strumenti.code.col_concluso')" style="width: 150px;">
        <template #body="{ data }">
          {{ data.ended_at ? displayTimestamp(data.ended_at) : '—' }}
        </template>
      </Column>
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
      <template #empty>
        <div class="app-empty-state">
          <i class="pi pi-inbox" />
          <p>{{ t('strumenti.code.nessuna_riga') }}</p>
        </div>
      </template>
    </DataTable>

    <JobDettaglioDrawer
      v-model:visible="dettaglioVisible"
      :job-id="dettaglioJobId"
      @changed="load"
    />
  </div>
</template>

<style scoped>
.app-code-tipo {
  font-family: monospace;
  font-size: 0.85em;
}
.app-code-mio-tag {
  margin-left: 0.35rem;
  font-size: 0.65rem;
}
</style>
