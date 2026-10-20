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
import { computed, onActivated, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import DashEmptyState from '../../core/components/DashEmptyState.vue'
import DonutFasi from '../../core/components/charts/DonutFasi.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
import { exportDashboardApertoDocumenti } from '../api/dashboardAperto'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { MANAGE_ICONS, READONLY_DOMAINS, STATUS_ICONS } from '../../core/constants'
import { extractApiError } from '../../core/utils/apiError'
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { faseDocumentoSeverity } from '../../core/utils/severity'
import DocumentoDrawerHost from '../../core/components/DocumentoDrawerHost.vue'
import { DOCUMENTO_DRAWER_TIPI } from '../../core/drawerEntita'
import { useDocumentoDrawer } from '../../core/composables/useDocumentoDrawer'
import {
  DASH_AREA_CONFIG,
  buildApriDocumentoAction,
  dashAreaLabel,
  dashAreaSeverity,
  dashFaseLabel,
  dashMotivoLabel,
} from '../dashboardAree'
import { useDashboardApertoStore } from '../stores/dashboardAperto'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useContrattoFiltriLocali } from '../../core/composables/useContrattoFiltriLocali'
import { misureOpzioni } from '../../core/misurePagina'

const { t, te } = useI18n()
const notify = useNotify()

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

// Ref alla lista configurabile + prop paginator: la view non usa
// useSearchTable (lo stato di pagina vive nello store dashboard), quindi le
// compone qui con quello che gia' possiede.
const listaRef = ref(null)
const documentiPaginatorOptions = computed(() => ({
  totalRecords: documentiCount.value,
  rows: documentiPageSize.value,
  first: (documentiPage.value - 1) * documentiPageSize.value,
  rowsPerPageOptions: misureOpzioni(),
}))

// Scopo: allinea una volta la dimensione pagina a quella risolta dal BE.
const configAllineata = ref(false)
function onConfigLoaded(config) {
  if (configAllineata.value) return
  configAllineata.value = true
  const nuovoLimit = config?.pagina_dimensione
  if (nuovoLimit && nuovoLimit !== documentiPageSize.value) {
    documentiPageSize.value = nuovoLimit
    store.fetchDocumenti()
  }
}

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
      // Hint per misure non ovvie (es. ORDINE_VENDITA misura mista, DL-23): la
      // mappatura area→hint vive in DASH_AREA_CONFIG con route/severity,
      // non qui — la view non conosce le aree per nome.
      hint: DASH_AREA_CONFIG[a.area]?.apertoHintKey
        ? t(DASH_AREA_CONFIG[a.area].apertoHintKey)
        : null,
    }
  })
)

// Totali per la card "Tutte le aree" (altrimenti troppo scarna vs le card
// donut): valore euro complessivo (somma dei valori-area delle aree a euro) +
// i conteggi delle due aree a soli numeri più significative (offerte, contratti).
// Ogni area espone già n_documenti e valore_totale a livello area (BE
// fn_dash_aperto_riepilogo): qui solo aggregazione, nessuna seconda fonte.
const totaliAperto = computed(() => {
  let euro = 0
  let offerte = 0
  let contratti = 0
  for (const a of aree.value) {
    if (a.valore_totale !== null && a.valore_totale !== undefined) {
      euro += Number(a.valore_totale)
    }
    if (a.area === DOCUMENTO_DRAWER_TIPI.OFFERTA_COMMERCIALE) offerte = a.n_documenti ?? 0
    if (a.area === DOCUMENTO_DRAWER_TIPI.CONTRATTO) contratti = a.n_documenti ?? 0
  }
  return { euro, offerte, contratti }
})

// Opzioni filtro fase: dal vocabolario top-level servito dal riepilogo BE
// (3 fasi vive sempre presenti + eventuali future accodate fail-visible) —
// nessuna copia FE del vocabolario config.stati_doc_*.
const faseOptions = computed(() => [
  { value: null, label: t('vendite.situazione_aperta.filtro_fase_tutte') },
  ...fasi.value.map((f) => ({ value: f, label: faseLabel(f) })),
])

// Opzioni filtro "aperti da oltre N giorni" (DL-17): soglia su data documento,
// solo sulla lista. null = nessuna soglia (drill-down completo).
const ritardoOptions = computed(() => [
  { value: null, label: t('vendite.situazione_aperta.ritardo_tutti') },
  { value: 30, label: t('vendite.situazione_aperta.ritardo_30') },
  { value: 60, label: t('vendite.situazione_aperta.ritardo_60') },
  { value: 90, label: t('vendite.situazione_aperta.ritardo_90') },
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

// Scopo: il contratto dei filtri della barra — chi sono, che default hanno, il
//        segno che mostrano e «Pulisci filtri». UNA sede: chiave, `rif` e
//        default sulla stessa riga.
// ⛔ Il default si DICHIARA e non si fotografa dal `ref`: questi due filtri
//    vivono nello store `userScoped` del cruscotto, che SOPRAVVIVE al
//    componente — al secondo montaggio una fotografia avrebbe preso il filtro
//    lasciato dall'operatore come se fosse il default.
// ⚠️ I due nascono entrambi a `null`, quindi il numero grigio non compare mai:
//    o non filtrano, o sono stati scelti a mano (numero blu).
// ⛔ Non c'e' l'AREA: quella si sceglie dalle card, che restano sempre a video
//    — il segno esiste per cio' che in modalita' compatta non si vede piu'.
const {
  segno: segnoFiltriCruscotto,
  azzeraFiltri: pulisciFiltri,
} = useContrattoFiltriLocali({
  ritardo_giorni: { rif: ritardoGiorni, default: null },
  fase: { rif: faseSelezionata, default: null },
}, { onAzzera: () => onFiltriChange() })

// Scopo: click sul corpo della card = livello AREA (nessuna fase), SELEZIONE
//        esclusiva (non piu' toggle: un secondo click sulla stessa area non la
//        deseleziona piu', evitando che la lista si rimescolasse con tutte le
//        aree). Il ritorno a "tutte" ha la sua card dedicata (`area === null`).
//        Se sull'area c'e' gia' una fase attiva (drill-down da legenda), il
//        click sul corpo la rimuove tornando a "tutta l'area".
function selezionaArea(area) {
  // Card "Tutte le aree": azzera area + fase. No-op se gia' su "tutte".
  if (area === null) {
    if (areaSelezionata.value === null && faseSelezionata.value === null) return
    areaSelezionata.value = null
    faseSelezionata.value = null
    onFiltriChange()
    return
  }
  // Stessa area con fase attiva: torna a "tutta l'area" (azzera solo la fase).
  if (areaSelezionata.value === area && faseSelezionata.value !== null) {
    faseSelezionata.value = null
    onFiltriChange()
    return
  }
  // Stessa area senza fase = no-op (niente toggle-off, niente refetch).
  if (areaSelezionata.value === area) return
  // Area diversa: selezione esclusiva, fase azzerata.
  areaSelezionata.value = area
  faseSelezionata.value = null
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

// Drawer di dettaglio del documento di riga: stato nel BB condiviso, host
// montato in fondo alla view. La lista e' cross-area: il registry risolve
// area -> drawer (DASH_AREA_CONFIG.drawerTipo). Alla chiusura si ricarica il
// cruscotto: nel drawer il documento puo' essere avanzato (e magari uscito
// dal perimetro aperti-non-chiusi).
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
      label: t('vendite.situazione_aperta.apri_documento'),
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
  exportFn: exportDashboardApertoDocumenti,
  getExportParams: (formato) => ({
    formato,
    area: areaSelezionata.value,
    fase: faseSelezionata.value,
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
      <div class="app-page-toolbar-start">
        <h2 style="margin: 0;">{{ t('vendite.situazione_aperta.page_title') }}</h2>
        <small class="app-text-muted">{{ t('vendite.situazione_aperta.page_description') }}</small>
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
      <!-- Card per area (click = filtro, selezione esclusiva): donut per fase.
           La card "Tutte le aree" azzera il filtro area. -->
      <div class="app-dash-cards">
        <div
          class="app-dash-card app-dash-card--reset"
          :class="{ 'is-selected': areaSelezionata === null }"
          role="button"
          tabindex="0"
          @click="selezionaArea(null)"
          @keydown.enter="selezionaArea(null)"
        >
          <span class="app-dash-card-title">{{ t('vendite.situazione_aperta.filtro_area_tutte') }}</span>
          <span v-if="totaliAperto.euro > 0" class="app-dash-stat-euro">
            {{ formatCurrency(totaliAperto.euro) }}
          </span>
          <span class="app-dash-stat-sub">
            {{ areaLabel(DOCUMENTO_DRAWER_TIPI.OFFERTA_COMMERCIALE) }}: {{ totaliAperto.offerte }}
            · {{ areaLabel(DOCUMENTO_DRAWER_TIPI.CONTRATTO) }}: {{ totaliAperto.contratti }}
          </span>
        </div>
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
              class="app-dash-card-hint" :class="STATUS_ICONS.INFO"
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
            {{ t('vendite.situazione_aperta.lista_titolo') }}
          </h4>
          <!-- ⚠️ `:segno` e non `:store`: un cruscotto non ha uno store-LISTA —
               i suoi filtri sono ref sciolte, non un oggetto `filters` coi
               propri default. E' il ripiego dichiarato dal brief per le
               superfici senza store.
               ⛔ `areaSelezionata` NON ci entra: si sceglie dalle card, che sono
               sempre a video. -->
          <FiltriLista :segno="segnoFiltriCruscotto" @pulisci="pulisciFiltri">
            <label class="app-dash-filter-toggle">
              <span>{{ t('vendite.situazione_aperta.filtro_ritardo_label') }}</span>
              <Select
                v-model="ritardoGiorni"
                class="app-filter-w-sm"
                :options="ritardoOptions"
                option-label="label"
                option-value="value"
                :placeholder="t('vendite.situazione_aperta.ritardo_tutti')"
                size="small"
                @change="onFiltriChange"
              />
            </label>
            <Select
              v-model="faseSelezionata"
              class="app-filter-w-md"
              :options="faseOptions"
              option-label="label"
              option-value="value"
              :placeholder="t('vendite.situazione_aperta.filtro_fase_tutte')"
              size="small"
              @change="onFiltriChange"
            />
          </FiltriLista>
        </div>
        <ListaConfigurabile
          v-if="documentiCount > 0 || documentiLoading"
          ref="listaRef"
          codice="vendite.dash_aperto_documenti"
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
                ? t('vendite.situazione_aperta.aperto_da_giorni', { n: data.anzianita_giorni })
                : '—' }}
            </span>
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
          <template #cell-fase="{ data }">
            <Tag
              v-if="data.fase"
              :value="faseLabel(data.fase)"
              :severity="faseDocumentoSeverity(data.fase)"
            />
            <span v-else>—</span>
          </template>
          <template #cell-stato_codice="{ data }">
            <Tag :value="data.stato_codice ?? '—'" :severity="statoSeverity(data)" />
          </template>
          <!-- valore_totale non ha slot: il seed dichiara `currency_eur`. -->
          <template #cell-unita_totali="{ data }">
            {{ data.unita_totali ?? '—' }}
          </template>
          <template #cell-motivo_fermo="{ data }">
            {{ data.motivo_fermo ? motivoLabel(data.motivo_fermo) : '—' }}
          </template>

          <template #actions="{ data }">
            <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
          </template>
        </ListaConfigurabile>
        <DashEmptyState
          v-else
          :loaded="documentiLoaded"
          :empty-text="t('vendite.situazione_aperta.nessun_documento')"
          :placeholder-text="t('vendite.situazione_aperta.non_caricato')"
        />
      </div>
    </div>

    <!-- Host cross-dominio: apre il drawer di gestione del documento della
         riga (stesso meccanismo delle tappe "Passaggi"), senza uscire dal
         cruscotto. -->
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
