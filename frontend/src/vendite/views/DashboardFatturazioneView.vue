<script setup>
// Scopo: Dashboard fatturazione — controllo del transito per competenza
//        (brief-design-dashboard-fatturazione §7, Fase 3 FE).
//        Dati reali da GET /vendite/dashboard-fatturazione/ (+ /fermi/) via
//        store Pinia; la semantica totale/transitato/fermo vive nel DB.
//        Layout: pannello laterale anno + 12 mesi con semaforo (D-5) —
//        stepper compatto su piccoli schermi; card per area (donut € /
//        frazione conteggi, D-2/D-3/D-4); drill-down fermi in pagina.
import { computed, nextTick, onActivated, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import DonutTransito from '../../core/components/charts/DonutTransito.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { MANAGE_ICONS, PAGINATION, READONLY_DOMAINS } from '../../core/constants'
import { extractApiError } from '../../core/utils/apiError'
import { formatCurrency } from '../../core/utils/format'
import {
  statoCommessaSeverity,
  statoContrattoSeverity,
  statoOffertaSeverity,
  statoOrdineSeverity,
  statoPreventiveSeverity,
} from '../../core/utils/severity'
import { useDashboardFatturazioneStore } from '../stores/dashboardFatturazione'

const { t, locale } = useI18n()
const notify = useNotify()
const router = useRouter()

// Provider readonly di area: la dashboard e' consultazione pura, ma il
// provider mantiene il pattern standard (ReadonlyBadge nel suffix toolbar).
useReadonlyMode(READONLY_DOMAINS.VENDITE)

const store = useDashboardFatturazioneStore()
const {
  anno,
  meseIdx,
  areaSelezionata,
  mesi,
  fermi,
  fermiCount,
  fermiPage,
  fermiPageSize,
  fermiLoading,
} = storeToRefs(store)

// Config UNICA per area (ordine funnel, allineata alla whitelist BE
// DASH_FATTURAZIONE_AREE). kind: 'euro' = donut con importi (D-4),
// 'count' = frazione n/n (D-2/D-3). route: lista FE per "apri documento"
// (null = area senza view, riga consultiva — COMMESSE in v1).
// severity: shortcut centralizzata in core/utils/severity.js per gli stati
// documento nel drill-down (un solo punto di modifica dei colori).
const AREE = [
  { key: 'PREVENTIVI', kind: 'euro', route: '/vendite/preventivi', severity: statoPreventiveSeverity },
  { key: 'ORDINI', kind: 'euro', route: '/vendite/ordini', severity: statoOrdineSeverity },
  { key: 'OFFERTE', kind: 'count', route: '/vendite/offerte', severity: statoOffertaSeverity },
  { key: 'CONTRATTI', kind: 'count', route: '/vendite/contratti', severity: statoContrattoSeverity },
  { key: 'COMMESSE', kind: 'euro', route: null, severity: statoCommessaSeverity },
]
const AREA_BY_KEY = Object.fromEntries(AREE.map((a) => [a.key, a]))

const meseCorrente = computed(() => mesi.value[meseIdx.value] ?? null)

// Nomi mese localizzati: un solo Intl.DateTimeFormat per (anno, locale),
// array di 12 stringhe — evita di ricostruire il formatter a ogni render.
const nomiMesi = computed(() => {
  const fmt = new Intl.DateTimeFormat(locale.value, { month: 'long' })
  return Array.from({ length: 12 }, (_, m) => fmt.format(new Date(anno.value, m, 1)))
})

// Scopo: semaforo del mese: 'ok' = ha dati e tutto transitato;
//        'fermi' = fermi > 0; 'vuoto' = zero dati.
function computeStatoMese(mese) {
  if (!mese) return { stato: 'vuoto', fermi: 0 }
  const nFermi = mese.aree.reduce((acc, a) => acc + a.n_fermi, 0)
  const nDocumenti = mese.aree.reduce((acc, a) => acc + a.n_documenti, 0)
  if (nDocumenti === 0) return { stato: 'vuoto', fermi: 0 }
  if (nFermi > 0) return { stato: 'fermi', fermi: nFermi }
  return { stato: 'ok', fermi: 0 }
}

// Semaforo pre-calcolato UNA volta per mese (usato dal pannello laterale e,
// per il mese corrente, dallo stepper) — niente ricalcolo nel template.
const statiMesi = computed(() => mesi.value.map(computeStatoMese))
const statoMeseCorrente = computed(() => statiMesi.value[meseIdx.value] ?? { stato: 'vuoto', fermi: 0 })

// Card del mese selezionato: config area + cella BE (valori string → Number).
const cards = computed(() => {
  if (!meseCorrente.value) return []
  return AREE.map((cfg) => {
    const dati = meseCorrente.value.aree.find((a) => a.area === cfg.key) ?? {}
    const nDoc = dati.n_documenti ?? 0
    const nTrans = dati.n_transitati ?? 0
    return {
      ...cfg,
      ...dati,
      valoreTotale: Number(dati.valore_totale ?? 0),
      valoreTransitato: Number(dati.valore_transitato ?? 0),
      // Per le aree a conteggi: fermo = documenti - transitati (= n_fermi tra
      // i vivi), cosi' la frazione mostra transitati/documenti.
      nDocumenti: nDoc,
      nTransitati: nTrans,
      nFermoConteggio: Math.max(0, nDoc - nTrans),
    }
  })
})

// Riepilogo mese: somme delle sole aree in euro + conteggio abortiti.
const totaliMese = computed(() => {
  const vuoto = { totale: 0, transitato: 0, fermo: 0, abortiti: 0 }
  if (!meseCorrente.value) return vuoto
  const aree = meseCorrente.value.aree
  // Aree in euro dalla config unica (AREA_BY_KEY.kind), non sniffando la
  // forma del dato: evita un encoding parallelo di euro/count.
  const euro = aree.filter((a) => AREA_BY_KEY[a.area]?.kind === 'euro')
  const totale = euro.reduce((acc, a) => acc + Number(a.valore_totale), 0)
  const transitato = euro.reduce((acc, a) => acc + Number(a.valore_transitato), 0)
  return {
    totale,
    transitato,
    fermo: totale - transitato,
    abortiti: aree.reduce((acc, a) => acc + a.n_abortiti, 0),
  }
})

const areaSelezionataLabel = computed(() =>
  areaSelezionata.value ? t(`dashboard_fatturazione.area_${areaSelezionata.value.toLowerCase()}`) : ''
)

// Scopo: carica la matrice annuale con gestione errori standard.
async function loadMatrice() {
  try {
    await store.fetchMatrice()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Scopo: carica la pagina corrente di fermi (mese+area selezionati).
async function loadFermi() {
  if (!meseCorrente.value) return
  try {
    await store.fetchFermi(meseCorrente.value.competenza_mese)
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

function selezionaMese(idx) {
  meseIdx.value = idx
  store.resetFermi()
}

// Ref alla sezione fermi per l'auto-scroll post-selezione.
const fermiSection = ref(null)

function selezionaArea(areaKey) {
  if (areaSelezionata.value === areaKey) {
    store.resetFermi()
    return
  }
  store.resetFermi()
  areaSelezionata.value = areaKey
  loadFermi()
  // Su schermi piccoli la sezione fermi renderizza sotto il fold: senza
  // auto-scroll il click sembra non fare nulla. Scroll dopo il re-render.
  nextTick(() => fermiSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

function cambiaAnno(delta) {
  anno.value += delta
  store.resetFermi()
  loadMatrice()
}

// Scopo: passo mese ±1 per lo stepper compatto (piccoli schermi),
//        scavalcando l'anno ai bordi (dic ▶ = gennaio anno successivo).
function stepMese(delta) {
  let idx = meseIdx.value + delta
  if (idx > 11) {
    anno.value += 1
    idx = 0
    loadMatrice()
  } else if (idx < 0) {
    anno.value -= 1
    idx = 11
    loadMatrice()
  }
  selezionaMese(idx)
}

// Scopo: paginazione DataTable fermi (lazy, paginator top).
function onFermiPage(event) {
  fermiPageSize.value = event.rows
  fermiPage.value = Math.floor(event.first / event.rows) + 1
  loadFermi()
}

// Severity Tag per lo stato documento del drill-down: dispatch alla shortcut
// centralizzata dell'area selezionata (colori single-source in severity.js).
function statoSeverity(codice) {
  const fn = AREA_BY_KEY[areaSelezionata.value]?.severity
  return fn ? fn(codice) : 'secondary'
}

// Azioni riga drill-down: "apri documento" naviga alla lista area con
// ?search=<codice> (pattern ricerca-universale). COMMESSE: consultiva (v1).
function buildRowActions(data) {
  const route = AREA_BY_KEY[areaSelezionata.value]?.route
  return [
    {
      key: 'apri',
      label: t('dashboard_fatturazione.apri_documento'),
      icon: MANAGE_ICONS.LIST,
      visible: Boolean(route && data.codice),
      command: () => router.push({ path: route, query: { search: data.codice } }),
    },
  ]
}

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: () => {
      loadMatrice()
      if (areaSelezionata.value) loadFermi()
    },
  },
])

// KeepAlive (ContentTabs): onActivated scatta anche al primo mount e a ogni
// rientro in foreground — refresh idempotente di matrice E drill-down aperto,
// cosi' card e tabella non restano incoerenti dopo modifiche in altri tab
// (memoria feedback_keepalive_onactivated).
onActivated(() => {
  loadMatrice()
  if (areaSelezionata.value) loadFermi()
})
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h2 style="margin: 0;">{{ t('dashboard_fatturazione.page_title') }}</h2>
        <small class="text-color-secondary">{{ t('dashboard_fatturazione.page_description') }}</small>
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <div class="app-dash-layout">
      <!-- Pannello laterale: anno libero + 12 mesi con semaforo (D-5). -->
      <aside class="app-dash-mesi">
        <div class="app-dash-anno">
          <Button
            icon="pi pi-chevron-left"
            text
            rounded
            size="small"
            :aria-label="t('dashboard_fatturazione.anno_precedente')"
            v-tooltip.bottom="t('dashboard_fatturazione.anno_precedente')"
            @click="cambiaAnno(-1)"
          />
          <span>{{ anno }}</span>
          <Button
            icon="pi pi-chevron-right"
            text
            rounded
            size="small"
            :aria-label="t('dashboard_fatturazione.anno_successivo')"
            v-tooltip.bottom="t('dashboard_fatturazione.anno_successivo')"
            @click="cambiaAnno(1)"
          />
        </div>
        <button
          v-for="(mese, idx) in mesi"
          :key="mese.competenza_mese"
          type="button"
          class="app-dash-mese-btn"
          :class="{ 'is-active': idx === meseIdx }"
          @click="selezionaMese(idx)"
        >
          <span class="app-dash-mese-nome">{{ nomiMesi[idx] }}</span>
          <i
            v-if="statiMesi[idx].stato === 'ok'"
            class="pi pi-check app-dash-mese-ok"
            v-tooltip.right="t('dashboard_fatturazione.mese_ok')"
          />
          <span
            v-else-if="statiMesi[idx].stato === 'fermi'"
            class="app-dash-mese-fermi"
            v-tooltip.right="t('dashboard_fatturazione.mese_fermi', { n: statiMesi[idx].fermi })"
          >
            <i class="pi pi-exclamation-triangle" /> {{ statiMesi[idx].fermi }}
          </span>
          <i
            v-else
            class="pi pi-minus app-dash-mese-vuoto"
            v-tooltip.right="t('dashboard_fatturazione.mese_vuoto')"
          />
        </button>
      </aside>

      <!-- Colonna principale: competenza + card aree + totali + fermi. -->
      <div class="app-dash-main">
        <!-- Stepper compatto anno/mese: visibile SOLO su piccoli schermi
             (CSS-first, sostituisce il pannello 12 mesi). -->
        <div class="app-dash-stepper">
          <Button
            icon="pi pi-chevron-left"
            text
            rounded
            size="small"
            :aria-label="t('dashboard_fatturazione.mese_precedente')"
            @click="stepMese(-1)"
          />
          <span class="app-dash-stepper-label">
            {{ nomiMesi[meseIdx] }} {{ anno }}
            <i v-if="statoMeseCorrente.stato === 'ok'" class="pi pi-check app-dash-mese-ok" />
            <span v-else-if="statoMeseCorrente.stato === 'fermi'" class="app-dash-mese-fermi">
              <i class="pi pi-exclamation-triangle" /> {{ statoMeseCorrente.fermi }}
            </span>
            <i v-else class="pi pi-minus app-dash-mese-vuoto" />
          </span>
          <Button
            icon="pi pi-chevron-right"
            text
            rounded
            size="small"
            :aria-label="t('dashboard_fatturazione.mese_successivo')"
            @click="stepMese(1)"
          />
        </div>

        <div class="app-dash-header">
          <h3 style="margin: 0;">
            {{ t('dashboard_fatturazione.competenza_titolo', { mese: nomiMesi[meseIdx], anno }) }}
          </h3>
        </div>

        <div class="app-dash-cards">
          <div
            v-for="card in cards"
            :key="card.key"
            class="app-dash-card"
            :class="{ 'is-selected': areaSelezionata === card.key }"
            role="button"
            tabindex="0"
            @click="selezionaArea(card.key)"
            @keydown.enter="selezionaArea(card.key)"
          >
            <span class="app-dash-card-title">
              {{ t(`dashboard_fatturazione.area_${card.key.toLowerCase()}`) }}
            </span>

            <!-- Aree in euro: donut transitato vs fermo (D-4: imponibile).
                 Aree a conteggi (D-2/D-3): frazione n/n, stessa card. -->
            <DonutTransito
              v-if="card.kind === 'euro'"
              :transitato="card.valoreTransitato"
              :fermo="card.valoreTotale - card.valoreTransitato"
              format="currency"
              :label-transitato="t('dashboard_fatturazione.transitato')"
              :label-fermo="t('dashboard_fatturazione.fermo')"
            />
            <DonutTransito
              v-else
              mode="fraction"
              format="count"
              :transitato="card.nTransitati"
              :fermo="card.nFermoConteggio"
              :label-transitato="t('dashboard_fatturazione.transitati_n')"
              :label-fermo="t('dashboard_fatturazione.fermi_n')"
            />
          </div>
        </div>

        <div class="app-dash-totali">
          <span>
            {{ t('dashboard_fatturazione.totale_mese') }}
            <strong>{{ formatCurrency(totaliMese.totale) }}</strong>
          </span>
          <span>
            {{ t('dashboard_fatturazione.transitato_mese') }}
            <strong>{{ formatCurrency(totaliMese.transitato) }}</strong>
          </span>
          <span>
            {{ t('dashboard_fatturazione.fermo_mese') }}
            <strong>{{ formatCurrency(totaliMese.fermo) }}</strong>
          </span>
          <span v-if="totaliMese.abortiti > 0">
            {{ t('dashboard_fatturazione.abortiti_mese') }}
            <strong>{{ totaliMese.abortiti }}</strong>
          </span>
        </div>

        <!-- Drill-down fermi in pagina (click su card, §7). -->
        <div ref="fermiSection" class="app-dash-fermi">
          <template v-if="areaSelezionata">
            <h4 class="app-dash-fermi-title">
              {{ t('dashboard_fatturazione.fermi_titolo', { area: areaSelezionataLabel }) }}
            </h4>
            <DataTable
              v-if="fermiCount > 0 || fermiLoading"
              :value="fermi"
              :loading="fermiLoading"
              :total-records="fermiCount"
              :rows="fermiPageSize"
              :first="(fermiPage - 1) * fermiPageSize"
              paginator
              paginator-position="top"
              lazy
              :rows-per-page-options="PAGINATION.ROWS_OPTIONS"
              class="app-datatable app-datatable--inner"
              striped-rows
              data-key="documento_id"
              @page="onFermiPage"
            >
              <Column field="codice" :header="t('dashboard_fatturazione.col_codice')" style="width: 130px;">
                <template #body="{ data }">
                  {{ data.codice ?? '—' }}
                </template>
              </Column>
              <Column field="cliente_display" :header="t('dashboard_fatturazione.col_cliente')">
                <template #body="{ data }">
                  {{ data.cliente_display ?? '—' }}
                </template>
              </Column>
              <Column field="valore_totale" :header="t('dashboard_fatturazione.col_valore')" style="width: 130px;">
                <template #body="{ data }">
                  {{ data.valore_totale !== null ? formatCurrency(data.valore_totale) : '—' }}
                </template>
              </Column>
              <Column field="unita_totali" :header="t('dashboard_fatturazione.col_unita')" style="width: 110px;">
                <template #body="{ data }">
                  {{ data.unita_transitate ?? 0 }}/{{ data.unita_totali ?? 0 }}
                </template>
              </Column>
              <Column field="motivo_fermo" :header="t('dashboard_fatturazione.col_motivo')">
                <template #body="{ data }">
                  {{ data.motivo_fermo ? t(`dashboard_fatturazione.motivo_fermo.${data.motivo_fermo}`) : '—' }}
                </template>
              </Column>
              <Column field="stato_codice" :header="t('dashboard_fatturazione.col_stato')" style="width: 130px;">
                <template #body="{ data }">
                  <Tag
                    :value="data.stato_codice ?? '—'"
                    :severity="statoSeverity(data.stato_codice_interno)"
                  />
                </template>
              </Column>
              <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
                <template #body="{ data }">
                  <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
                </template>
              </Column>
            </DataTable>
            <div v-else class="app-empty-state">
              <i class="pi pi-check-circle" />
              <p>{{ t('dashboard_fatturazione.nessun_fermo') }}</p>
            </div>
          </template>
          <div v-else class="app-empty-state">
            <i class="pi pi-chart-pie" />
            <p>{{ t('dashboard_fatturazione.fermi_hint') }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
