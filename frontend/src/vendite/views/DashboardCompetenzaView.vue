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
import Button from 'primevue/button'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import CommessaGestioneDrawer from '../components/CommessaGestioneDrawer.vue'
import LottoDrawer from '../components/LottoDrawer.vue'
import { useDashMesiNav } from '../../core/composables/useDashMesiNav'
import { useReadonlyMode, useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { useJobPolling } from '../../core/composables/useJobPolling'
import { MANAGE_ICONS, PAGINATION, READONLY_DOMAINS } from '../../core/constants'
import { extractApiError } from '../../core/utils/apiError'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { statoDocFiscaleSeverity } from '../../core/utils/severity'
import { approvaCompetenza } from '../api/commesse'
import { getFatturazioneRun, runFatturazione, runNumerazione } from '../api/lotti'
import { useDashboardCompetenzaStore } from '../stores/dashboardCompetenza'

const { t, te } = useI18n()
const notify = useNotify()

// Provider readonly di area: con le azioni di processo (Fase A cockpit) il
// readonly ora governa anche i pulsanti Approva (ReadonlyBadge + gate).
useReadonlyMode(READONLY_DOMAINS.VENDITE)
const areaReadonly = useInjectReadonly()
// Gate azione di processo (pattern action gate, L2): senza permesso i
// pulsanti/kebab di approvazione spariscono (il BE resta la difesa vera).
const { isAllowed: canApprovare } = useActionPermission('approva_attivita_commessa')
// Gate unico dell'approvazione (permesso + readonly): card e kebab usano lo
// stesso predicato — mai due copie che possono divergere.
const canApprova = computed(() => canApprovare.value && !areaReadonly.value)
// Gate del verbo FATTURA (C-6, I-7: separato da APPROVA e dalla numerazione).
// Stesso permesso dell'endpoint C-3 (genera_fatture_lotti) + readonly d'area.
const { isAllowed: canGenerareFatture } = useActionPermission('genera_fatture_lotti')
const canFatturare = computed(() => canGenerareFatture.value && !areaReadonly.value)
// Gate del verbo RENDI DEFINITIVE (C-7, atto fiscale I-7): permesso dedicato
// dell'endpoint C-4 (numera_fatture_lotti) + readonly d'area.
const { isAllowed: canNumerareFatture } = useActionPermission('numera_fatture_lotti')
const canNumerare = computed(() => canNumerareFatture.value && !areaReadonly.value)
const { execute, loading: azioneLoading } = useApiHandler()
const { confirmAction } = useConfirmAction()

const store = useDashboardCompetenzaStore()
const {
  anno,
  meseIdx,
  stadioSelezionato,
  soloRitardo,
  mesi,
  commesse,
  commesseCount,
  commessePage,
  commessePageSize,
  commesseLoading,
  commesseOrderBy,
  commesseOrderDir,
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
    store.resetCommesse()
    store.resetErrori()
  },
  onAnnoChange: loadMensile,
})

const meseCorrente = computed(() => mesi.value[meseIdx.value] ?? null)

// Scopo: decodifica i18n con fallback al codice grezzo: un nuovo stadio o
//        tipo evento introdotto DB-side si mostra col suo codice, non col
//        path della chiave i18n mancante (fail-visible).
function stadioLabel(stadio) {
  return labelOrCode(t, te, `vendite.dashboard_competenza.stadio_${String(stadio).toLowerCase()}`, stadio)
}

function tipoEventoLabel(codice) {
  return labelOrCode(t, te, `vendite.dashboard_competenza.tipo_evento.${codice}`, codice)
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

// Scopo: carica la pagina corrente del drill-down per commessa (competenza
//        derivata da anno/mese selezionati, race-free sul cambio anno).
async function loadCommesse() {
  try {
    await store.fetchCommesse(competenzaCorrente.value)
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
const commesseSection = ref(null)

function selezionaStadio(stadio) {
  if (stadioSelezionato.value === stadio) {
    store.resetCommesse()
    return
  }
  store.resetCommesse()
  stadioSelezionato.value = stadio
  loadCommesse()
  // Su schermi piccoli la sezione renderizza sotto il fold: senza auto-scroll
  // il click sembra non fare nulla. Scroll dopo il re-render.
  nextTick(() => commesseSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
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
  commessePage.value = 1
  loadCommesse()
}

// Scopo: paginazione DataTable commesse (lazy, paginator top; calcolo
//        pagina nel BB usePagedDashFetch).
function onCommessePage(event) {
  store.applyCommessePage(event)
  loadCommesse()
}

// Ordinamento colonne commesse per il DataTable (controllato): campo dallo
// store, direzione nella convenzione PrimeVue (1 asc, -1 desc).
const commesseSortOrder = computed(() => (commesseOrderDir.value === 'desc' ? -1 : 1))

// Scopo: ordinamento colonne commesse (server-side, lista lazy): aggiorna lo
//        stato sort e ricarica dalla PAGINA 1 senza deselezionare lo stadio
//        (come il filtro recuperi tardivi). Corretto su tutte le pagine.
function onCommesseSort(event) {
  store.applyCommesseSort(event)
  commessePage.value = 1
  loadCommesse()
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
      if (stadioSelezionato.value) loadCommesse()
    },
  },
])

// ------------------------------------------------------------------ azioni (Fase A cockpit)
// Card DA_APPROVARE del mese corrente (per contatore/valore della conferma).
const cardDaApprovare = computed(() => cards.value.find((c) => c.stadio === 'DA_APPROVARE') ?? null)

// Scopo: refresh post-azione — aggregata + drill-down aperto (gli errori
//        seguono l'aggregata via watch).
function reloadDopoAzione() {
  loadMensile()
  if (stadioSelezionato.value) loadCommesse()
}

// Scopo: verbo APPROVA a grana mese (A-2/D-3): conferma con contatore+valore
//        (WYSIWYG con la card), poi POST approva-competenza sul mese corrente.
function onApprovaMese() {
  const card = cardDaApprovare.value
  if (!card) return
  confirmAction({
    title: t('vendite.dashboard_competenza.approva_mese_header'),
    message: t('vendite.dashboard_competenza.approva_mese_conferma', {
      n: card.nAttivita,
      valore: formatCurrency(card.valoreDisplay),
      mese: `${nomiMesi.value[meseIdx.value]} ${anno.value}`,
    }),
    onAccept: async () => {
      const res = await execute(() => approvaCompetenza(competenzaCorrente.value))
      if (res !== null) {
        notify.success(t('vendite.dashboard_competenza.approva_mese_esito', {
          n: res?.approvate ?? 0,
          commesse: res?.commesse ?? 0,
        }))
        reloadDopoAzione()
      }
    },
  })
}

// -------------------------------------------------- verbi asincroni FATTURA / NUMERA (C-6/C-7)
// I due verbi non bloccanti «Fattura adesso» (C-6) e «Rendi definitive» (C-7)
// condividono il flusso: conferma → accoda (POST) → polling del job (GET
// run/<id>/) → esito + refresh. Estratto in un helper locale (regola del 2):
// cambiano solo API, testi e campi dell'esito. Ogni verbo ha il PROPRIO polling
// (loading del pulsante indipendente); vive sulla card del suo stadio (WYSIWYG),
// gate nel template. I-7: «Fattura» (pre-fiscale, ferma a EMESSA) e «Rendi
// definitive» (numerazione, atto fiscale) sono pulsanti SEPARATI su card diverse.
// Se il worker non e' schedulato il job resta PENDING → onTimeout avvisa "in
// coda" invece di girare all'infinito; colpi a vuoto del polling silenziosi.
function useVerboFatturazione({ apiFn, keys, buildEsitoOk }) {
  const { start, polling } = useJobPolling({
    fetchStatus: (jobId) => getFatturazioneRun(jobId),
    onDone: (stato) => {
      if (stato.stato === 'FATTO') {
        buildEsitoOk(stato.result ?? {})
      } else {
        // ERRORE/ANNULLATO: non andato a buon fine (payload, revoca…).
        notify.error(stato.ultimo_errore?.message || t(keys.errore))
      }
      reloadDopoAzione()
    },
    onTimeout: () => {
      notify.warn(t(keys.inCoda))
      reloadDopoAzione()
    },
  })
  function avvia() {
    confirmAction({
      title: t(keys.header),
      message: t(keys.conferma, {
        mese: `${nomiMesi.value[meseIdx.value]} ${anno.value}`,
      }),
      onAccept: async () => {
        const res = await execute(() => apiFn(competenzaCorrente.value))
        if (res === null) return
        notify.success(t(keys.accodato))
        start(res.job_id)
      },
    })
  }
  return { avvia, polling }
}

// Verbo FATTURA (C-6): card DA_EMETTERE. Corsia differita → ferma a EMESSA,
// cumulativo su competenza ≤ M.
const { avvia: onFatturaMese, polling: giroInCorso } = useVerboFatturazione({
  apiFn: runFatturazione,
  keys: {
    header: 'vendite.dashboard_competenza.fattura_mese_header',
    conferma: 'vendite.dashboard_competenza.fattura_mese_conferma',
    accodato: 'vendite.dashboard_competenza.fattura_mese_accodato',
    errore: 'vendite.dashboard_competenza.fattura_mese_errore',
    inCoda: 'vendite.dashboard_competenza.fattura_mese_in_coda',
  },
  buildEsitoOk: (r) => {
    const lane = Number(r.lane ?? 0)
    const falliti = Number(r.falliti ?? 0)
    if (falliti > 0) {
      notify.warn(t('vendite.dashboard_competenza.fattura_mese_esito_parziale', { lane, falliti }))
    } else {
      notify.success(t('vendite.dashboard_competenza.fattura_mese_esito', { lane }))
    }
  },
})

// Verbo RENDI DEFINITIVE (C-7): card EMESSA_NON_FATTURATA. Numerazione di
// perimetro (step DEFINITIVA sui lotti EMESSA del mese) — atto fiscale.
const { avvia: onRendiDefinitive, polling: numeraInCorso } = useVerboFatturazione({
  apiFn: runNumerazione,
  keys: {
    header: 'vendite.dashboard_competenza.numera_mese_header',
    conferma: 'vendite.dashboard_competenza.numera_mese_conferma',
    accodato: 'vendite.dashboard_competenza.numera_mese_accodato',
    errore: 'vendite.dashboard_competenza.numera_mese_errore',
    inCoda: 'vendite.dashboard_competenza.numera_mese_in_coda',
  },
  buildEsitoOk: (r) => {
    const lotti = Number(r.lotti ?? 0)
    const numerati = Number(r.numerati ?? 0)
    const saltati = Number(r.saltati ?? 0)
    const falliti = Number(r.falliti ?? 0)
    // «saltato» = lotto processato ma NON transitato a DEFINITIVA (es. legacy
    // senza step eseguibili): esito parziale quanto un errore, va mostrato.
    if (falliti > 0 || saltati > 0) {
      notify.warn(t('vendite.dashboard_competenza.numera_mese_esito_parziale', { numerati, saltati, falliti, lotti }))
    } else {
      notify.success(t('vendite.dashboard_competenza.numera_mese_esito', { numerati }))
    }
  },
})

// Scopo: verbo APPROVA a grana commessa dal drill-down (A-1, DEC-4): la riga e'
//        aggregata, quindi approva TUTTE le attivita' DA_APPROVARE della commessa
//        nel mese via approva-competenza scoped (commessa_ids=[id]) — non la
//        singola attivita' (che vive nel drawer). Conferma con contatore+codice.
function onApprovaCommessa(row) {
  confirmAction({
    title: t('vendite.dashboard_competenza.approva_commessa_header'),
    message: t('vendite.dashboard_competenza.approva_commessa_conferma', {
      n: row.n_attivita,
      commessa: row.commessa_codice ?? `#${row.commessa_id}`,
    }),
    onAccept: async () => {
      const res = await execute(() =>
        approvaCompetenza(competenzaCorrente.value, { commessaIds: [row.commessa_id] }))
      if (res !== null) {
        notify.success(t('vendite.dashboard_competenza.approva_commessa_esito', {
          n: res?.approvate ?? 0,
        }))
        reloadDopoAzione()
      }
    },
  })
}

// Drawer di governo commessa (A-4), aperto dal kebab del drill-down.
const commessaDrawerVisible = ref(false)
const commessaDrawerId = ref(null)

function apriCommessa(row) {
  commessaDrawerId.value = row.commessa_id
  commessaDrawerVisible.value = true
}

// Raggiungibilita' contestuale (B-5): dal pannello errori si atterra sul
// LottoDrawer diagnostico gia' filtrato sul lotto dell'evento — l'operatore
// passa dall'errore al governo del lotto (fatture/task-run/segnalazioni,
// ristampa) senza cercarlo a mano nella lista lotti. Solo le righe con
// lotto_id sono agganciabili (una FATTURA_CRITICA non ancora in lotto ne e'
// priva): il gate e' sul dato, non sul tipo evento.
const lottoDrawerVisible = ref(false)
const lottoDrawerId = ref(null)

function apriLotto(lottoId) {
  if (!lottoId) return
  lottoDrawerId.value = lottoId
  lottoDrawerVisible.value = true
}

// Scopo: kebab riga drill-down (per commessa) — Apri commessa sempre; Approva
//        solo sullo stadio DA_APPROVARE (con permesso e non in readonly),
//        approva l'intera popolazione DA_APPROVARE della commessa nel mese.
function buildCommessaRowActions(row) {
  return [
    {
      key: 'approva',
      label: t('vendite.dashboard_competenza.azione_approva'),
      icon: 'pi pi-check',
      visible: stadioSelezionato.value === 'DA_APPROVARE' && canApprova.value,
      disabled: azioneLoading.value,
      command: () => onApprovaCommessa(row),
    },
    {
      key: 'apri_commessa',
      label: t('vendite.dashboard_competenza.azione_apri_commessa'),
      icon: MANAGE_ICONS.COMMESSA,
      command: () => apriCommessa(row),
    },
  ]
}

// KeepAlive (ContentTabs): onActivated scatta anche al primo mount e a ogni
// rientro in foreground — refresh idempotente di aggregata E drill-down
// aperto; il pannello errori segue l'aggregata via watch
// (memoria feedback_keepalive_onactivated).
onActivated(() => {
  loadMensile()
  if (stadioSelezionato.value) loadCommesse()
})
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h2 style="margin: 0;">{{ t('vendite.dashboard_competenza.page_title') }}</h2>
        <small class="text-color-secondary">{{ t('vendite.dashboard_competenza.page_description') }}</small>
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
            v-tooltip.right="t('vendite.dashboard_competenza.mese_errori', { n: statiMesi[idx].errori })"
          >
            <i class="pi pi-times-circle" /> {{ statiMesi[idx].errori }}
          </span>
          <span
            v-if="statiMesi[idx].aperti > 0"
            class="app-dash-mese-fermi"
            v-tooltip.right="t('vendite.dashboard_competenza.mese_aperti', { n: statiMesi[idx].aperti })"
          >
            <i class="pi pi-exclamation-triangle" /> {{ statiMesi[idx].aperti }}
          </span>
          <i
            v-if="statiMesi[idx].stato === 'ok'"
            class="pi pi-check app-dash-mese-ok"
            v-tooltip.right="t('vendite.dashboard_competenza.mese_ok')"
          />
          <i
            v-else-if="statiMesi[idx].stato === 'vuoto'"
            class="pi pi-minus app-dash-mese-vuoto"
            v-tooltip.right="t('vendite.dashboard_competenza.mese_vuoto')"
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
            {{ t('vendite.dashboard_competenza.competenza_titolo', { mese: nomiMesi[meseIdx], anno }) }}
          </h3>
        </div>

        <div class="app-dash-cards">
          <!-- Copertura del mese: totali BE (fatturato = imponibile, DB-6). -->
          <div class="app-dash-card" style="cursor: default;">
            <span class="app-dash-card-title">
              {{ t('vendite.dashboard_competenza.copertura_titolo') }}
            </span>
            <DonutTransito
              :transitato="totaliMese.fatturato"
              :fermo="totaliMese.daFatturare"
              format="currency"
              :label-transitato="t('vendite.dashboard_competenza.fatturato')"
              :label-fermo="t('vendite.dashboard_competenza.da_fatturare')"
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
            <span class="app-dash-stat-sub">{{ t('vendite.dashboard_competenza.n_attivita') }}</span>
            <span class="app-dash-stat-euro">{{ formatCurrency(card.valoreDisplay) }}</span>
            <!-- Verbo APPROVA a grana mese (Fase A cockpit): solo sul card
                 DA_APPROVARE, gate permesso+readonly; @click.stop per non
                 attivare il drill-down della card. -->
            <Button
              v-if="card.stadio === 'DA_APPROVARE' && card.nAttivita > 0 && canApprova"
              :label="t('vendite.dashboard_competenza.approva_mese')"
              icon="pi pi-check-circle"
              size="small"
              :disabled="azioneLoading"
              style="margin-top: 0.5rem;"
              @click.stop="onApprovaMese"
            />
            <!-- Verbo FATTURA a grana mese (C-6): solo sul card DA_EMETTERE,
                 gate permesso+readonly; @click.stop per non attivare il
                 drill-down. Loading = giro in corso (polling non bloccante). -->
            <Button
              v-if="card.stadio === 'DA_EMETTERE' && card.nAttivita > 0 && canFatturare"
              :label="t('vendite.dashboard_competenza.fattura_mese')"
              icon="pi pi-file-export"
              size="small"
              :loading="giroInCorso"
              :disabled="azioneLoading || giroInCorso"
              style="margin-top: 0.5rem;"
              @click.stop="onFatturaMese"
            />
            <!-- Verbo RENDI DEFINITIVE a grana mese (C-7): solo sul card
                 EMESSA_NON_FATTURATA, gate permesso+readonly. Atto FISCALE
                 (I-7): severity warn per distinguerlo dal pre-fiscale «Fattura».
                 Loading = numerazione in corso (polling non bloccante). -->
            <Button
              v-if="card.stadio === 'EMESSA_NON_FATTURATA' && card.nAttivita > 0 && canNumerare"
              :label="t('vendite.dashboard_competenza.numera_mese')"
              icon="pi pi-lock"
              size="small"
              severity="warn"
              :loading="numeraInCorso"
              :disabled="azioneLoading || numeraInCorso"
              style="margin-top: 0.5rem;"
              @click.stop="onRendiDefinitive"
            />
            <span v-if="card.nInRitardo > 0" class="app-dash-ritardo">
              <i class="pi pi-clock" />
              {{ t('vendite.dashboard_competenza.in_ritardo', { n: card.nInRitardo }) }}
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
            {{ t('vendite.dashboard_competenza.totale_competenza') }}
            <strong>{{ formatCurrency(totaliMese.teorico) }}</strong>
          </span>
          <span>
            {{ t('vendite.dashboard_competenza.fatturato_mese') }}
            <strong>{{ formatCurrency(totaliMese.fatturato) }}</strong>
          </span>
          <span>
            {{ t('vendite.dashboard_competenza.da_fatturare_mese') }}
            <strong>{{ formatCurrency(totaliMese.daFatturare) }}</strong>
          </span>
          <span v-if="totaliMese.nInRitardo > 0">
            {{ t('vendite.dashboard_competenza.in_ritardo_mese') }}
            <strong>{{ totaliMese.nInRitardo }}</strong>
          </span>
        </div>

        <!-- Pannello errori vivi del mese (blocco 4). -->
        <div v-if="nErroriMese > 0" class="app-dash-fermi">
          <h4 class="app-dash-fermi-title">
            <i class="pi pi-times-circle app-dash-mese-errori" />
            {{ t('vendite.dashboard_competenza.errori_titolo', { n: erroriCount }) }}
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
            <Column field="tipo_evento" :header="t('vendite.dashboard_competenza.col_tipo_evento')" style="width: 140px;">
              <template #body="{ data }">
                <Tag :value="tipoEventoLabel(data.tipo_evento)" severity="danger" />
              </template>
            </Column>
            <Column field="lotto_codice" :header="t('vendite.dashboard_competenza.col_lotto')" style="width: 130px;">
              <template #body="{ data }">
                <Button
                  v-if="data.lotto_id"
                  link
                  class="app-cell-link"
                  :label="data.lotto_codice ?? String(data.lotto_id)"
                  v-tooltip.top="t('vendite.dashboard_competenza.apri_lotto')"
                  @click="apriLotto(data.lotto_id)"
                />
                <span v-else>{{ data.lotto_codice ?? '—' }}</span>
              </template>
            </Column>
            <Column field="fattura_numero" :header="t('vendite.dashboard_competenza.col_fattura')" style="width: 110px;">
              <template #body="{ data }">
                {{ fatturaDisplay(data) }}
              </template>
            </Column>
            <Column field="error_code" :header="t('vendite.dashboard_competenza.col_codice_errore')" style="width: 170px;">
              <template #body="{ data }">
                {{ data.error_code ?? data.task_code ?? '—' }}
              </template>
            </Column>
            <Column field="messaggio" :header="t('vendite.dashboard_competenza.col_messaggio')">
              <template #body="{ data }">
                {{ data.messaggio ?? '—' }}
              </template>
            </Column>
            <Column field="data_evento" :header="t('vendite.dashboard_competenza.col_data_evento')" style="width: 150px;">
              <template #body="{ data }">
                {{ data.data_evento ? displayTimestamp(data.data_evento) : '—' }}
              </template>
            </Column>
          </DataTable>
        </div>

        <!-- Drill-down per COMMESSA in pagina (click su card stadio, DEC-4):
             una riga per commessa; il dettaglio a grana attivita' e' nel
             drawer di gestione (kebab «Apri commessa»). -->
        <div ref="commesseSection" class="app-dash-fermi">
          <template v-if="stadioSelezionato">
            <div class="app-page-toolbar">
              <h4 class="app-dash-fermi-title">
                {{ t('vendite.dashboard_competenza.commesse_titolo', { stadio: stadioSelezionatoLabel }) }}
              </h4>
              <label class="app-dash-filter-toggle">
                <Checkbox v-model="soloRitardo" binary @change="onSoloRitardoChange" />
                {{ t('vendite.dashboard_competenza.solo_ritardo') }}
              </label>
            </div>
            <DataTable
              v-if="commesseCount > 0 || commesseLoading"
              :value="commesse"
              :loading="commesseLoading"
              :total-records="commesseCount"
              :rows="commessePageSize"
              :first="(commessePage - 1) * commessePageSize"
              paginator
              paginator-position="top"
              lazy
              :rows-per-page-options="PAGINATION.ROWS_OPTIONS"
              :sort-field="commesseOrderBy"
              :sort-order="commesseSortOrder"
              class="app-datatable app-datatable--inner"
              striped-rows
              data-key="commessa_id"
              @page="onCommessePage"
              @sort="onCommesseSort"
            >
              <Column field="commessa_codice" :header="t('vendite.dashboard_competenza.col_commessa')" sortable style="width: 140px;">
                <template #body="{ data }">
                  {{ data.commessa_codice ?? `#${data.commessa_id}` }}
                </template>
              </Column>
              <Column field="cliente_display" :header="t('vendite.dashboard_competenza.col_cliente')" sortable>
                <template #body="{ data }">
                  {{ data.cliente_display ?? '—' }}
                </template>
              </Column>
              <Column field="n_attivita" :header="t('vendite.dashboard_competenza.col_n_attivita')" sortable style="width: 100px;">
                <template #body="{ data }">
                  <Tag :value="String(data.n_attivita)" severity="secondary" v-tooltip.bottom="t('vendite.dashboard_competenza.n_attivita_tooltip', { n: data.n_attivita })" />
                </template>
              </Column>
              <Column field="valore_tot" :header="t('vendite.dashboard_competenza.col_valore')" sortable style="width: 130px;">
                <template #body="{ data }">
                  {{ data.valore_tot !== null ? formatCurrency(data.valore_tot) : '—' }}
                </template>
              </Column>
              <Column field="valore_fatturato_tot" :header="t('vendite.dashboard_competenza.col_fatturato')" style="width: 130px;">
                <template #body="{ data }">
                  {{ data.valore_fatturato_tot !== null ? formatCurrency(data.valore_fatturato_tot) : '—' }}
                </template>
              </Column>
              <Column field="data_attivita_max" :header="t('vendite.dashboard_competenza.col_periodo')" sortable style="width: 150px;">
                <template #body="{ data }">
                  <span v-if="data.data_attivita_min">
                    {{ displayDate(data.data_attivita_min) }}<template v-if="data.data_attivita_max && data.data_attivita_max !== data.data_attivita_min"> – {{ displayDate(data.data_attivita_max) }}</template>
                  </span>
                  <span v-else>—</span>
                </template>
              </Column>
              <Column field="n_in_ritardo" :header="t('vendite.dashboard_competenza.col_ritardo')" style="width: 90px;">
                <template #body="{ data }">
                  <span v-if="data.n_in_ritardo > 0" class="app-dash-ritardo">
                    <i class="pi pi-clock" /> {{ data.n_in_ritardo }}
                  </span>
                  <span v-else>—</span>
                </template>
              </Column>
              <!-- Azioni riga (Fase A cockpit): Approva (solo DA_APPROVARE, l'intera
                   commessa) + Apri commessa (drawer col dettaglio attivita'). -->
              <Column :header="t('vendite.dashboard_competenza.col_azioni')" class="app-col-actions" :exportable="false">
                <template #body="{ data }">
                  <RowActionsMenu :row="data" :actions="buildCommessaRowActions(data)" />
                </template>
              </Column>
            </DataTable>
            <div v-else class="app-empty-state">
              <i class="pi pi-check-circle" />
              <p>{{ t('vendite.dashboard_competenza.nessuna_commessa') }}</p>
            </div>
          </template>
          <div v-else class="app-empty-state">
            <i class="pi pi-chart-pie" />
            <p>{{ t('vendite.dashboard_competenza.commesse_hint') }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Drawer di governo commessa (A-4): riapprovvigiona la dashboard al save. -->
    <CommessaGestioneDrawer
      v-model:visible="commessaDrawerVisible"
      :commessa-id="commessaDrawerId"
      @saved="reloadDopoAzione"
    />

    <!-- Drawer diagnostico lotto (B-5): agganciato dal pannello errori. Un
         @changed (es. ristampa/reset dal drawer) riallinea aggregata+errori. -->
    <LottoDrawer
      v-model:visible="lottoDrawerVisible"
      :lotto-id="lottoDrawerId"
      @changed="reloadDopoAzione"
    />
  </div>
</template>
