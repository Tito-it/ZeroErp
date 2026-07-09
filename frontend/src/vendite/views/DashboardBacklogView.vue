<script setup>
// Scopo: Lente 2 Backlog — cosa e' fermo a monte della commessa, da quanto e
//        cosa serve per sbloccarlo (brief-design-fatturazione-due-lenti §5,
//        Fase 2 FE). Asse = anzianita' + azionabilita', NON la competenza:
//        niente calendario mesi. Dati reali da GET /vendite/dashboard-backlog/
//        (+ /documenti/) via store Pinia; classi, motivi e ordinamento vivono
//        nel DB/BE (vw_dash_backlog_* + config.motivi_fermo): la view rende.
//        Layout: contatori per classe (card cliccabili = filtro) + filtro
//        area + lista per anzianita' con motivo/azione/stato.
import { computed, onActivated } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import DashEmptyState from '../../core/components/DashEmptyState.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { MANAGE_ICONS, PAGINATION, READONLY_DOMAINS } from '../../core/constants'
import { extractApiError } from '../../core/utils/apiError'
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { classeBacklogSeverity } from '../../core/utils/severity'
import {
  buildApriDocumentoAction,
  DASH_AREE,
  dashAreaLabel,
  dashAreaSeverity,
  dashMotivoLabel,
} from '../dashboardAree'
import { useDashboardBacklogStore } from '../stores/dashboardBacklog'

const { t, te } = useI18n()
const notify = useNotify()
const router = useRouter()

// Provider readonly di area: la lente e' consultazione pura, ma il provider
// mantiene il pattern standard (ReadonlyBadge nel suffix toolbar).
useReadonlyMode(READONLY_DOMAINS.VENDITE)

const store = useDashboardBacklogStore()
const {
  classeSelezionata,
  areaSelezionata,
  orderBy,
  orderDir,
  classi,
  documenti,
  documentiCount,
  documentiPage,
  documentiPageSize,
  documentiLoading,
  documentiLoaded,
} = storeToRefs(store)

// Ordinamento colonne per il DataTable (controllato): campo dallo store,
// direzione nella convenzione PrimeVue (1 asc, -1 desc).
const documentiSortOrder = computed(() => (orderDir.value === 'desc' ? -1 : 1))

// Scopo: decodifiche i18n con fallback al codice grezzo (fail-visible per
//        classi/motivi/aree future introdotte DB-side). Motivi e aree dai BB
//        condivisi di dashboardAree (gruppo dash_comune, riusato dalla
//        Situazione aperta); la classe e' vocabolario solo-Backlog.
function classeLabel(classe) {
  return labelOrCode(t, te, `dashboard_backlog.classe_${String(classe).toLowerCase()}`, classe)
}

const motivoLabel = (motivo) => dashMotivoLabel(t, te, motivo)
const areaLabel = (area) => dashAreaLabel(t, te, area)

// Card contatori: iterazione diretta di classi dal BE (3 sempre presenti,
// eventuali classi future accodate fail-visible).
const cards = computed(() =>
  classi.value.map((c) => ({
    classe: c.classe,
    nDocumenti: c.n_documenti ?? 0,
    valoreFermo: Number(c.valore_fermo_tot ?? 0),
    unitaFerme: c.unita_ferme_tot ?? 0,
    // NULL = eta' sconosciuta (nessuna data documento): niente badge.
    anzianitaMax: c.anzianita_max_giorni ?? 0,
  }))
)

// Opzioni filtro area (tutte + 5 aree funnel dal BB condiviso, label
// condivise con la 5-card).
const areaOptions = computed(() => [
  { value: null, label: t('dashboard_backlog.filtro_area_tutte') },
  ...DASH_AREE.map((area) => ({ value: area, label: areaLabel(area) })),
])

// Scopo: carica i contatori per classe con gestione errori standard.
async function loadRiepilogo() {
  try {
    await store.fetchRiepilogo()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Scopo: carica la pagina corrente della lista coi filtri correnti.
async function loadDocumenti() {
  try {
    await store.fetchDocumenti()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Scopo: click su card classe = toggle del filtro classe (riparte da pag. 1).
function selezionaClasse(classe) {
  classeSelezionata.value = classeSelezionata.value === classe ? null : classe
  store.resetDocumenti()
  loadDocumenti()
}

// Scopo: cambio filtro area (riparte da pagina 1).
function onAreaChange() {
  store.resetDocumenti()
  loadDocumenti()
}

// Scopo: paginazione DataTable documenti (lazy, paginator top; calcolo
//        pagina nel BB usePagedDashFetch).
function onDocumentiPage(event) {
  store.applyDocumentiPage(event)
  loadDocumenti()
}

// Scopo: ordinamento colonne (server-side, lista lazy): aggiorna lo stato sort
//        e ricarica dalla PAGINA 1 (come i cambi filtro). Corretto su tutte le
//        pagine, non solo su quella visibile.
function onDocumentiSort(event) {
  store.applyDocumentiSort(event)
  store.resetDocumenti()
  loadDocumenti()
}

// Severity Tag per lo stato documento: dispatch al BB condiviso sull'area
// della riga (la lista e' cross-area).
function statoSeverity(row) {
  return dashAreaSeverity(row.area, row.stato_codice_interno)
}

// Azioni riga: "apri documento" via BB condiviso (naviga alla lista area
// con ?search=; il deep-link azzera i default data della lista target).
function buildRowActions(data) {
  return [
    buildApriDocumentoAction({
      area: data.area,
      codice: data.codice,
      label: t('dashboard_backlog.apri_documento'),
      router,
    }),
  ]
}

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: () => {
      loadRiepilogo()
      loadDocumenti()
    },
  },
])

// KeepAlive (ContentTabs): onActivated scatta anche al primo mount e a ogni
// rientro in foreground — refresh idempotente di contatori E lista
// (memoria feedback_keepalive_onactivated).
onActivated(() => {
  loadRiepilogo()
  loadDocumenti()
})
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h2 style="margin: 0;">{{ t('dashboard_backlog.page_title') }}</h2>
        <small class="text-color-secondary">{{ t('dashboard_backlog.page_description') }}</small>
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <div class="app-dash-main">
      <!-- Contatori per classe di azionabilita' (card = filtro toggle). -->
      <div class="app-dash-cards">
        <div
          v-for="card in cards"
          :key="card.classe"
          class="app-dash-card"
          :class="{ 'is-selected': classeSelezionata === card.classe }"
          role="button"
          tabindex="0"
          @click="selezionaClasse(card.classe)"
          @keydown.enter="selezionaClasse(card.classe)"
        >
          <Tag
            :value="classeLabel(card.classe)"
            :severity="classeBacklogSeverity(card.classe)"
          />
          <span class="app-dash-stat-n">{{ card.nDocumenti }}</span>
          <span class="app-dash-stat-sub">{{ t('dashboard_backlog.n_documenti') }}</span>
          <span v-if="card.valoreFermo > 0" class="app-dash-stat-euro">
            {{ formatCurrency(card.valoreFermo) }}
          </span>
          <!-- Aree a conteggi (offerte/contratti): unita' al posto del valore. -->
          <span v-if="card.unitaFerme > 0" class="app-dash-stat-sub">
            {{ t('dashboard_backlog.unita_ferme', { n: card.unitaFerme }) }}
          </span>
          <span v-if="card.anzianitaMax > 0" class="app-dash-ritardo">
            <i class="pi pi-clock" />
            {{ t('dashboard_backlog.anzianita_max', { n: card.anzianitaMax }) }}
          </span>
        </div>
      </div>

      <!-- Lista per anzianita' con filtro area. Niente data-key: la union e'
           cross-area e documento_uid si ripete per i contratti mese-esplosi
           (nessuna chiave riga univoca disponibile). -->
      <div class="app-dash-fermi">
        <div class="app-page-toolbar">
          <h4 class="app-dash-fermi-title">
            {{ t('dashboard_backlog.lista_titolo') }}
          </h4>
          <Select
            v-model="areaSelezionata"
            :options="areaOptions"
            option-label="label"
            option-value="value"
            :placeholder="t('dashboard_backlog.filtro_area_tutte')"
            size="small"
            style="width: 200px;"
            @change="onAreaChange"
          />
        </div>
        <DataTable
          v-if="documentiCount > 0 || documentiLoading"
          :value="documenti"
          :loading="documentiLoading"
          :total-records="documentiCount"
          :rows="documentiPageSize"
          :first="(documentiPage - 1) * documentiPageSize"
          paginator
          paginator-position="top"
          lazy
          :rows-per-page-options="PAGINATION.ROWS_OPTIONS"
          :sort-field="orderBy"
          :sort-order="documentiSortOrder"
          class="app-datatable app-datatable--inner"
          striped-rows
          @page="onDocumentiPage"
          @sort="onDocumentiSort"
        >
          <Column field="anzianita_giorni" :header="t('dashboard_backlog.col_fermo_da')" sortable style="width: 110px;">
            <template #body="{ data }">
              <span
                class="app-dash-ritardo"
                v-tooltip.bottom="data.data_riferimento ? displayDate(data.data_riferimento) : ''"
              >
                {{ data.anzianita_giorni !== null
                  ? t('dashboard_backlog.fermo_da_giorni', { n: data.anzianita_giorni })
                  : '—' }}
              </span>
            </template>
          </Column>
          <Column field="classe" :header="t('dashboard_backlog.col_classe')" style="width: 140px;">
            <template #body="{ data }">
              <Tag :value="classeLabel(data.classe)" :severity="classeBacklogSeverity(data.classe)" />
            </template>
          </Column>
          <Column field="area" :header="t('dashboard_backlog.col_area')" sortable style="width: 110px;">
            <template #body="{ data }">
              {{ areaLabel(data.area) }}
            </template>
          </Column>
          <Column field="codice" :header="t('dashboard_backlog.col_codice')" sortable style="width: 130px;">
            <template #body="{ data }">
              {{ data.codice ?? '—' }}
            </template>
          </Column>
          <Column field="cliente_display" :header="t('dashboard_backlog.col_cliente')" sortable>
            <template #body="{ data }">
              {{ data.cliente_display ?? '—' }}
            </template>
          </Column>
          <Column field="valore_fermo" :header="t('dashboard_backlog.col_valore')" sortable style="width: 120px;">
            <template #body="{ data }">
              {{ data.valore_fermo !== null ? formatCurrency(data.valore_fermo) : '—' }}
            </template>
          </Column>
          <Column field="unita_ferme" :header="t('dashboard_backlog.col_unita')" style="width: 90px;">
            <template #body="{ data }">
              {{ data.unita_ferme ?? '—' }}
            </template>
          </Column>
          <Column field="motivo_fermo" :header="t('dashboard_backlog.col_motivo')">
            <template #body="{ data }">
              {{ motivoLabel(data.motivo_fermo) }}
            </template>
          </Column>
          <Column field="azione" :header="t('dashboard_backlog.col_azione')">
            <template #body="{ data }">
              {{ data.azione ?? '—' }}
            </template>
          </Column>
          <Column field="stato_codice" :header="t('dashboard_backlog.col_stato')" sortable style="width: 120px;">
            <template #body="{ data }">
              <Tag :value="data.stato_codice ?? '—'" :severity="statoSeverity(data)" />
            </template>
          </Column>
          <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
            <template #body="{ data }">
              <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
            </template>
          </Column>
        </DataTable>
        <DashEmptyState
          v-else
          :loaded="documentiLoaded"
          :empty-text="t('dashboard_backlog.nessun_documento')"
          :placeholder-text="t('dashboard_backlog.non_caricato')"
        />
      </div>
    </div>
  </div>
</template>
