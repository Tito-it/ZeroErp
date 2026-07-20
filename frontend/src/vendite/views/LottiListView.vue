<script setup>
// Scopo: Registro dei giri di fatturazione (cockpit Fase B, B-2). Lista dei
//        lotti con filtri competenza/stato, scope emittente applicato dal BE
//        (RLS + get_scope_user_id). Non è il percorso quotidiano: serve per le
//        eccezioni (errori, reset, recuperi) e per il gate fiscale. Il click
//        apre il LottoDrawer diagnostico (step corrente, fatture, task-run,
//        segnalazioni) con le azioni di governo. Nessuna logica di dominio:
//        stato/step/gate vivono nel motore, la lista rende e naviga.
import { ref, computed, onActivated } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import LottoDrawer from '../components/LottoDrawer.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { usePagedDashFetch } from '../../core/composables/usePagedDashFetch'
import { extractApiError } from '../../core/utils/apiError'
import { displayDate, displayTimestamp, toDateString } from '../../core/utils/date'
import { MANAGE_ICONS, PAGINATION, READONLY_DOMAINS } from '../../core/constants'
import { statoLottoSeverity } from '../../core/utils/severity'
import { listLotti } from '../api/lotti'

const { t } = useI18n()
const notify = useNotify()
useReadonlyMode(READONLY_DOMAINS.VENDITE)

// Filtri: mese di competenza (DatePicker mese) + stato lotto (select statico
// sui valori di dominio; una nuova voce si mostra comunque via fail-visible).
const competenzaFilter = ref(null)
const statoFilter = ref(null)

const statoOptions = computed(() => [
  { value: 'DRAFT', label: t('vendite.lotti.stato_draft') },
  { value: 'IN_ESECUZIONE', label: t('vendite.lotti.stato_in_esecuzione') },
  { value: 'COMPLETATO', label: t('vendite.lotti.stato_completato') },
  { value: 'ERRORE', label: t('vendite.lotti.stato_errore') },
])

// Scopo: fetch di pagina per il BB paginato (filtri correnti nella query).
function fetchLottiPage(paging) {
  const params = { page: paging.page, page_size: paging.page_size }
  if (competenzaFilter.value) params.competenza_mese = toDateString(competenzaFilter.value)
  if (statoFilter.value) params.stato_lotto = statoFilter.value
  return listLotti(params)
}

// BB standard delle liste paginate dash: guard anti-race, unwrap envelope,
// adozione pagina effettiva BE (niente stato paginazione hand-rolled).
const {
  items, count, page, pageSize, loading, fetch: fetchLotti, applyPageEvent,
} = usePagedDashFetch(fetchLottiPage, { defaultPageSize: PAGINATION.DEFAULT_ROWS })

// Scopo: carica con toast d'errore (il BB propaga l'eccezione: fail-visible).
async function load() {
  try {
    await fetchLotti()
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

// KeepAlive (ContentTabs): onActivated scatta anche al primo mount e a ogni
// rientro nel tab — un solo hook, niente doppio fetch iniziale
// (feedback_keepalive_onactivated).
onActivated(load)

// Drawer diagnostico.
const drawerVisible = ref(false)
const drawerLottoId = ref(null)

function apriLotto(row) {
  drawerLottoId.value = row.id
  drawerVisible.value = true
}

function buildRowActions(row) {
  return [
    {
      key: 'apri',
      label: t('vendite.lotti.azione_apri'),
      icon: 'pi pi-search',
      command: () => apriLotto(row),
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
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h2 style="margin: 0;">{{ t('vendite.lotti.page_title') }}</h2>
        <small class="text-color-secondary">{{ t('vendite.lotti.page_description') }}</small>
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <div class="app-page-filters" style="display: flex; gap: 1rem; align-items: flex-end; margin-bottom: 1rem;">
      <div class="form-field">
        <label>{{ t('vendite.lotti.filtro_competenza') }}</label>
        <DatePicker
          v-model="competenzaFilter"
          view="month"
          date-format="mm/yy"
          show-icon
          show-button-bar
          @update:model-value="onFilterChange"
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.lotti.filtro_stato') }}</label>
        <Select
          v-model="statoFilter"
          :options="statoOptions"
          option-label="label"
          option-value="value"
          show-clear
          :placeholder="t('common.all')"
          @update:model-value="onFilterChange"
        />
      </div>
    </div>

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
      class="app-datatable"
      striped-rows
      data-key="id"
      @page="onPage"
      @row-click="({ data }) => apriLotto(data)"
    >
      <Column field="codice" :header="t('vendite.lotti.col_codice')" style="width: 160px;">
        <template #body="{ data }">
          <strong>{{ data.codice }}</strong>
        </template>
      </Column>
      <Column field="competenza_mese" :header="t('vendite.lotti.col_competenza')" style="width: 110px;">
        <template #body="{ data }">
          {{ data.competenza_mese ? displayDate(data.competenza_mese) : '—' }}
        </template>
      </Column>
      <Column field="tipo_lotto" :header="t('vendite.lotti.col_tipo')" style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.tipo_lotto" severity="secondary" />
        </template>
      </Column>
      <Column field="tipo_doc_fiscale_descrizione" :header="t('vendite.lotti.col_tipo_doc')">
        <template #body="{ data }">
          {{ data.tipo_doc_fiscale_descrizione ?? '—' }}
        </template>
      </Column>
      <Column field="utility_descrizione" :header="t('vendite.lotti.col_utility')">
        <template #body="{ data }">
          {{ data.utility_descrizione ?? '—' }}
        </template>
      </Column>
      <Column field="stato_lotto" :header="t('vendite.lotti.col_stato')" style="width: 130px;">
        <template #body="{ data }">
          <Tag :value="data.stato_lotto" :severity="statoLottoSeverity(data.stato_lotto)" />
        </template>
      </Column>
      <Column field="stato_doc_fiscale_descrizione" :header="t('vendite.lotti.col_stato_doc')" style="width: 150px;">
        <template #body="{ data }">
          <Tag
            v-if="data.stato_doc_fiscale_descrizione"
            :value="data.stato_doc_fiscale_descrizione"
            severity="info"
          />
          <span v-else>—</span>
        </template>
      </Column>
      <Column field="data_insert" :header="t('vendite.lotti.col_creato')" style="width: 150px;">
        <template #body="{ data }">
          {{ data.data_insert ? displayTimestamp(data.data_insert) : '—' }}
        </template>
      </Column>
      <Column :header="t('vendite.lotti.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
      <template #empty>
        <div class="app-empty-state">
          <i class="pi pi-server" />
          <p>{{ t('vendite.lotti.nessun_lotto') }}</p>
        </div>
      </template>
    </DataTable>

    <LottoDrawer
      v-model:visible="drawerVisible"
      :lotto-id="drawerLottoId"
      @changed="load"
    />
  </div>
</template>
