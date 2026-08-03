<script setup>
// Scopo: Tab «Coda lavori» della vista Strumenti (FE-4/FE-5): lista paginata
//        dei job di dbops.coda_lavori. Righe proprie = azionabili (annulla su
//        PENDING, requeue su IN_CORSO/ERRORE); righe altrui = sola lettura con
//        colonna proprietario. La vista «Tutti» è aperta a ogni operatore
//        (2026-07-23, decisione Tid): la coda è condivisa e chi aspetta deve
//        vedere il lavoro altrui che la impegna; azioni e DETTAGLIO restano
//        gated (proprie o code_manage). `is_mio` arriva dal BE (P-5: il FE non
//        confronta identità). Gate stato sui CODICI stabili (I-2), enforcement
//        vero nel BE (I-3: qui si nasconde, là si blinda).
//
//        Convertita a <ListaConfigurabile> (config DB `dbops.coda_lavori`,
//        ui.lista_definizione id 34 — 7° lotto, 2026-08-03): personalizzazione
//        colonne + ordinamento server-side (whitelist BE ELENCA_SORT_SQL,
//        estesa a `stato`/`proprietario` il 2026-08-02) + preset
//        `started_at desc` che replica il default BE. Stato lista nello store
//        Pinia `useCodaLavoriStore` (stores/codeJobs.js).
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useNotify } from '../../core/composables/useNotify'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { extractApiError } from '../../core/utils/apiError'
import { statoCodaLavoriSeverity, STATO_CODA_LAVORI_MAP } from '../../core/utils/severity'
import { annullaCodaLavoro, requeueCodaLavoro } from '../../core/api/tracciamento'
import { useCodaFiltri } from '../composables/useCodaFiltri'
import { useCodaLavoriStore } from '../stores/codeJobs'
import CodaFiltriToolbar from './CodaFiltriToolbar.vue'
import CodaWorkerStato from './CodaWorkerStato.vue'
import JobDettaglioDrawer from './JobDettaglioDrawer.vue'

const { t } = useI18n()
const notify = useNotify()
const { execute, loading: azioneLoading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()

const store = useCodaLavoriStore()

// Helper UI condivisi dei tab code (opzioni + gate azioni code_manage).
const { canManage, statoOptions, ambitoOptions } = useCodaFiltri(STATO_CODA_LAVORI_MAP)

// Stato worker: ricaricato insieme alla lista, così «Ricarica» aggiorna anche
// l'ultimo giro (altrimenti resterebbe fermo al primo ingresso nel tab).
const workerStatoRef = ref(null)

// Scopo: fetch con refresh worker e cattura errore (fail-visible: una tabella
//        vuota per errore non deve sembrare "coda vuota").
async function load() {
  workerStatoRef.value?.refresh()
  try {
    await store.fetchList()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

const {
  onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, { onReload: load })

// Cambio filtro toolbar: si riparte da pagina 1.
function onFilterChange() {
  store.filters.offset = 0
  load()
}

// Primo caricamento al mount: con <Tabs lazy> ogni attivazione del tab è un
// MOUNT (pattern ResiCodaTable); la freshness al rientro rotta la gestisce
// l'onActivated di useSearchTable dentro lo scaffolding.
onMounted(load)

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

// Scopo: azioni riga — annulla/requeue solo su righe azionabili (mie o
//        code_manage) fuori readonly, gate sui codici stato. Anche il
//        DETTAGLIO è gated (mie o code_manage): la lista «Tutti» è visibilità
//        della coda condivisa, ma payload/errori del job altrui possono
//        contenere dati della sua attività — il BE risponde comunque 404
//        fuori scope, qui si evita di offrire un'azione destinata a fallire.
function buildRowActions(row) {
  const azionabile = (row.is_mio === true || canManage.value) && !isReadonly.value
  return [
    {
      key: 'dettaglio',
      label: t('strumenti.code.azione_dettaglio'),
      icon: 'pi pi-search',
      visible: row.is_mio === true || canManage.value,
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

// Click riga = dettaglio, stesso gate delle azioni.
function onRowClick(data) {
  if (data.is_mio === true || canManage.value) apriDettaglio(data)
}
</script>

<template>
  <div class="app-tab-content">
    <CodaFiltriToolbar
      :filtri="store.filters"
      :stato-options="statoOptions"
      :ambito-options="ambitoOptions"
      :page-actions="pageActions"
      @change="onFilterChange"
    >
      <template #actions-suffix>
        <ListaConfigStatusTag :dirty="dirty" />
      </template>
    </CodaFiltriToolbar>

    <!-- Liveness del drainer: dice se la coda sta girando o è ferma. Il
         conteggio delle sue esecuzioni è volutamente assente (un poller a
         1/min produce numeri enormi che non informano su nulla). -->
    <CodaWorkerStato ref="workerStatoRef" coda="coda_lavori" />

    <ListaConfigurabile
      ref="listaRef"
      codice="dbops.coda_lavori"
      data-key="id"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading || azioneLoading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      @config-loaded="onConfigLoaded"
    >
      <template #cell-job_type="{ data }">
        <span class="app-code-tipo">{{ data.job_type }}</span>
      </template>
      <template #cell-stato="{ data }">
        <Tag :value="data.stato" :severity="statoCodaLavoriSeverity(data.stato)" />
      </template>
      <template #cell-proprietario="{ data }">
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
      <!-- Colonna calcolata FE (seed: campo_sorgente vuoto, ordinabile=f). -->
      <template #cell-tentativi="{ data }">
        {{ data.tentativi }}/{{ data.max_tentativi }}
      </template>
      <!-- started_at/ended_at non hanno slot: il seed dichiara
           `datetime_short` e il formatter di serie le rende gia' cosi'. -->

      <template #actions="{ data, compact }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" :force-compact="compact" />
      </template>

      <template #empty>
        <div class="app-empty-state">
          <i class="pi pi-inbox" />
          <p>{{ t('strumenti.code.nessuna_riga') }}</p>
        </div>
      </template>
    </ListaConfigurabile>

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
