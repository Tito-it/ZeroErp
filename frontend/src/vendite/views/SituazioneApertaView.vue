<script setup>
// Scopo: Situazione aperta — stock dei documenti aperti in pipeline, per
//        fase normalizzata e SENZA asse temporale (brief-design-fatturazione-
//        due-lenti §6-bis, Fase 3: trasformazione della 5-card). Terza vista
//        dei cruscotti: la Lente 1 guarda il mese di competenza, la Lente 2
//        il lavoro da sbloccare ora, qui si fotografa TUTTO l'aperto (🟢
//        fisiologici inclusi). Dati reali da GET /vendite/dashboard-aperto/
//        (+ /documenti/) via store Pinia; aree, fasi e ordinamento vivono nel
//        DB/BE (vw_dash_aperto_* + config.stati_doc_*): la view rende.
//        Layout: card per area (click = filtro) con transito e chip per fase
//        + lista dei documenti ordinata per "in essere da".
import { computed, onActivated } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import DashEmptyState from '../../core/components/DashEmptyState.vue'
import DonutTransito from '../../core/components/charts/DonutTransito.vue'
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
  soloAperti,
  aree,
  fasi,
  documenti,
  documentiCount,
  documentiPage,
  documentiPageSize,
  documentiLoading,
  documentiLoaded,
} = storeToRefs(store)

// Scopo: decodifiche i18n fail-visible dai BB condivisi di dashboardAree
//        (gruppo dash_comune, riusato dal Backlog): alias locali per tenere
//        il template invariato.
const areaLabel = (area) => dashAreaLabel(t, te, area)
const faseLabel = (fase) => dashFaseLabel(t, te, fase)
const motivoLabel = (motivo) => dashMotivoLabel(t, te, motivo)

// La fase CHIUSO e' stock storico che cresce per sempre: resta FUORI dagli
// aggregati del donut (che fotografa la pipeline viva), mentre le sue
// eventuali anomalie aperte restano visibili nelle chip e in lista.
const FASE_CHIUSO = 'CHIUSO'

// Card per area: iterazione diretta di aree dal BE (4 sempre presenti in
// ordine funnel, eventuali aree future accodate fail-visible). La misura la
// decide il BE (DL-11): valore_* stringa per le aree con valori, null per le
// aree a conteggi — il FE legge il payload, non tiene una seconda copia della
// whitelist euro. Donut: aree con valori = residuo (totale - transitato: i
// documenti completamente transitati contribuiscono 0); aree a conteggi =
// frazione documenti. Le chip mostrano le fasi con aperti (n_aperti > 0).
const cards = computed(() =>
  aree.value.map((a) => {
    const isEuro = a.valore_totale !== null
    const fasiArea = a.fasi ?? []
    const vive = fasiArea.filter((f) => f.fase !== FASE_CHIUSO)
    const somma = (sel) => vive.reduce((acc, f) => acc + (sel(f) ?? 0), 0)
    const nDocVivi = somma((f) => f.n_documenti)
    const nApertiVivi = somma((f) => f.n_aperti)
    const totale = somma((f) => Number(f.valore_totale ?? 0))
    const transitato = somma((f) => Number(f.valore_transitato ?? 0))
    return {
      area: a.area,
      nAperti: a.n_aperti ?? 0,
      donut: isEuro
        ? { mode: 'donut', format: 'currency', transitato, fermo: totale - transitato }
        : {
            mode: 'fraction',
            format: 'count',
            transitato: nDocVivi - nApertiVivi,
            fermo: nApertiVivi,
          },
      fasi: fasiArea.filter((f) => (f.n_aperti ?? 0) > 0),
    }
  })
)

// Opzioni filtro fase: dal vocabolario top-level servito dal riepilogo BE
// (4 fasi sempre presenti + eventuali future accodate fail-visible) —
// nessuna copia FE del vocabolario config.stati_doc_*.
const faseOptions = computed(() => [
  { value: null, label: t('situazione_aperta.filtro_fase_tutte') },
  ...fasi.value.map((f) => ({ value: f, label: faseLabel(f) })),
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

// Scopo: handler unico di cambio filtri lista (fase, solo aperti, area):
//        riparte da pagina 1 e ricarica coi filtri correnti.
function onFiltriChange() {
  store.resetDocumenti()
  loadDocumenti()
}

// Scopo: click su card area = toggle del filtro area.
function selezionaArea(area) {
  areaSelezionata.value = areaSelezionata.value === area ? null : area
  onFiltriChange()
}

// Scopo: paginazione DataTable documenti (lazy, paginator top; calcolo
//        pagina nel BB usePagedDashFetch).
function onDocumentiPage(event) {
  store.applyDocumentiPage(event)
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
      <!-- Card per area (click = filtro toggle sulla lista). -->
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
          <span class="app-dash-card-title">{{ areaLabel(card.area) }}</span>
          <DonutTransito
            :transitato="card.donut.transitato"
            :fermo="card.donut.fermo"
            :mode="card.donut.mode"
            :format="card.donut.format"
            :label-transitato="t('situazione_aperta.label_transitato')"
            :label-fermo="t('situazione_aperta.label_aperto')"
            :size="110"
          />
          <span class="app-dash-stat-n">{{ card.nAperti }}</span>
          <span class="app-dash-stat-sub">{{ t('situazione_aperta.n_aperti') }}</span>
          <!-- Chip per fase: solo le fasi con documenti aperti. -->
          <span v-if="card.fasi.length" class="app-dash-fasi-chips">
            <Tag
              v-for="f in card.fasi"
              :key="f.fase"
              :value="`${faseLabel(f.fase)} ${f.n_aperti}`"
              :severity="faseDocumentoSeverity(f.fase)"
            />
          </span>
        </div>
      </div>

      <!-- Lista per "in essere da" con filtri fase + solo aperti. Niente
           data-key: la union e' cross-area (documento_id si ripete tra
           aree diverse). -->
      <div class="app-dash-fermi">
        <div class="app-page-toolbar">
          <h4 class="app-dash-fermi-title">
            {{ t('situazione_aperta.lista_titolo') }}
          </h4>
          <div class="app-page-filters">
            <label class="app-dash-filter-toggle">
              <ToggleSwitch v-model="soloAperti" @change="onFiltriChange" />
              <span>{{ t('situazione_aperta.solo_aperti') }}</span>
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
          class="app-datatable app-datatable--inner"
          striped-rows
          @page="onDocumentiPage"
        >
          <Column field="data_riferimento" :header="t('situazione_aperta.col_in_essere_da')" style="width: 120px;">
            <template #body="{ data }">
              {{ data.data_riferimento ? displayDate(data.data_riferimento) : '—' }}
            </template>
          </Column>
          <Column field="area" :header="t('situazione_aperta.col_area')" style="width: 110px;">
            <template #body="{ data }">
              {{ areaLabel(data.area) }}
            </template>
          </Column>
          <Column field="codice" :header="t('situazione_aperta.col_codice')" style="width: 130px;">
            <template #body="{ data }">
              {{ data.codice ?? '—' }}
            </template>
          </Column>
          <Column field="cliente_display" :header="t('situazione_aperta.col_cliente')">
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
          <Column field="valore_totale" :header="t('situazione_aperta.col_valore')" style="width: 120px;">
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
