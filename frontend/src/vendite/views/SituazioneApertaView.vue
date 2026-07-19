<script setup>
// Scopo: Situazione aperta v2 — serbatoio pre-commessa: i documenti aperti-non-
//        chiusi che, se conclusi, andrebbero in commessa/fatturazione ma non ci
//        sono ancora arrivati (brief-design-fatturazione-due-lenti §6-ter,
//        DL-14..18). Terza vista dei cruscotti: la Lente 1 guarda il mese di
//        competenza, la Lente 2 il lavoro da sbloccare ora, qui si fotografa
//        DOVE sono tutti gli aperti, per fase (maturità verso la commessa).
//        Dati reali da GET /vendite/dashboard-aperto/ (+ /documenti/) via store
//        Pinia; perimetro, aree, fasi e ordinamento vivono nel DB/BE
//        (vw_dash_aperto_* v2 + config.stati_doc_*): la view rende.
//        Layout: card per area (click = filtro) con donut per fase + lista dei
//        documenti ordinata per "in essere da", con filtro "aperti da oltre N
//        giorni" (solo lista: le card restano la fotografia completa, DL-17).
import { computed, onActivated } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import DashEmptyState from '../../core/components/DashEmptyState.vue'
import DonutFasi from '../../core/components/charts/DonutFasi.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { MANAGE_ICONS, PAGINATION, READONLY_DOMAINS } from '../../core/constants'
import { extractApiError } from '../../core/utils/apiError'
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { faseDocumentoSeverity } from '../../core/utils/severity'
import {
  DASH_AREA_CONFIG,
  buildApriDocumentoAction,
  dashAreaLabel,
  dashAreaSeverity,
  dashFaseLabel,
  dashMotivoLabel,
} from '../dashboardAree'
import { useDashboardApertoStore } from '../stores/dashboardAperto'

const { t, te } = useI18n()
const notify = useNotify()
const router = useRouter()

// Provider readonly di area: la vista e' consultazione pura, ma il provider
// mantiene il pattern standard (ReadonlyBadge nel suffix toolbar).
useReadonlyMode(READONLY_DOMAINS.VENDITE)

const store = useDashboardApertoStore()
const {
  areaSelezionata,
  faseSelezionata,
  ritardoGiorni,
  orderBy,
  orderDir,
  aree,
  fasi,
  documenti,
  documentiCount,
  documentiPage,
  documentiPageSize,
  documentiLoading,
  documentiLoaded,
} = storeToRefs(store)

// Ordinamento colonne per il DataTable (controllato): il campo dallo store,
// la direzione tradotta nella convenzione PrimeVue (1 asc, -1 desc).
const documentiSortOrder = computed(() => (orderDir.value === 'desc' ? -1 : 1))

// Scopo: decodifiche i18n fail-visible dai BB condivisi di dashboardAree
//        (gruppo dash_comune, riusato dal Backlog): alias locali per tenere
//        il template invariato.
const areaLabel = (area) => dashAreaLabel(t, te, area)
const faseLabel = (fase) => dashFaseLabel(t, te, fase)
const motivoLabel = (motivo) => dashMotivoLabel(t, te, motivo)

// Card per area: donut a spicchi per FASE (DL-16), un segmento per ogni fase
// con documenti. La misura la decide il BE (DL-11): valore_totale stringa per
// le aree euro, null per le aree a conteggi (il FE legge il payload, non tiene
// una seconda copia della whitelist euro). Il perimetro aperti-non-chiusi è
// già nella vista v2: qui nessun filtro CHIUSO da rifare.
const cards = computed(() =>
  aree.value.map((a) => {
    const isEuro = a.valore_totale !== null
    const segmenti = (a.fasi ?? [])
      .map((f) => ({
        fase: f.fase,
        label: faseLabel(f.fase),
        value: isEuro ? Number(f.valore_totale ?? 0) : (f.n_documenti ?? 0),
      }))
      .filter((s) => s.value > 0)
    return {
      area: a.area,
      format: isEuro ? 'currency' : 'count',
      fasi: segmenti,
      // Hint per misure non ovvie (es. ORDINI misura mista, DL-23): la
      // mappatura area→hint vive in DASH_AREA_CONFIG con route/severity,
      // non qui — la view non conosce le aree per nome.
      hint: DASH_AREA_CONFIG[a.area]?.apertoHintKey
        ? t(DASH_AREA_CONFIG[a.area].apertoHintKey)
        : null,
    }
  })
)

// Opzioni filtro fase: dal vocabolario top-level servito dal riepilogo BE
// (3 fasi vive sempre presenti + eventuali future accodate fail-visible) —
// nessuna copia FE del vocabolario config.stati_doc_*.
const faseOptions = computed(() => [
  { value: null, label: t('situazione_aperta.filtro_fase_tutte') },
  ...fasi.value.map((f) => ({ value: f, label: faseLabel(f) })),
])

// Opzioni filtro "aperti da oltre N giorni" (DL-17): soglia su data documento,
// solo sulla lista. null = nessuna soglia (drill-down completo).
const ritardoOptions = computed(() => [
  { value: null, label: t('situazione_aperta.ritardo_tutti') },
  { value: 30, label: t('situazione_aperta.ritardo_30') },
  { value: 60, label: t('situazione_aperta.ritardo_60') },
  { value: 90, label: t('situazione_aperta.ritardo_90') },
])

// Scopo: carica il riepilogo area × fase con gestione errori standard.
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

// Scopo: handler unico di cambio filtri lista (fase, ritardo giorni, area):
//        riparte da pagina 1 e ricarica SOLO la lista — le card restano la
//        fotografia completa (DL-17: il riepilogo non è mai filtrato).
function onFiltriChange() {
  store.resetDocumenti()
  loadDocumenti()
}

// Scopo: click sul corpo della card = livello AREA (nessuna fase). Se su
//        quest'area c'e' gia' una fase attiva (drill-down da legenda), il click
//        la rimuove tornando a "tutta l'area"; altrimenti toggle classico
//        dell'area. In ogni caso la fase viene azzerata (vista d'area).
function selezionaArea(area) {
  if (areaSelezionata.value === area && faseSelezionata.value !== null) {
    faseSelezionata.value = null
  } else {
    areaSelezionata.value = areaSelezionata.value === area ? null : area
    faseSelezionata.value = null
  }
  onFiltriChange()
}

// Scopo: click su una voce di legenda del donut (una fase specifica): filtra la
//        lista per AREA + FASE e valorizza i filtri (la card si evidenzia,
//        il Select fase mostra la fase). Set esplicito, non toggle.
function selezionaAreaFase(area, fase) {
  areaSelezionata.value = area
  faseSelezionata.value = fase
  onFiltriChange()
}

// Scopo: paginazione DataTable documenti (lazy, paginator top; calcolo
//        pagina nel BB usePagedDashFetch).
function onDocumentiPage(event) {
  store.applyDocumentiPage(event)
  loadDocumenti()
}

// Scopo: ordinamento colonne (server-side, lista lazy): aggiorna lo stato sort
//        e ricarica dalla PAGINA 1 — riordinare riparte dall'inizio, come i
//        cambi filtro. Corretto su tutte le pagine (non solo quella visibile).
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
      label: t('situazione_aperta.apri_documento'),
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
// rientro in foreground — refresh idempotente di riepilogo E lista
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
        <h2 style="margin: 0;">{{ t('situazione_aperta.page_title') }}</h2>
        <small class="text-color-secondary">{{ t('situazione_aperta.page_description') }}</small>
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <div class="app-dash-main">
      <!-- Card per area (click = filtro toggle sulla lista): donut per fase. -->
      <div class="app-dash-cards">
        <div
          v-for="card in cards"
          :key="card.area"
          class="app-dash-card"
          :class="{ 'is-selected': areaSelezionata === card.area }"
          role="button"
          tabindex="0"
          @click="selezionaArea(card.area)"
          @keydown.enter="selezionaArea(card.area)"
        >
          <span class="app-dash-card-title">
            {{ areaLabel(card.area) }}
            <!-- Focusabile + aria-label: il chiarimento sulla misura deve
                 essere raggiungibile anche da tastiera/screen reader (il
                 v-tooltip PrimeVue si attiva anche su focus). -->
            <i
              v-if="card.hint"
              v-tooltip.bottom="card.hint"
              class="pi pi-info-circle app-dash-card-hint"
              role="img"
              tabindex="0"
              :aria-label="card.hint"
              @click.stop
              @keydown.enter.stop
            />
          </span>
          <DonutFasi
            :fasi="card.fasi"
            :format="card.format"
            :size="110"
            @fase-click="(fase) => selezionaAreaFase(card.area, fase)"
          />
        </div>
      </div>

      <!-- Lista per "in essere da" con filtri fase + "aperti da oltre N gg".
           Niente data-key: la union e' cross-area (documento_id si ripete tra
           aree diverse). -->
      <div class="app-dash-fermi">
        <div class="app-page-toolbar">
          <h4 class="app-dash-fermi-title">
            {{ t('situazione_aperta.lista_titolo') }}
          </h4>
          <div class="app-page-filters">
            <label class="app-dash-filter-toggle">
              <span>{{ t('situazione_aperta.filtro_ritardo_label') }}</span>
              <Select
                v-model="ritardoGiorni"
                :options="ritardoOptions"
                option-label="label"
                option-value="value"
                size="small"
                style="width: 150px;"
                @change="onFiltriChange"
              />
            </label>
            <Select
              v-model="faseSelezionata"
              :options="faseOptions"
              option-label="label"
              option-value="value"
              :placeholder="t('situazione_aperta.filtro_fase_tutte')"
              size="small"
              style="width: 200px;"
              @change="onFiltriChange"
            />
          </div>
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
          <Column field="anzianita_giorni" :header="t('situazione_aperta.col_aperto_da')" sortable style="width: 130px;">
            <template #body="{ data }">
              <span
                class="app-dash-ritardo"
                v-tooltip.bottom="data.data_riferimento ? displayDate(data.data_riferimento) : ''"
              >
                {{ data.anzianita_giorni !== null
                  ? t('situazione_aperta.aperto_da_giorni', { n: data.anzianita_giorni })
                  : '—' }}
              </span>
            </template>
          </Column>
          <Column field="area" :header="t('situazione_aperta.col_area')" style="width: 110px;">
            <template #body="{ data }">
              {{ areaLabel(data.area) }}
            </template>
          </Column>
          <Column field="codice" :header="t('situazione_aperta.col_codice')" sortable style="width: 130px;">
            <template #body="{ data }">
              {{ data.codice ?? '—' }}
            </template>
          </Column>
          <Column field="cliente_display" :header="t('situazione_aperta.col_cliente')" sortable>
            <template #body="{ data }">
              {{ data.cliente_display ?? '—' }}
            </template>
          </Column>
          <Column field="fase" :header="t('situazione_aperta.col_fase')" style="width: 140px;">
            <template #body="{ data }">
              <Tag
                v-if="data.fase"
                :value="faseLabel(data.fase)"
                :severity="faseDocumentoSeverity(data.fase)"
              />
              <span v-else>—</span>
            </template>
          </Column>
          <Column field="stato_codice" :header="t('situazione_aperta.col_stato')" style="width: 120px;">
            <template #body="{ data }">
              <Tag :value="data.stato_codice ?? '—'" :severity="statoSeverity(data)" />
            </template>
          </Column>
          <Column field="valore_totale" :header="t('situazione_aperta.col_valore')" sortable style="width: 120px;">
            <template #body="{ data }">
              {{ data.valore_totale !== null ? formatCurrency(data.valore_totale) : '—' }}
            </template>
          </Column>
          <Column field="unita_totali" :header="t('situazione_aperta.col_unita')" style="width: 90px;">
            <template #body="{ data }">
              {{ data.unita_totali ?? '—' }}
            </template>
          </Column>
          <Column field="motivo_fermo" :header="t('situazione_aperta.col_motivo')">
            <template #body="{ data }">
              {{ data.motivo_fermo ? motivoLabel(data.motivo_fermo) : '—' }}
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
          :empty-text="t('situazione_aperta.nessun_documento')"
          :placeholder-text="t('situazione_aperta.non_caricato')"
        />
      </div>
    </div>
  </div>
</template>
