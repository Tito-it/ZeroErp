<script setup>
// Scopo: Lente 2 Backlog — cosa e' fermo a monte della commessa, da quanto e
//        cosa serve per sbloccarlo (brief-design-fatturazione-due-lenti §5,
//        Fase 2 FE). Asse = anzianita' + azionabilita', NON la competenza:
//        niente calendario mesi. Dati reali da GET /vendite/dashboard-backlog/
//        (+ /documenti/) via store Pinia; classi, motivi e ordinamento vivono
//        nel DB/BE (vw_dash_backlog_* + config.motivi_fermo): la view rende.
//        Layout: contatori per classe (card cliccabili = filtro) + filtro
//        area + lista per anzianita' con motivo/azione/stato.
import { computed, onActivated, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import DashEmptyState from '../../core/components/DashEmptyState.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
import { exportDashboardBacklogDocumenti } from '../api/dashboardBacklog'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { MANAGE_ICONS, READONLY_DOMAINS, STATUS_ICONS } from '../../core/constants'
import { extractApiError } from '../../core/utils/apiError'
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { classeBacklogSeverity } from '../../core/utils/severity'
import DocumentoDrawerHost from '../../core/components/DocumentoDrawerHost.vue'
import { useDocumentoDrawer } from '../../core/composables/useDocumentoDrawer'
import {
  buildApriDocumentoAction,
  DASH_AREE,
  dashAreaLabel,
  dashAreaSeverity,
  dashMotivoLabel,
} from '../dashboardAree'
import { useDashboardBacklogStore } from '../stores/dashboardBacklog'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useContrattoFiltriLocali } from '../../core/composables/useContrattoFiltriLocali'
import { misureOpzioni } from '../../core/misurePagina'
import { allineaMisuraConfig } from '../../core/allineaMisuraConfig'

const { t, te } = useI18n()
const notify = useNotify()

// Provider readonly di area: la lente e' consultazione pura, ma il provider
// mantiene il pattern standard (ReadonlyBadge nel suffix toolbar).
useReadonlyMode(READONLY_DOMAINS.VENDITE)

const store = useDashboardBacklogStore()
const {
  classeSelezionata,
  areaSelezionata,
  ritardoGiorni,
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

// Ref alla lista configurabile + prop paginator (lo stato di pagina vive nello
// store dashboard, non in useSearchTable: si compongono qui).
const listaRef = ref(null)
const documentiPaginatorOptions = computed(() => ({
  totalRecords: documentiCount.value,
  rows: documentiPageSize.value,
  first: (documentiPage.value - 1) * documentiPageSize.value,
  rowsPerPageOptions: misureOpzioni(),
}))

// Scopo: allinea la dimensione pagina a quella risolta dal BE quando la
//        misura della configurazione cambia (BB `allineaMisuraConfig`).
const misuraConfig = allineaMisuraConfig()
function onConfigLoaded(config) {
  const nuovoLimit = misuraConfig.daApplicare(config)
  if (nuovoLimit && nuovoLimit !== documentiPageSize.value) {
    documentiPageSize.value = nuovoLimit
    // ⚠️ Con un passo nuovo la pagina di prima non e' piu' la stessa.
    documentiPage.value = 1
    store.fetchDocumenti()
  }
}

// Scopo: decodifiche i18n con fallback al codice grezzo (fail-visible per
//        classi/motivi/aree future introdotte DB-side). Motivi e aree dai BB
//        condivisi di dashboardAree (gruppo dash_comune, riusato dalla
//        Situazione aperta); la classe e' vocabolario solo-Backlog.
function classeLabel(classe) {
  return labelOrCode(t, te, `vendite.dashboard_backlog.classe_${String(classe).toLowerCase()}`, classe)
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

// Totali per la card "Tutte" (le classi partizionano il backlog: la somma è il
// totale). Documenti + valore euro fermo complessivo, così la card di reset non
// resta scarna. Il valore euro è la somma dei valori-fermo di classe (le aree a
// soli conteggi contribuiscono 0 al valore, coerente con le card di classe).
const totaleDocumenti = computed(() =>
  cards.value.reduce((s, c) => s + c.nDocumenti, 0)
)
const totaleValore = computed(() =>
  cards.value.reduce((s, c) => s + c.valoreFermo, 0)
)

// Riepilogo PER AREA della classe selezionata: risponde alla domanda che ci si
// fa dopo aver scelto una classe — «30 documenti da recuperare: di COSA sono?».
// Prima si poteva scoprire solo provando le aree una per una nella tendina.
//
// ⚠️ Il dato non costa una chiamata: `vw_dash_backlog_riepilogo` è aggregata
// per **(classe, area)**, e il BE la consegna già pronta — ogni classe porta la
// propria ripartizione nell'array annidato `aree`. Il FE finora leggeva i soli
// totali di classe e lasciava `aree` inutilizzato: il dettaglio era già in
// mano, si poteva scoprire solo provando le aree una per una nella tendina.
//
// Con «tutte le classi» (`classeSelezionata === null`) si somma per area su
// tutte le classi; con una classe scelta si prende la sua sola ripartizione.
// Aree a zero ESCLUSE (decisione Tid 2026-08-17): un elenco di sei voci di cui
// quattro a zero è rumore, non informazione.
const riepilogoAree = computed(() => {
  const perArea = new Map()
  for (const r of classi.value) {
    if (classeSelezionata.value && r.classe !== classeSelezionata.value) continue
    for (const a of r.aree ?? []) {
      const n = Number(a.n_documenti ?? 0)
      if (!n) continue
      perArea.set(a.area, (perArea.get(a.area) ?? 0) + n)
    }
  }
  // Ordine del funnel (DASH_AREE), non alfabetico né per conteggio: la lente
  // racconta un percorso, e un ordine che cambia a ogni click è illeggibile.
  return DASH_AREE
    .filter((area) => perArea.has(area))
    .map((area) => ({ area, label: areaLabel(area), nDocumenti: perArea.get(area) }))
})

// Scopo: click su una voce del riepilogo = filtro area, sullo STESSO stato
//        della tendina (`areaSelezionata`): due comandi, una sola verità.
//        Ri-cliccare l'area già attiva la azzera — senza, per tornare a
//        «tutte» si dovrebbe passare per la tendina.
function selezionaArea(area) {
  areaSelezionata.value = areaSelezionata.value === area ? null : area
  onAreaChange()
}

// Opzioni filtro area (tutte + 5 aree funnel dal BB condiviso, label
// condivise con la 5-card).
const areaOptions = computed(() => [
  { value: null, label: t('vendite.dashboard_backlog.filtro_area_tutte') },
  ...DASH_AREE.map((area) => ({ value: area, label: areaLabel(area) })),
])

// Opzioni filtro "fermo da oltre N giorni" (stessa scala della Situazione
// aperta): null = nessuna soglia. Filtra solo la lista, non le card.
const ritardoOptions = computed(() => [
  { value: null, label: t('vendite.dashboard_backlog.ritardo_tutti') },
  { value: 30, label: t('vendite.dashboard_backlog.ritardo_30') },
  { value: 60, label: t('vendite.dashboard_backlog.ritardo_60') },
  { value: 90, label: t('vendite.dashboard_backlog.ritardo_90') },
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

// Scopo: click su card classe = SELEZIONE (non toggle). Un secondo click sulla
//        stessa card la lascia selezionata: prima il toggle-off la deselezionava
//        e la lista si rimescolava con tutte le classi (un doppio-click bastava a
//        perdere il filtro). Il ritorno a "tutte" ha ora la sua card dedicata
//        (`classe === null`). Idempotente: stessa classe = no-op (niente refetch).
function selezionaClasse(classe) {
  if (classeSelezionata.value === classe) return
  classeSelezionata.value = classe
  store.resetDocumenti()
  loadDocumenti()
}

// Scopo: cambio filtro area (riparte da pagina 1).
function onAreaChange() {
  store.resetDocumenti()
  loadDocumenti()
}

// Scopo: cambio filtro "fermo da oltre N giorni" (riparte da pagina 1).
function onRitardoChange() {
  store.resetDocumenti()
  loadDocumenti()
}

// Scopo: il contratto dei filtri della barra — chi sono, che default hanno, il
//        segno che mostrano e «Pulisci filtri». UNA sede: chiave, `rif` e
//        default sulla stessa riga.
// ⛔ Il default si DICHIARA e non si fotografa dal `ref`: questi due filtri
//    vivono nello store `userScoped` del cruscotto, che SOPRAVVIVE al
//    componente — al secondo montaggio una fotografia avrebbe preso il filtro
//    lasciato dall'operatore come se fosse il default.
// ⚠️ I due nascono entrambi a `null`, quindi qui il numero grigio non compare
//    mai: o non filtrano, o sono stati scelti a mano (numero blu).
// ⛔ Non c'e' la CLASSE: quella si sceglie dalle card, che restano sempre a
//    video — il segno esiste per cio' che in modalita' compatta non si vede piu'.
const {
  segno: segnoFiltriCruscotto,
  azzeraFiltri: pulisciFiltri,
} = useContrattoFiltriLocali({
  ritardo_giorni: { rif: ritardoGiorni, default: null },
  area: { rif: areaSelezionata, default: null },
}, {
  onAzzera: () => {
    store.resetDocumenti()
    loadDocumenti()
  },
})

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

// Drawer di dettaglio del documento di riga: stato nel BB condiviso, host
// montato in fondo alla view. La lista e' cross-area (incluse le COMMESSE,
// che non hanno una view lista): il registry risolve area -> drawer. Alla
// chiusura si ricarica la lente: sbloccare il documento dal drawer e' proprio
// lo scopo del Backlog, la riga appena lavorata non deve restare stantia.
const {
  visible: docDrawerVisible,
  tipo: docDrawerTipo,
  id: docDrawerId,
  apri: apriDocumento,
  onVisibleChange: onDocDrawerVisible,
} = useDocumentoDrawer(() => {
  loadRiepilogo()
  loadDocumenti()
})

// Azioni riga: "apri documento" via BB condiviso — apre il drawer di gestione
// del documento per id, senza lasciare il cruscotto.
function buildRowActions(data) {
  return [
    buildApriDocumentoAction({
      area: data.area,
      documentoId: data.documento_id,
      label: t('vendite.dashboard_backlog.apri_documento'),
      onApri: apriDocumento,
    }),
  ]
}

// Azioni di lista (personalizza colonne + esporta): BB condiviso con le altre
// liste configurabili. L'export riceve gli STESSI filtri e lo STESSO
// ordinamento della lista a video — il file e' la lista, non una seconda query.
const {
  dirty, exportDialogVisible, exportLoading, onExportConfirm, azioniLista,
} = useListaAzioni(() => listaRef.value, {
  exportFn: exportDashboardBacklogDocumenti,
  getExportParams: (formato) => ({
    formato,
    classe: classeSelezionata.value,
    area: areaSelezionata.value,
    ritardo_giorni: ritardoGiorni.value,
    order_by: orderBy.value,
    order_dir: orderDir.value,
  }),
})

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
  ...azioniLista.value,
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
      <div class="app-page-toolbar-start">
        <h2 style="margin: 0;">{{ t('vendite.dashboard_backlog.page_title') }}</h2>
        <small class="app-text-muted">{{ t('vendite.dashboard_backlog.page_description') }}</small>
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <!-- `--scorrimento-unico`: card e lista sono UNA cosa sola che
         scorre, come nella Lente Competenza — le card salgono
         insieme alle righe invece di lasciare la lista incastrata
         in un riquadro con una barra sua. -->
    <div class="app-dash-main app-dash-main--scorrimento-unico">
      <!-- Contatori per classe di azionabilita' (card = filtro, selezione
           esclusiva). La card "Tutte" azzera il filtro classe. -->
      <div class="app-dash-cards">
        <div
          class="app-dash-card"
          :class="{ 'is-selected': classeSelezionata === null }"
          role="button"
          tabindex="0"
          @click="selezionaClasse(null)"
          @keydown.enter="selezionaClasse(null)"
        >
          <Tag :value="t('vendite.dashboard_backlog.filtro_classe_tutte')" severity="secondary" />
          <span class="app-dash-stat-n">{{ totaleDocumenti }}</span>
          <span class="app-dash-stat-sub">{{ t('vendite.dashboard_backlog.n_documenti') }}</span>
          <span v-if="totaleValore > 0" class="app-dash-stat-euro">
            {{ formatCurrency(totaleValore) }}
          </span>
        </div>
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
          <span class="app-dash-stat-sub">{{ t('vendite.dashboard_backlog.n_documenti') }}</span>
          <span v-if="card.valoreFermo > 0" class="app-dash-stat-euro">
            {{ formatCurrency(card.valoreFermo) }}
          </span>
          <!-- Aree a conteggi (offerte/contratti): unita' al posto del valore. -->
          <span v-if="card.unitaFerme > 0" class="app-dash-stat-sub">
            {{ t('vendite.dashboard_backlog.unita_ferme', { n: card.unitaFerme }) }}
          </span>
          <span v-if="card.anzianitaMax > 0" class="app-dash-ritardo">
            <i :class="STATUS_ICONS.IN_RITARDO" />
            {{ t('vendite.dashboard_backlog.anzianita_max', { n: card.anzianitaMax }) }}
          </span>
        </div>
      </div>

      <!-- Ripartizione per AREA della classe selezionata: dice DI COSA sono i
           documenti contati dalla card sopra. Ogni voce è un filtro (stesso
           stato della tendina); le aree a zero non compaiono. Solo conteggi,
           mai importi: offerte, contratti e resi vanno a conteggi per
           decisione (DL-11, DL-24) e un «€ 0» accanto sarebbe falso. -->
      <div v-if="riepilogoAree.length" class="app-dash-chips">
        <span
          v-for="v in riepilogoAree"
          :key="v.area"
          class="app-dash-chip"
          :class="{ 'is-selected': areaSelezionata === v.area }"
          role="button"
          tabindex="0"
          @click="selezionaArea(v.area)"
          @keydown.enter="selezionaArea(v.area)"
        >
          {{ v.label }}
          <strong>{{ v.nDocumenti }}</strong>
        </span>
      </div>

      <!-- Lista per anzianita' con filtro area. Niente data-key: la union e'
           cross-area e documento_uid si ripete per i contratti mese-esplosi
           (nessuna chiave riga univoca disponibile). -->
      <div class="app-dash-fermi">
        <div class="app-page-toolbar">
          <h4 class="app-dash-fermi-title">
            {{ t('vendite.dashboard_backlog.lista_titolo') }}
          </h4>
          <!-- ⚠️ `:segno` e non `:store`: un cruscotto non ha uno store-LISTA —
               i suoi filtri sono ref sciolte, non un oggetto `filters` con i
               propri default. E' il ripiego dichiarato dal brief per le
               superfici senza store, e resta l'unica sede del conteggio.
               ⛔ `classeSelezionata` NON ci entra: si sceglie dalle card, che
               sono sempre a video — il segno esiste per cio' che, in modalita'
               compatta, non si vede piu'. -->
          <FiltriLista :segno="segnoFiltriCruscotto" @pulisci="pulisciFiltri">
            <label class="app-dash-filter-toggle">
              <span>{{ t('vendite.dashboard_backlog.filtro_ritardo_label') }}</span>
              <Select
                v-model="ritardoGiorni"
                class="app-filter-w-sm"
                :options="ritardoOptions"
                option-label="label"
                option-value="value"
                :placeholder="t('vendite.dashboard_backlog.ritardo_tutti')"
                size="small"
                @change="onRitardoChange"
              />
            </label>
            <Select
              v-model="areaSelezionata"
              class="app-filter-w-md"
              :options="areaOptions"
              option-label="label"
              option-value="value"
              :placeholder="t('vendite.dashboard_backlog.filtro_area_tutte')"
              size="small"
              @change="onAreaChange"
            />
          </FiltriLista>
        </div>
        <ListaConfigurabile
          v-if="documentiCount > 0 || documentiLoading"
          ref="listaRef"
          codice="vendite.dash_backlog_documenti"
          data-key="documento_id"
          :rows="documenti"
          :total="documentiCount"
          :loading="documentiLoading"
          :paginator-options="documentiPaginatorOptions"
          :page="documentiPage"
          :sort-field="orderBy"
          :sort-order="documentiSortOrder"
          @page="onDocumentiPage"
          @sort="onDocumentiSort"
          @config-loaded="onConfigLoaded"
        >
          <template #cell-anzianita_giorni="{ data }">
            <span
              class="app-dash-ritardo"
              v-tooltip.bottom="data.data_riferimento ? displayDate(data.data_riferimento) : ''"
            >
              {{ data.anzianita_giorni !== null
                ? t('vendite.dashboard_backlog.fermo_da_giorni', { n: data.anzianita_giorni })
                : '—' }}
            </span>
          </template>
          <template #cell-classe="{ data }">
            <Tag :value="classeLabel(data.classe)" :severity="classeBacklogSeverity(data.classe)" />
          </template>
          <template #cell-area="{ data }">
            {{ areaLabel(data.area) }}
          </template>
          <template #cell-codice="{ data }">
            {{ data.codice ?? '—' }}
          </template>
          <template #cell-cliente_display="{ data }">
            {{ data.cliente_display ?? '—' }}
          </template>
          <!-- valore_fermo non ha slot: il seed dichiara `currency_eur`. -->
          <template #cell-unita_ferme="{ data }">
            {{ data.unita_ferme ?? '—' }}
          </template>
          <template #cell-motivo_fermo="{ data }">
            {{ motivoLabel(data.motivo_fermo) }}
          </template>
          <template #cell-azione="{ data }">
            {{ data.azione ?? '—' }}
          </template>
          <template #cell-stato_codice="{ data }">
            <Tag :value="data.stato_codice ?? '—'" :severity="statoSeverity(data)" />
          </template>

          <template #actions="{ data }">
            <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
          </template>
        </ListaConfigurabile>
        <DashEmptyState
          v-else
          :loaded="documentiLoaded"
          :empty-text="t('vendite.dashboard_backlog.nessun_documento')"
          :placeholder-text="t('vendite.dashboard_backlog.non_caricato')"
        />
      </div>
    </div>

    <!-- Host cross-dominio: apre il drawer di gestione del documento della
         riga (stesso meccanismo delle tappe "Passaggi"), senza uscire dalla
         lente. -->
    <DocumentoDrawerHost
      :visible="docDrawerVisible"
      :tipo-codice="docDrawerTipo"
      :doc-id="docDrawerId"
      @update:visible="onDocDrawerVisible" />

    <!-- Scelta formato export (CSV/XLSX): il file copia la lista a video,
         filtri e ordinamento compresi. -->
    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />
  </div>
</template>
