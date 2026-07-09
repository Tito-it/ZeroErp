<script setup>
// Scopo: Lente 1 Competenza — funnel commessa → fattura per mese di
//        competenza (brief-design-fatturazione-due-lenti §4, Fase 1 FE).
//        Dati reali da GET /vendite/dashboard-competenza/ (+ /attivita/,
//        /errori/) via store Pinia; la semantica stadi/ritardo/errori/misure
//        vive nel DB e nel BE (vw_dash_competenza_* + valore_display/totali,
//        DB-6): questa view rende soltanto. Telaio anno/mesi condiviso con la
//        dashboard 5-card (useDashMesiNav + DashMesiSidebar/DashMeseStepper);
//        qui restano solo card stadi, pannello errori e drill-down.
import { computed, nextTick, onActivated, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import DashMesiSidebar from '../../core/components/dash/DashMesiSidebar.vue'
import DashMeseStepper from '../../core/components/dash/DashMeseStepper.vue'
import DonutTransito from '../../core/components/charts/DonutTransito.vue'
import { useDashMesiNav } from '../../core/composables/useDashMesiNav'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { MANAGE_ICONS, PAGINATION, READONLY_DOMAINS } from '../../core/constants'
import { extractApiError } from '../../core/utils/apiError'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { statoDocFiscaleSeverity } from '../../core/utils/severity'
import { useDashboardCompetenzaStore } from '../stores/dashboardCompetenza'

const { t, te } = useI18n()
const notify = useNotify()

// Provider readonly di area: la lente e' consultazione pura, ma il provider
// mantiene il pattern standard (ReadonlyBadge nel suffix toolbar).
useReadonlyMode(READONLY_DOMAINS.VENDITE)

const store = useDashboardCompetenzaStore()
const {
  anno,
  meseIdx,
  stadioSelezionato,
  soloRitardo,
  mesi,
  attivita,
  attivitaCount,
  attivitaPage,
  attivitaPageSize,
  attivitaLoading,
  attivitaOrderBy,
  attivitaOrderDir,
  errori,
  erroriCount,
  erroriPage,
  erroriPageSize,
  erroriLoading,
} = storeToRefs(store)

// Telaio anno/mesi condiviso: competenzaCorrente e' derivata da (anno, mese)
// — race-free sul cambio anno (mai da mesi[], che puo' essere stale).
const { nomiMesi, competenzaCorrente, selezionaMese, cambiaAnno, stepMese } = useDashMesiNav({
  anno,
  meseIdx,
  onMeseChange: () => {
    store.resetAttivita()
    store.resetErrori()
  },
  onAnnoChange: loadMensile,
})

const meseCorrente = computed(() => mesi.value[meseIdx.value] ?? null)

// Scopo: decodifica i18n con fallback al codice grezzo: un nuovo stadio o
//        tipo evento introdotto DB-side si mostra col suo codice, non col
//        path della chiave i18n mancante (fail-visible).
function stadioLabel(stadio) {
  return labelOrCode(t, te, `dashboard_competenza.stadio_${String(stadio).toLowerCase()}`, stadio)
}

function tipoEventoLabel(codice) {
  return labelOrCode(t, te, `dashboard_competenza.tipo_evento.${codice}`, codice)
}

// Scopo: semaforo del mese: 'ok' = tutto fatturato senza errori; 'vuoto' =
//        zero attivita' e zero errori; 'aperto' = c'e' lavoro (badge ⚠ con le
//        attivita' da fatturare e/o badge ✖ con gli errori vivi — i due
//        contatori sono indipendenti e possono coesistere).
function computeStatoMese(mese) {
  if (!mese) return { stato: 'vuoto', aperti: 0, errori: 0 }
  const nTot = mese.stadi.reduce((acc, s) => acc + s.n_attivita, 0)
  const fatturate = mese.stadi.find((s) => s.stadio === 'FATTURATA')?.n_attivita ?? 0
  const aperti = nTot - fatturate
  const nErrori = mese.n_errori ?? 0
  if (nTot === 0 && nErrori === 0) return { stato: 'vuoto', aperti: 0, errori: 0 }
  if (aperti === 0 && nErrori === 0) return { stato: 'ok', aperti: 0, errori: 0 }
  return { stato: 'aperto', aperti, errori: nErrori }
}

const statiMesi = computed(() => mesi.value.map(computeStatoMese))
const statoMeseCorrente = computed(() => statiMesi.value[meseIdx.value] ?? { stato: 'vuoto', aperti: 0, errori: 0 })

// Card per stadio: iterazione diretta di mese.stadi — l'ordine funnel, gli
// stadi presenti e la misura da mostrare (valore_display, DB-6) sono contratto
// BE; nessuna ri-codifica del vocabolario stadi lato FE.
const cards = computed(() => {
  if (!meseCorrente.value) return []
  return meseCorrente.value.stadi.map((cella) => ({
    stadio: cella.stadio,
    nAttivita: cella.n_attivita ?? 0,
    valoreDisplay: Number(cella.valore_display ?? 0),
    nInRitardo: cella.n_in_ritardo ?? 0,
    statiFattura: cella.stati_fattura ?? [],
  }))
})

// Totali di copertura del mese: calcolati dal BE (blocco `totali`, DB-6).
const totaliMese = computed(() => {
  const tot = meseCorrente.value?.totali ?? {}
  return {
    teorico: Number(tot.valore_teorico ?? 0),
    fatturato: Number(tot.valore_fatturato ?? 0),
    daFatturare: Number(tot.valore_da_fatturare ?? 0),
    nInRitardo: tot.n_in_ritardo ?? 0,
  }
})

const nErroriMese = computed(() => meseCorrente.value?.n_errori ?? 0)

const stadioSelezionatoLabel = computed(() =>
  stadioSelezionato.value ? stadioLabel(stadioSelezionato.value) : ''
)

// Scopo: carica l'aggregata annuale con gestione errori standard.
async function loadMensile() {
  try {
    await store.fetchMensile()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Scopo: carica la pagina corrente del drill-down attivita' (competenza
//        derivata da anno/mese selezionati, race-free sul cambio anno).
async function loadAttivita() {
  try {
    await store.fetchAttivita(competenzaCorrente.value)
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Scopo: carica la pagina corrente degli errori vivi del mese (blocco 4).
async function loadErrori() {
  try {
    await store.fetchErrori(competenzaCorrente.value)
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Ref alla sezione drill-down per l'auto-scroll post-selezione.
const attivitaSection = ref(null)

function selezionaStadio(stadio) {
  if (stadioSelezionato.value === stadio) {
    store.resetAttivita()
    return
  }
  store.resetAttivita()
  stadioSelezionato.value = stadio
  loadAttivita()
  // Su schermi piccoli la sezione renderizza sotto il fold: senza auto-scroll
  // il click sembra non fare nulla. Scroll dopo il re-render.
  nextTick(() => attivitaSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

// Il pannello errori segue (mese selezionato, aggregata): il watch scatta sia
// al cambio mese/anno (competenzaCorrente) sia all'arrivo di un'aggregata
// fresca (mesi cambia identita' a ogni fetchMensile) — MAI in base al solo
// valore del conteggio: due mesi con lo stesso n_errori non farebbero
// scattare un watch sul numero e il pannello resterebbe vuoto/stantio.
watch([competenzaCorrente, mesi], () => {
  if (nErroriMese.value > 0) {
    loadErrori()
  } else {
    store.resetErrori()
  }
})

// Scopo: toggle filtro recuperi tardivi del drill-down (riparte da pagina 1).
function onSoloRitardoChange() {
  attivitaPage.value = 1
  loadAttivita()
}

// Scopo: paginazione DataTable attivita' (lazy, paginator top; calcolo
//        pagina nel BB usePagedDashFetch).
function onAttivitaPage(event) {
  store.applyAttivitaPage(event)
  loadAttivita()
}

// Ordinamento colonne attivita' per il DataTable (controllato): campo dallo
// store, direzione nella convenzione PrimeVue (1 asc, -1 desc).
const attivitaSortOrder = computed(() => (attivitaOrderDir.value === 'desc' ? -1 : 1))

// Scopo: ordinamento colonne attivita' (server-side, lista lazy): aggiorna lo
//        stato sort e ricarica dalla PAGINA 1 senza deselezionare lo stadio
//        (come il filtro recuperi tardivi). Corretto su tutte le pagine.
function onAttivitaSort(event) {
  store.applyAttivitaSort(event)
  attivitaPage.value = 1
  loadAttivita()
}

// Scopo: paginazione DataTable errori (lazy, paginator top; calcolo
//        pagina nel BB usePagedDashFetch).
function onErroriPage(event) {
  store.applyErroriPage(event)
  loadErrori()
}

// Scopo: display compatto degli estremi fattura (serie numero/anno).
function fatturaDisplay(row) {
  if (!row.fattura_id) return '—'
  const serie = row.fattura_serie ? `${row.fattura_serie} ` : ''
  const numero = row.fattura_numero ?? '—'
  return `${serie}${numero}/${row.fattura_anno ?? '—'}`
}

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: () => {
      // Gli errori si riallineano da soli via watch sull'aggregata fresca.
      loadMensile()
      if (stadioSelezionato.value) loadAttivita()
    },
  },
])

// KeepAlive (ContentTabs): onActivated scatta anche al primo mount e a ogni
// rientro in foreground — refresh idempotente di aggregata E drill-down
// aperto; il pannello errori segue l'aggregata via watch
// (memoria feedback_keepalive_onactivated).
onActivated(() => {
  loadMensile()
  if (stadioSelezionato.value) loadAttivita()
})
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h2 style="margin: 0;">{{ t('dashboard_competenza.page_title') }}</h2>
        <small class="text-color-secondary">{{ t('dashboard_competenza.page_description') }}</small>
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <div class="app-dash-layout">
      <!-- Pannello laterale anno + 12 mesi (BB condiviso); badge di lente:
           errori vivi (✖) e attivita' aperte (⚠) indipendenti e coesistenti,
           check/minus solo per ok/vuoto. -->
      <DashMesiSidebar
        :anno="anno"
        :mesi="mesi"
        :mese-idx="meseIdx"
        :nomi-mesi="nomiMesi"
        @seleziona-mese="selezionaMese"
        @cambia-anno="cambiaAnno"
      >
        <template #badge="{ idx }">
          <span
            v-if="statiMesi[idx].errori > 0"
            class="app-dash-mese-errori"
            v-tooltip.right="t('dashboard_competenza.mese_errori', { n: statiMesi[idx].errori })"
          >
            <i class="pi pi-times-circle" /> {{ statiMesi[idx].errori }}
          </span>
          <span
            v-if="statiMesi[idx].aperti > 0"
            class="app-dash-mese-fermi"
            v-tooltip.right="t('dashboard_competenza.mese_aperti', { n: statiMesi[idx].aperti })"
          >
            <i class="pi pi-exclamation-triangle" /> {{ statiMesi[idx].aperti }}
          </span>
          <i
            v-if="statiMesi[idx].stato === 'ok'"
            class="pi pi-check app-dash-mese-ok"
            v-tooltip.right="t('dashboard_competenza.mese_ok')"
          />
          <i
            v-else-if="statiMesi[idx].stato === 'vuoto'"
            class="pi pi-minus app-dash-mese-vuoto"
            v-tooltip.right="t('dashboard_competenza.mese_vuoto')"
          />
        </template>
      </DashMesiSidebar>

      <!-- Colonna principale: competenza + card stadi + totali + errori + drill-down. -->
      <div class="app-dash-main">
        <!-- Stepper compatto anno/mese (BB condiviso): solo piccoli schermi. -->
        <DashMeseStepper
          :anno="anno"
          :mese-idx="meseIdx"
          :nomi-mesi="nomiMesi"
          @step="stepMese"
        >
          <template #badge>
            <span v-if="statoMeseCorrente.errori > 0" class="app-dash-mese-errori">
              <i class="pi pi-times-circle" /> {{ statoMeseCorrente.errori }}
            </span>
            <span v-if="statoMeseCorrente.aperti > 0" class="app-dash-mese-fermi">
              <i class="pi pi-exclamation-triangle" /> {{ statoMeseCorrente.aperti }}
            </span>
            <i v-if="statoMeseCorrente.stato === 'ok'" class="pi pi-check app-dash-mese-ok" />
            <i v-else-if="statoMeseCorrente.stato === 'vuoto'" class="pi pi-minus app-dash-mese-vuoto" />
          </template>
        </DashMeseStepper>

        <div class="app-dash-header">
          <h3 style="margin: 0;">
            {{ t('dashboard_competenza.competenza_titolo', { mese: nomiMesi[meseIdx], anno }) }}
          </h3>
        </div>

        <div class="app-dash-cards">
          <!-- Copertura del mese: totali BE (fatturato = imponibile, DB-6). -->
          <div class="app-dash-card" style="cursor: default;">
            <span class="app-dash-card-title">
              {{ t('dashboard_competenza.copertura_titolo') }}
            </span>
            <DonutTransito
              :transitato="totaliMese.fatturato"
              :fermo="totaliMese.daFatturare"
              format="currency"
              :label-transitato="t('dashboard_competenza.fatturato')"
              :label-fermo="t('dashboard_competenza.da_fatturare')"
            />
          </div>

          <!-- Card stadio funnel (ordine e misura dal BE): click → drill-down. -->
          <div
            v-for="card in cards"
            :key="card.stadio"
            class="app-dash-card"
            :class="{ 'is-selected': stadioSelezionato === card.stadio }"
            role="button"
            tabindex="0"
            @click="selezionaStadio(card.stadio)"
            @keydown.enter="selezionaStadio(card.stadio)"
          >
            <span class="app-dash-card-title">{{ stadioLabel(card.stadio) }}</span>
            <span class="app-dash-stat-n">{{ card.nAttivita }}</span>
            <span class="app-dash-stat-sub">{{ t('dashboard_competenza.n_attivita') }}</span>
            <span class="app-dash-stat-euro">{{ formatCurrency(card.valoreDisplay) }}</span>
            <span v-if="card.nInRitardo > 0" class="app-dash-ritardo">
              <i class="pi pi-clock" />
              {{ t('dashboard_competenza.in_ritardo', { n: card.nInRitardo }) }}
            </span>
            <!-- Breakdown per stato documento fiscale (blocco 3a). -->
            <div v-if="card.statiFattura.length > 0" class="app-dash-breakdown">
              <div
                v-for="stato in card.statiFattura"
                :key="stato.stato_fattura_codice_interno ?? 'nd'"
                class="app-dash-breakdown-row"
              >
                <Tag
                  :value="stato.stato_fattura_codice ?? '—'"
                  :severity="statoDocFiscaleSeverity(stato.stato_fattura_codice_interno)"
                />
                <span>{{ stato.n_attivita }} · {{ formatCurrency(Number(stato.valore_fatturato ?? 0)) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="app-dash-totali">
          <span>
            {{ t('dashboard_competenza.totale_competenza') }}
            <strong>{{ formatCurrency(totaliMese.teorico) }}</strong>
          </span>
          <span>
            {{ t('dashboard_competenza.fatturato_mese') }}
            <strong>{{ formatCurrency(totaliMese.fatturato) }}</strong>
          </span>
          <span>
            {{ t('dashboard_competenza.da_fatturare_mese') }}
            <strong>{{ formatCurrency(totaliMese.daFatturare) }}</strong>
          </span>
          <span v-if="totaliMese.nInRitardo > 0">
            {{ t('dashboard_competenza.in_ritardo_mese') }}
            <strong>{{ totaliMese.nInRitardo }}</strong>
          </span>
        </div>

        <!-- Pannello errori vivi del mese (blocco 4). -->
        <div v-if="nErroriMese > 0" class="app-dash-fermi">
          <h4 class="app-dash-fermi-title">
            <i class="pi pi-times-circle app-dash-mese-errori" />
            {{ t('dashboard_competenza.errori_titolo', { n: erroriCount }) }}
          </h4>
          <DataTable
            :value="errori"
            :loading="erroriLoading"
            :total-records="erroriCount"
            :rows="erroriPageSize"
            :first="(erroriPage - 1) * erroriPageSize"
            paginator
            paginator-position="top"
            lazy
            :rows-per-page-options="PAGINATION.ROWS_OPTIONS"
            class="app-datatable app-datatable--inner"
            striped-rows
            @page="onErroriPage"
          >
            <Column field="tipo_evento" :header="t('dashboard_competenza.col_tipo_evento')" style="width: 140px;">
              <template #body="{ data }">
                <Tag :value="tipoEventoLabel(data.tipo_evento)" severity="danger" />
              </template>
            </Column>
            <Column field="lotto_codice" :header="t('dashboard_competenza.col_lotto')" style="width: 130px;">
              <template #body="{ data }">
                {{ data.lotto_codice ?? '—' }}
              </template>
            </Column>
            <Column field="fattura_numero" :header="t('dashboard_competenza.col_fattura')" style="width: 110px;">
              <template #body="{ data }">
                {{ fatturaDisplay(data) }}
              </template>
            </Column>
            <Column field="error_code" :header="t('dashboard_competenza.col_codice_errore')" style="width: 170px;">
              <template #body="{ data }">
                {{ data.error_code ?? data.task_code ?? '—' }}
              </template>
            </Column>
            <Column field="messaggio" :header="t('dashboard_competenza.col_messaggio')">
              <template #body="{ data }">
                {{ data.messaggio ?? '—' }}
              </template>
            </Column>
            <Column field="data_evento" :header="t('dashboard_competenza.col_data_evento')" style="width: 150px;">
              <template #body="{ data }">
                {{ data.data_evento ? displayTimestamp(data.data_evento) : '—' }}
              </template>
            </Column>
          </DataTable>
        </div>

        <!-- Drill-down attivita' in pagina (click su card stadio). -->
        <div ref="attivitaSection" class="app-dash-fermi">
          <template v-if="stadioSelezionato">
            <div class="app-page-toolbar">
              <h4 class="app-dash-fermi-title">
                {{ t('dashboard_competenza.attivita_titolo', { stadio: stadioSelezionatoLabel }) }}
              </h4>
              <label class="app-dash-filter-toggle">
                <Checkbox v-model="soloRitardo" binary @change="onSoloRitardoChange" />
                {{ t('dashboard_competenza.solo_ritardo') }}
              </label>
            </div>
            <DataTable
              v-if="attivitaCount > 0 || attivitaLoading"
              :value="attivita"
              :loading="attivitaLoading"
              :total-records="attivitaCount"
              :rows="attivitaPageSize"
              :first="(attivitaPage - 1) * attivitaPageSize"
              paginator
              paginator-position="top"
              lazy
              :rows-per-page-options="PAGINATION.ROWS_OPTIONS"
              :sort-field="attivitaOrderBy"
              :sort-order="attivitaSortOrder"
              class="app-datatable app-datatable--inner"
              striped-rows
              data-key="commessa_attivita_id"
              @page="onAttivitaPage"
              @sort="onAttivitaSort"
            >
              <Column field="commessa_codice" :header="t('dashboard_competenza.col_commessa')" sortable style="width: 130px;">
                <template #body="{ data }">
                  {{ data.commessa_codice ?? '—' }}
                </template>
              </Column>
              <Column field="cliente_display" :header="t('dashboard_competenza.col_cliente')" sortable>
                <template #body="{ data }">
                  {{ data.cliente_display ?? '—' }}
                </template>
              </Column>
              <Column field="articolo_codice" :header="t('dashboard_competenza.col_articolo')" sortable>
                <template #body="{ data }">
                  {{ data.articolo_descrizione ?? data.articolo_codice ?? '—' }}
                </template>
              </Column>
              <Column field="data_attivita" :header="t('dashboard_competenza.col_data_attivita')" sortable style="width: 110px;">
                <template #body="{ data }">
                  {{ data.data_attivita ? displayDate(data.data_attivita) : '—' }}
                </template>
              </Column>
              <Column field="valore" :header="t('dashboard_competenza.col_valore')" sortable style="width: 120px;">
                <template #body="{ data }">
                  {{ data.valore !== null ? formatCurrency(data.valore) : '—' }}
                </template>
              </Column>
              <Column field="emessa_in_ritardo" :header="t('dashboard_competenza.col_ritardo')" style="width: 90px;">
                <template #body="{ data }">
                  <span v-if="data.emessa_in_ritardo" class="app-dash-ritardo">
                    <i class="pi pi-clock" v-tooltip.bottom="t('dashboard_competenza.emessa_in_ritardo_tooltip')" />
                  </span>
                  <span v-else>—</span>
                </template>
              </Column>
              <Column field="fattura_numero" :header="t('dashboard_competenza.col_fattura')" style="width: 110px;">
                <template #body="{ data }">
                  {{ fatturaDisplay(data) }}
                </template>
              </Column>
              <Column field="stato_fattura_codice" :header="t('dashboard_competenza.col_stato_fattura')" style="width: 120px;">
                <template #body="{ data }">
                  <Tag
                    v-if="data.stato_fattura_codice"
                    :value="data.stato_fattura_codice"
                    :severity="statoDocFiscaleSeverity(data.stato_fattura_codice_interno)"
                  />
                  <span v-else>—</span>
                </template>
              </Column>
              <Column field="valore_fatturato" :header="t('dashboard_competenza.col_fatturato')" style="width: 120px;">
                <template #body="{ data }">
                  {{ data.valore_fatturato !== null ? formatCurrency(data.valore_fatturato) : '—' }}
                </template>
              </Column>
            </DataTable>
            <div v-else class="app-empty-state">
              <i class="pi pi-check-circle" />
              <p>{{ t('dashboard_competenza.nessuna_attivita') }}</p>
            </div>
          </template>
          <div v-else class="app-empty-state">
            <i class="pi pi-chart-pie" />
            <p>{{ t('dashboard_competenza.attivita_hint') }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
