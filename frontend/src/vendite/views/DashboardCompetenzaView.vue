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
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
import {
  exportDashboardCompetenzaCommesse,
  exportDashboardCompetenzaErrori,
  exportDashboardCompetenzaGruppi,
} from '../api/dashboardCompetenza'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import DashMesiSidebar from '../../core/components/dash/DashMesiSidebar.vue'
import DashMeseStepper from '../../core/components/dash/DashMeseStepper.vue'
import DonutTransito from '../../core/components/charts/DonutTransito.vue'
import Button from 'primevue/button'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import CommessaGestioneDrawer from '../components/CommessaGestioneDrawer.vue'
import DocumentoDrawerHost from '../_shared/documenti/DocumentoDrawerHost.vue'
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
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { statoDocFiscaleSeverity } from '../../core/utils/severity'
import { approvaCompetenza } from '../api/commesse'
import { getFatturazioneRun, runFatturazione, runNumerazione } from '../api/lotti'
import { useDocumentoDrawer } from '../_shared/documenti/useDocumentoDrawer'
import { buildApriDocumentoAction } from '../dashboardAree'
import { useSelezioneToggle } from '../_shared/righe/useSelezioneToggle'
import { STADIO_GRUPPI, useDashboardCompetenzaStore } from '../stores/dashboardCompetenza'

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
  gruppi,
  gruppiCount,
  gruppiPage,
  gruppiPageSize,
  gruppiLoading,
  gruppiLoaded,
  gruppiOrderBy,
  gruppiOrderDir,
  gruppiRiepilogo,
  gruppiTipo,
  gruppiTipi,
  errori,
  erroriCount,
  erroriPage,
  erroriPageSize,
  erroriOrderBy,
  erroriOrderDir,
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
    // La selezione e i lotti prodotti vivono nella view, non nello store:
    // vanno azzerati QUI e non solo in selezionaStadio, altrimenti restano
    // agganciati a un mese che non e' piu' quello a video — e basterebbe un
    // percorso futuro che riapre la lista senza passare da selezionaStadio
    // per fatturare, col mese nuovo, i gruppi del mese vecchio.
    azzeraStatoGruppi()
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
    // Seconda misura: quante FATTURE. `?? null` e NON `?? 0`: dove il numero
    // non c'e', dire «0 fatture» sarebbe un'affermazione, e falsa.
    nFatture: cella.n_fatture ?? null,
    // ...e il PERCHE' non c'e', che il FE non deve dedurre: `NON_APPLICABILE`
    // (per progetto: «Da emettere» non ha ancora una chiave documento) fa
    // tacere la card, `ERRORE` le fa mostrare un avvertimento. Erano
    // indistinguibili fino al 2026-08-03, e un guasto aveva percio' lo stesso
    // aspetto del funzionamento normale.
    nFattureStato: cella.n_fatture_stato ?? 'NON_APPLICABILE',
    valoreDisplay: Number(cella.valore_display ?? 0),
    nInRitardo: cella.n_in_ritardo ?? 0,
    statiFattura: cella.stati_fattura ?? [],
  }))
})

// Scopo: chiarimento sulla MISURA della card, quando il numero non dice cio'
//        che sembra dire. Oggi solo «Da emettere», che e' la card azionabile:
//        li' il conteggio guida una decisione (premere «Fattura»), e chi lo
//        legge come «quante fatture nasceranno» sbaglia in due modi opposti —
//        un articolo COMPOSITO produce un'attivita' per componente (3 righe da
//        una riga d'ordine), e all'inverso piu' attivita' confluiscono nella
//        STESSA fattura per via dell'aggregazione. Nel caso reale che ha fatto
//        nascere questo hint: 3 attivita' -> 1 gruppo -> 1 fattura.
//        Chiave i18n condizionale (`te`): una card senza spiegazione non
//        mostra l'icona, invece di mostrarla vuota.
function cardHint(stadio) {
  const key = `vendite.dashboard_competenza.card_hint_${String(stadio).toLowerCase()}`
  return te(key) ? t(key) : null
}

// Difetto D2 (§6-bis, corretto 2026-07-27): il verbo «Rendi definitive» stava
// sulla card EMESSA_NON_FATTURATA, ma numera i LOTTI IN STATO EMESSA, cioe'
// fatture gia' create — che nel funnel stanno in FATTURATA con
// `stato_fattura_codice_interno = 'EMESSA'` (vedi il CASE di
// vw_dash_competenza_attivita: FATTURATA = riga con fattura_riga_id).
// Conseguenza del difetto: a mese tutto fatturato la card residui va a 0 e il
// pulsante SPARIVA proprio quando serviva numerare, e compariva quando non
// c'era nulla da numerare. Qui la condizione e' il dato vero: esistono
// attivita' fatturate la cui fattura e' ancora EMESSA.
const nDaNumerare = computed(() => {
  const fatturate = cards.value.find((c) => c.stadio === 'FATTURATA')
  if (!fatturate) return 0
  return fatturate.statiFattura
    .filter((s) => s.stato_fattura_codice_interno === 'EMESSA')
    .reduce((acc, s) => acc + Number(s.n_attivita ?? 0), 0)
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

// Scopo: carica la pagina corrente dei gruppi fatturabili del mese (drill-down
//        della card «Da emettere»: l'unita' su cui si preme «Fattura»).
async function loadGruppi() {
  try {
    await store.fetchGruppi(competenzaCorrente.value)
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Il drill-down della card «Da emettere» scende sui GRUPPI FATTURABILI, quello
// delle altre card resta sulle commesse: ogni card scende sull'unita' del
// proprio verbo. Un solo punto di smistamento, cosi' non puo' capitare che una
// card carichi una lista e ne mostri un'altra.
function loadDrillDown() {
  return stadioSelezionato.value === STADIO_GRUPPI ? loadGruppi() : loadCommesse()
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
  azzeraStatoGruppi()
  stadioSelezionato.value = stadio
  loadDrillDown()
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

// ------------------------------------------------------- gruppi fatturabili (emissione mirata)
// Selezione multipla dei gruppi da fatturare. Le righe con TESTATA bloccata
// (`commessa_emittibile === false`, brief emittibilita' §3.1) restano in lista
// — «segnalare, non nascondere», decisione Tid — ma NON sono selezionabili:
// il motore non le fatturerebbe, e spuntarle prometterebbe un lotto che non
// nasce. Il BB fa il resto: `isSelectable` alimenta il :disabled della
// checkbox e il guard di toggleRow tiene la selezione coerente comunque.
function isGruppoEmittibile(row) {
  // NULL (gruppo senza commessa) non e' un blocco: decide il motore a valle.
  return row.commessa_emittibile !== false
}
const gruppiSelezionabili = computed(() => gruppi.value.filter(isGruppoEmittibile))

// Scopo: elenco leggibile in un toast/conferma — primi 3 per esteso, il resto
//        riassunto da «…». Stessa soglia del compositore BE
//        (_MAX_GRUPPI_NEL_MESSAGGIO): un toast non regge un elenco puntato.
function elencoTroncato(items, fmt, sep = ', ') {
  return items.slice(0, 3).map(fmt).join(sep) + (items.length > 3 ? '…' : '')
}

const selezioneGruppi = ref([])
const {
  isSelected: isGruppoSelezionato,
  toggleRow: toggleGruppo,
  allSelected: tuttiGruppiSelezionati,
} = useSelezioneToggle({
  selected: selezioneGruppi,
  selezionabili: gruppiSelezionabili,
  rowKey: 'gruppo_key',
})

// La selezione sopravvive alle pagine e ai reload DI PROPOSITO — ma una riga
// selezionata da emittibile puo' tornare BLOCCATA a un refresh (un collega
// riporta la commessa in BOZZA). Senza questo prune resterebbe spuntata con la
// checkbox disabilitata — il guard del BB rende il de-toggle un no-op — quindi
// non rimovibile, contata nel pulsante e ri-sottomessa a ogni giro. Il prune
// toglie dalla selezione le chiavi che la pagina fresca dichiara bloccate: la
// checkbox si spegne a video, che e' la comunicazione onesta.
watch(gruppi, (rows) => {
  const bloccate = new Set(
    (rows ?? []).filter((r) => !isGruppoEmittibile(r)).map((r) => r.gruppo_key),
  )
  if (!bloccate.size) return
  selezioneGruppi.value = selezioneGruppi.value.filter(
    (r) => !bloccate.has(r.gruppo_key),
  )
})

// ⚠️ `toggleAll`/`anySelected` del BB NON sono riusabili qui, ed e' il punto
// meno ovvio di questa lista. Il BB nasce per dialog a lista INTERA (evasione
// ordine, crea-reso): `toggleAll` fa `selected = [...selezionabili]`, cioe'
// SOSTITUISCE la selezione. Su una lista PAGINATA questo significa che
// spuntare «tutti» in pagina 2 butterebbe via quanto selezionato in pagina 1 —
// silenziosamente, e l'operatore se ne accorgerebbe solo dal conteggio del
// pulsante. Qui la selezione e' per chiave di dominio e vive attraverso le
// pagine, quindi il seleziona-tutto opera SOLO sulla pagina corrente,
// aggiungendo o togliendo e lasciando intatto il resto.
const chiaviPagina = computed(() => gruppiSelezionabili.value.map((r) => r.gruppo_key))

// Selezione parziale DELLA PAGINA (stato indeterminate della checkbox header).
const alcuniGruppiSelezionati = computed(
  () => !tuttiGruppiSelezionati.value
    && gruppiSelezionabili.value.some((r) => isGruppoSelezionato(r)),
)

// Il seleziona-tutto di pagina opera sulle sole righe SELEZIONABILI: le
// bloccate non entrano nemmeno dal toggle di massa.
function toggleTuttiGruppi() {
  if (tuttiGruppiSelezionati.value) {
    const daTogliere = new Set(chiaviPagina.value)
    selezioneGruppi.value = selezioneGruppi.value.filter(
      (r) => !daTogliere.has(r.gruppo_key),
    )
    return
  }
  const gia = new Set(selezioneGruppi.value.map((r) => r.gruppo_key))
  selezioneGruppi.value = [
    ...selezioneGruppi.value,
    ...gruppiSelezionabili.value.filter((r) => !gia.has(r.gruppo_key)),
  ]
}

// Lotti prodotti dall'ultima emissione mirata: sono N, non uno (un gruppo con
// righe di tipo doc fiscale diverso finisce in lotti diversi). Alimentano
// l'aggancio «vai al lotto» — senza, l'operatore dovrebbe cercarsi a mano nella
// lista lotti il contenitore appena creato per andare a numerarlo.
const lottiEmessi = ref([])

// Scopo: azzera lo stato di selezione/esito che vive nella view (lo store
//        azzera il suo). Dichiarata come `function` per essere invocabile dai
//        callback registrati piu' in alto (nessun watch immediate la chiama in
//        setup: `useDashMesiNav` scatta solo su azione utente).
function azzeraStatoGruppi() {
  selezioneGruppi.value = []
  lottiEmessi.value = []
}

const gruppiSortOrder = computed(() => (gruppiOrderDir.value === 'desc' ? -1 : 1))

// Scopo: paginazione DataTable gruppi. La selezione NON si azzera al cambio
//        pagina: le chiavi selezionate restano valide (sono chiavi di dominio,
//        non indici di riga) e l'operatore puo' comporre la selezione su piu'
//        pagine.
function onGruppiPage(event) {
  store.applyGruppiPage(event)
  loadGruppi()
}

function onGruppiSort(event) {
  store.applyGruppiSort(event)
  gruppiPage.value = 1
  loadGruppi()
}

// Opzioni del filtro «tipo documento/sorgente»: vengono dal BE (facet sui dati
// del perimetro), non da `config.sorgenti` — quella tabella offre sorgenti che
// non possono mai essere un gruppo fatturabile e NON contiene gli oneri di
// commessa, che sono proprio il caso che si vuole poter isolare.
// «Tutti» in testa con value null = filtro assente (non un valore speciale).
const opzioniTipoGruppo = computed(() => [
  {
    value: null,
    label: t('vendite.dashboard_competenza.tipo_tutti', {
      n: gruppiTipi.value.reduce((acc, x) => acc + Number(x.n_gruppi ?? 0), 0),
    }),
  },
  ...gruppiTipi.value.map((x) => ({
    value: x.tipo_gruppo,
    label: `${gruppoTipoLabel(x)} (${x.n_gruppi})`,
  })),
])

// Scopo: cambio del filtro tipo — riparte da pagina 1 (le pagine successive
//        appartengono al perimetro precedente) e azzera la selezione: le righe
//        selezionate potrebbero non essere piu' a video, e fatturare una
//        selezione invisibile e' esattamente il tipo di sorpresa da evitare.
function onGruppiTipoChange() {
  gruppiPage.value = 1
  selezioneGruppi.value = []
  loadGruppi()
}

// Scopo: etichetta del gruppo — riferimento leggibile del documento
//        (PRV-0012…) oppure, per gli oneri sourceless, la commessa che li
//        contiene. Il BE risolve gia' il riferimento: qui solo il fallback.
function gruppoRiferimento(row) {
  return row.riferimento || row.commessa_codice || row.gruppo_key
}

// Scopo: etichetta del TIPO di gruppo con decodifica i18n fail-visible: un
//        tipo nuovo introdotto DB-side si mostra col suo codice, non col path
//        della chiave mancante.
function gruppoTipoLabel(row) {
  return labelOrCode(
    t,
    te,
    `vendite.dashboard_competenza.tipo_gruppo.${String(row.tipo_gruppo).toLowerCase()}`,
    row.tipo_gruppo,
  )
}

// Scopo: paginazione DataTable errori (lazy, paginator top; calcolo
//        pagina nel BB usePagedDashFetch).
function onErroriPage(event) {
  store.applyErroriPage(event)
  loadErrori()
}

// Scopo: ordinamento server-side del pannello errori (il BE lo espone dal
//        2026-08-03: prima la lista non ordinava affatto).
function onErroriSort(event) {
  store.applyErroriSort(event)
  loadErrori()
}
const erroriSortOrder = computed(() => (erroriOrderDir.value === 'desc' ? -1 : 1))

// La union degli errori non ha una PK (il tiebreak lato BE e' una catena di
// chiavi naturali): la chiave di riga per il DataTable si compone dalle stesse
// colonne, altrimenti Vue non ha un `data-key` stabile su cui riconciliare.
const erroriConChiave = computed(() =>
  errori.value.map((r) => ({
    ...r,
    row_key_errore: [
      r.tipo_evento, r.lotto_id ?? '', r.fattura_id ?? '', r.task_code ?? '',
    ].join(':'),
  })),
)

// Ref e prop paginator delle tre liste configurabili della Lente 1: lo stato
// di pagina vive nello store dashboard (non in useSearchTable), quindi le
// prop si compongono qui.
const listaErroriRef = ref(null)
const listaGruppiRef = ref(null)
const listaCommesseRef = ref(null)
const erroriPaginatorOptions = computed(() => ({
  totalRecords: erroriCount.value,
  rows: erroriPageSize.value,
  first: (erroriPage.value - 1) * erroriPageSize.value,
  rowsPerPageOptions: PAGINATION.ROWS_OPTIONS,
}))
const gruppiPaginatorOptions = computed(() => ({
  totalRecords: gruppiCount.value,
  rows: gruppiPageSize.value,
  first: (gruppiPage.value - 1) * gruppiPageSize.value,
  rowsPerPageOptions: PAGINATION.ROWS_OPTIONS,
}))
const commessePaginatorOptions = computed(() => ({
  totalRecords: commesseCount.value,
  rows: commessePageSize.value,
  first: (commessePage.value - 1) * commessePageSize.value,
  rowsPerPageOptions: PAGINATION.ROWS_OPTIONS,
}))

// Scopo: display compatto degli estremi fattura (serie numero/anno).
function fatturaDisplay(row) {
  if (!row.fattura_id) return '—'
  const serie = row.fattura_serie ? `${row.fattura_serie} ` : ''
  const numero = row.fattura_numero ?? '—'
  return `${serie}${numero}/${row.fattura_anno ?? '—'}`
}

// Azioni di lista (personalizza colonne + esporta). ⚠️ Questa pagina ha TRE
// liste configurabili e una toolbar sola: le azioni devono agire su quella che
// l'operatore sta davvero guardando, altrimenti personalizzerebbe o
// esporterebbe una lista che non ha davanti.
//
// La precedenza NON e' «il drill-down, se c'e'»: il pannello ERRORI vive di
// vita propria (`v-if="nErroriMese > 0"`) e senza stadio selezionato e'
// l'unica lista a video. Legare le azioni al solo `stadioSelezionato` le
// faceva sparire proprio li' — difetto misurato in app il 2026-08-15.
//
// Ordine: il drill-down quando c'e' (e' cio' su cui l'operatore sta
// lavorando), altrimenti gli errori se sono a video, altrimenti nessuna lista
// e nessuna azione.
const contestoLista = computed(() => {
  if (stadioSelezionato.value === STADIO_GRUPPI) {
    return {
      lista: listaGruppiRef.value,
      exportFn: exportDashboardCompetenzaGruppi,
      params: (formato) => ({
        formato,
        competenza_mese: competenzaCorrente.value,
        stadio: STADIO_GRUPPI,
        tipo_gruppo: gruppiTipo.value,
        order_by: gruppiOrderBy.value,
        order_dir: gruppiOrderDir.value,
      }),
    }
  }
  if (stadioSelezionato.value) {
    return {
      lista: listaCommesseRef.value,
      exportFn: exportDashboardCompetenzaCommesse,
      params: (formato) => ({
        formato,
        competenza_mese: competenzaCorrente.value,
        stadio: stadioSelezionato.value,
        solo_ritardo: soloRitardo.value,
        order_by: commesseOrderBy.value,
        order_dir: commesseOrderDir.value,
      }),
    }
  }
  if (nErroriMese.value > 0) {
    return {
      lista: listaErroriRef.value,
      exportFn: exportDashboardCompetenzaErrori,
      params: (formato) => ({
        formato,
        competenza_mese: competenzaCorrente.value,
        order_by: erroriOrderBy.value,
        order_dir: erroriOrderDir.value,
      }),
    }
  }
  return null
})

const {
  dirty, exportDialogVisible, exportLoading, onExportConfirm, azioniLista,
} = useListaAzioni(() => contestoLista.value?.lista, {
  // Dispatcher: fn e parametri seguono la lista attiva. L'export riceve gli
  // STESSI filtri e ordinamento della lista a video.
  exportFn: (params) => contestoLista.value?.exportFn?.(params),
  getExportParams: (formato) => contestoLista.value?.params?.(formato) ?? { formato },
})

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: () => {
      // Gli errori si riallineano da soli via watch sull'aggregata fresca.
      loadMensile()
      if (stadioSelezionato.value) loadDrillDown()
    },
  },
  // Le due azioni compaiono se c'e' una lista a video su cui agire — drill-down
  // OPPURE pannello errori (vedi `contestoLista`).
  ...(contestoLista.value ? azioniLista.value : []),
])

// ------------------------------------------------------------------ azioni (Fase A cockpit)
// Card DA_APPROVARE del mese corrente (per contatore/valore della conferma).
const cardDaApprovare = computed(() => cards.value.find((c) => c.stadio === 'DA_APPROVARE') ?? null)

// Scopo: refresh post-azione — aggregata + drill-down aperto (gli errori
//        seguono l'aggregata via watch).
function reloadDopoAzione() {
  loadMensile()
  if (stadioSelezionato.value) loadDrillDown()
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
// `avvia(opzioni)`: `messageParams` per i verbi la cui conferma non parla di un
// mese ma di una selezione (l'emissione mirata), `apiOptions` per gli argomenti
// extra della chiamata (i gruppi). Entrambi vuoti = comportamento dei due verbi
// storici, invariato.
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
  function avvia({ messageParams = null, apiOptions = null } = {}) {
    confirmAction({
      title: t(keys.header),
      message: t(keys.conferma, messageParams ?? {
        mese: `${nomiMesi.value[meseIdx.value]} ${anno.value}`,
      }),
      onAccept: async () => {
        const res = await execute(() =>
          apiOptions ? apiFn(competenzaCorrente.value, apiOptions)
                     : apiFn(competenzaCorrente.value))
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

// Verbo FATTURA MIRATA: stesso endpoint e stesso core del verbo di mese
// (I-1), ma con il perimetro ristretto ai gruppi selezionati. Si ferma a
// EMESSA come l'altro; l'esito porta gli N lotti prodotti, che diventano
// l'aggancio «vai al lotto».
const { avvia: avviaFatturaGruppi, polling: giroMirataInCorso } = useVerboFatturazione({
  apiFn: runFatturazione,
  keys: {
    header: 'vendite.dashboard_competenza.fattura_gruppi_header',
    conferma: 'vendite.dashboard_competenza.fattura_gruppi_conferma',
    accodato: 'vendite.dashboard_competenza.fattura_gruppi_accodato',
    errore: 'vendite.dashboard_competenza.fattura_mese_errore',
    inCoda: 'vendite.dashboard_competenza.fattura_mese_in_coda',
  },
  buildEsitoOk: (r) => {
    const lotti = Array.isArray(r.lotti) ? r.lotti : []
    lottiEmessi.value = lotti
    selezioneGruppi.value = []
    const falliti = Number(r.falliti ?? 0)
    // Gruppi richiesti ma rimasti FUORI dal giro (BE `gruppi_non_serviti`,
    // rev 2026-08-15): ognuno porta il motivo classificato dalla diagnosi.
    // Era il caso silenzioso — «2 su 3» sembrava un successo pieno e il
    // terzo restava fermo senza che nessuno lo cercasse.
    const nonServiti = Array.isArray(r.gruppi_non_serviti) ? r.gruppi_non_serviti : []
    // ⚠️ Non e' una catena else-if: falliti e non-serviti possono COESISTERE
    // (una terna fallita E un gruppo fuori perimetro nello stesso giro), e
    // subordinare il secondo al primo ricreerebbe proprio il silenzio che
    // questo esito e' nato per togliere — l'operatore ripara la terna e il
    // gruppo bloccato torna a sparire senza che nessuno lo nomini.
    if (falliti > 0) {
      notify.warn(t('vendite.dashboard_competenza.fattura_gruppi_esito_parziale', {
        lotti: lotti.length, falliti,
      }))
    }
    if (nonServiti.length > 0) {
      // «N su M, chi manca e perche'»: primi 3 per esteso (un toast non regge
      // un elenco), il resto riassunto. Il dettaglio pieno resta nell'esito
      // del job. `dettaglio` e' prosa del BE (come `ultimo_errore.message`,
      // resa cosi' com'e').
      notify.warn(t('vendite.dashboard_competenza.fattura_gruppi_esito_non_serviti', {
        lotti: lotti.length,
        mancanti: nonServiti.length,
        dettagli: elencoTroncato(nonServiti, (s) => `${s.commessa_codice || s.gruppo_key}: ${s.dettaglio}`, '; '),
      }))
    }
    if (falliti === 0 && nonServiti.length === 0) {
      if (lotti.length === 0) {
        // Zero lotti senza errori: nulla era davvero fatturabile (righe gia'
        // prese da un altro giro, o commessa non piu' emittibile). Va detto —
        // un «fatto» muto farebbe pensare a una fattura che non esiste.
        notify.warn(t('vendite.dashboard_competenza.fattura_gruppi_esito_vuoto'))
      } else {
        notify.success(t('vendite.dashboard_competenza.fattura_gruppi_esito', {
          lotti: lotti.length,
        }))
      }
    }
  },
})

// Scopo: avvia l'emissione mirata sui gruppi passati (una riga dal kebab,
//        oppure l'intera selezione). La conferma dichiara quanti gruppi e
//        quante attivita' si stanno per fatturare: e' il peso di cio' che sta
//        per succedere, prima che succeda.
function fatturaGruppi(righe) {
  if (!righe.length) return
  const nAttivita = righe.reduce((acc, r) => acc + Number(r.n_attivita ?? 0), 0)
  avviaFatturaGruppi({
    messageParams: {
      n: righe.length,
      attivita: nAttivita,
      riferimenti: elencoTroncato(righe, gruppoRiferimento),
    },
    apiOptions: { gruppi: righe.map((r) => r.gruppo_key) },
  })
}

// Scopo: kebab riga della lista gruppi — «Fattura questo» (gate permesso +
//        readonly, come il verbo di massa), apertura del DOCUMENTO che da'
//        nome al gruppo e, come seconda via, della commessa che lo contiene.
//
// L'ordine non e' estetico: la riga NOMINA un documento (`riferimento` =
// ORD0005174), quindi l'azione principale deve aprire quello. Fino al
// 2026-08-03 c'era la sola «Apri commessa», che portava a un oggetto
// DIVERSO da quello scritto nella riga — e su una commessa multi-documento
// (piu' ordini sulla stessa commessa) l'operatore ci trovava dentro anche
// righe di un altro documento, senza che nulla glielo avesse annunciato.
// La commessa resta raggiungibile: e' il contenitore in cui il gruppo verra'
// fatturato, e vederlo prima di premere «Fattura» ha senso.
//
// I gruppi SOURCELESS (oneri di commessa) non hanno documento: `documento_id`
// e `area_documento` sono NULL e il BB nasconde da se' la voce — lasciando la
// sola commessa, che per loro E' il riferimento (il `riferimento` di quelle
// righe e' infatti il codice commessa).
function buildGruppoRowActions(row) {
  // Testata bloccata: «Fattura questo» nasce DISABILITATO col motivo (brief
  // emittibilita' §3.1 — partiva e non faceva nulla), e compare «Sblocca
  // commessa»: apre il drawer di governo, dove il verbo «Rendi pronta» e' gia'
  // esposto data-driven dalle capability (fn_available_actions_commessa,
  // enabled+reasons dalla stessa funzione pura del guard).
  const bloccato = !isGruppoEmittibile(row)
  return [
    {
      key: 'fattura_gruppo',
      label: t('vendite.dashboard_competenza.azione_fattura_gruppo'),
      icon: 'pi pi-file-export',
      visible: canFatturare.value,
      disabled: azioneLoading.value || giroMirataInCorso.value || bloccato,
      tooltip: bloccato
        ? t('vendite.dashboard_competenza.gruppo_bloccato_tooltip', {
            stato: row.commessa_stato_descrizione ?? row.commessa_stato_codice_interno ?? '?',
          })
        : '',
      command: () => fatturaGruppi([row]),
    },
    {
      key: 'sblocca_commessa',
      label: t('vendite.dashboard_competenza.azione_sblocca_commessa'),
      icon: 'pi pi-unlock',
      visible: bloccato && !!row.commessa_id && canFatturare.value,
      command: () => apriCommessa(row),
    },
    buildApriDocumentoAction({
      area: row.area_documento,
      documentoId: row.documento_id,
      label: t('vendite.dashboard_competenza.azione_apri_documento', {
        codice: row.riferimento ?? '',
      }),
      onApri: apriDocumentoDrawer,
    }),
    {
      key: 'apri_commessa',
      label: t('vendite.dashboard_competenza.azione_apri_commessa'),
      icon: MANAGE_ICONS.COMMESSA,
      visible: !!row.commessa_id,
      command: () => apriCommessa(row),
    },
  ]
}

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

// Host cross-dominio per il drawer del documento sorgente del gruppo (stesso
// BB dei drill-down Situazione aperta/Backlog e delle tappe dei Passaggi).
// `onClose` ricarica: dal drawer l'operatore puo' aver fatto avanzare il
// documento (confermarlo, evaderlo) e la riga che lo ha aperto sarebbe
// stantia — o addirittura fuori dal perimetro «da emettere».
const {
  visible: docDrawerVisible,
  tipo: docDrawerTipo,
  id: docDrawerId,
  apri: apriDocumentoDrawer,
  onVisibleChange: onDocDrawerVisible,
} = useDocumentoDrawer(() => reloadDopoAzione())

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
  if (stadioSelezionato.value) loadDrillDown()
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
          <ListaConfigStatusTag :dirty="dirty" />
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
            <span class="app-dash-card-title">
              {{ stadioLabel(card.stadio) }}
              <!-- Chiarimento sulla MISURA (stesso pattern della card Ordini in
                   Situazione aperta): il numero conta ATTIVITA', non documenti
                   ne' fatture. Focusabile + aria-label: il v-tooltip PrimeVue
                   si attiva anche su focus, quindi la spiegazione e'
                   raggiungibile da tastiera e screen reader. -->
              <i
                v-if="cardHint(card.stadio)"
                v-tooltip.bottom="cardHint(card.stadio)"
                class="pi pi-info-circle app-dash-card-hint"
                role="img"
                tabindex="0"
                :aria-label="cardHint(card.stadio)"
                @click.stop
                @keydown.enter.stop
              />
            </span>
            <span class="app-dash-stat-n">{{ card.nAttivita }}</span>
            <span class="app-dash-stat-sub">{{ t('vendite.dashboard_competenza.n_attivita') }}</span>
            <!-- Seconda misura, la grana che conta per l'operatore: quante
                 FATTURE. `nFattureStato === 'OK'` e non un truthy check su
                 nFatture — zero fatture e' un'informazione da mostrare. -->
            <span
              v-if="card.nFattureStato === 'OK'"
              class="app-dash-stat-fatture"
            >
              {{ t('vendite.dashboard_competenza.n_fatture', card.nFatture,
                    { n: card.nFatture }) }}
            </span>
            <!-- Calcolo FALLITO: la card lo dice invece di tacere come fa
                 sugli stadi non calcolabili per progetto. Il resto della
                 schermata resta valido — l'avvertimento e' circoscritto alla
                 misura che manca, non un allarme sul cruscotto. -->
            <span
              v-else-if="card.nFattureStato === 'ERRORE'"
              v-tooltip.bottom="t('vendite.dashboard_competenza.n_fatture_errore_tooltip')"
              class="app-dash-stat-fatture-ko"
              role="img"
              tabindex="0"
              :aria-label="t('vendite.dashboard_competenza.n_fatture_errore_tooltip')"
              @click.stop
              @keydown.enter.stop
            >
              <i class="pi pi-exclamation-triangle" />
              {{ t('vendite.dashboard_competenza.n_fatture_errore') }}
            </span>
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
            <!-- Verbo RENDI DEFINITIVE a grana mese (C-7): sulla card
                 FATTURATA, dove stanno le fatture ancora EMESSA — cioe' quelle
                 che questo verbo numera (fix difetto D2, §6-bis). Atto FISCALE
                 (I-7): severity warn per distinguerlo dal pre-fiscale «Fattura».
                 Loading = numerazione in corso (polling non bloccante). -->
            <Button
              v-if="card.stadio === 'FATTURATA' && nDaNumerare > 0 && canNumerare"
              :label="t('vendite.dashboard_competenza.numera_mese')"
              icon="pi pi-lock"
              size="small"
              severity="warn"
              :loading="numeraInCorso"
              :disabled="azioneLoading || numeraInCorso"
              v-tooltip.bottom="t('vendite.dashboard_competenza.numera_mese_tooltip', { n: nDaNumerare })"
              style="margin-top: 0.5rem;"
              @click.stop="onRendiDefinitive"
            />
            <!-- Difetto D3 (§6-bis): «Emesse non fatturate» NON e' un passaggio
                 del percorso — pull e generazione righe fattura avvengono nello
                 stesso step DRAFT, quindi le attivita' passano da «Da emettere»
                 direttamente a «Fatturate». Quello che si raccoglie qui sono
                 RESIDUI (AF sospese, posticipate, o rimaste indietro per un
                 giro interrotto). Dirlo evita che l'operatore aspetti un
                 avanzamento che non arrivera' da solo. -->
            <span
              v-if="card.stadio === 'EMESSA_NON_FATTURATA' && card.nAttivita > 0"
              class="app-dash-residui-hint"
              v-tooltip.bottom="t('vendite.dashboard_competenza.residui_tooltip')"
            >
              <i class="pi pi-info-circle" />
              {{ t('vendite.dashboard_competenza.residui_hint') }}
            </span>
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
          <ListaConfigurabile
            ref="listaErroriRef"
            codice="vendite.dash_competenza_errori"
            data-key="row_key_errore"
            :rows="erroriConChiave"
            :total="erroriCount"
            :loading="erroriLoading"
            :paginator-options="erroriPaginatorOptions"
            :page="erroriPage"
            :sort-field="erroriOrderBy"
            :sort-order="erroriSortOrder"
            @page="onErroriPage"
            @sort="onErroriSort"
          >
            <template #cell-tipo_evento="{ data }">
              <Tag :value="tipoEventoLabel(data.tipo_evento)" severity="danger" />
            </template>
            <template #cell-lotto_codice="{ data }">
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
            <template #cell-fattura_numero="{ data }">
              {{ fatturaDisplay(data) }}
            </template>
            <template #cell-error_code="{ data }">
              {{ data.error_code ?? data.task_code ?? '—' }}
            </template>
            <template #cell-messaggio="{ data }">
              {{ data.messaggio ?? '—' }}
            </template>
            <!-- data_evento non ha slot: il seed dichiara `datetime_short`. -->
          </ListaConfigurabile>
        </div>

        <!-- Drill-down per COMMESSA in pagina (click su card stadio, DEC-4):
             una riga per commessa; il dettaglio a grana attivita' e' nel
             drawer di gestione (kebab «Apri commessa»). -->
        <div ref="commesseSection" class="app-dash-fermi">
          <!-- Card «Da emettere»: il drill-down scende sui GRUPPI FATTURABILI,
               non sulle commesse. Motivo: il verbo qui e' «Fattura», e si
               fattura un documento (o gli oneri di una commessa) — la commessa
               e' multi-sorgente e selezionarla non isola nulla. -->
          <template v-if="stadioSelezionato === STADIO_GRUPPI">
            <div class="app-page-toolbar">
              <h4 class="app-dash-fermi-title">
                {{ t('vendite.dashboard_competenza.gruppi_titolo') }}
              </h4>
              <div class="app-dash-filtri">
                <!-- Filtro tipo documento/sorgente: «Tutti» di default. Le voci
                     sono quelle presenti nel perimetro, col conteggio: una
                     tendina che offre opzioni da zero risultati sarebbe peggio
                     di nessun filtro. -->
                <Select
                  v-model="gruppiTipo"
                  :options="opzioniTipoGruppo"
                  option-label="label"
                  option-value="value"
                  class="app-form-select"
                  :placeholder="t('vendite.dashboard_competenza.filtro_tipo')"
                  v-tooltip.bottom="t('vendite.dashboard_competenza.filtro_tipo')"
                  @change="onGruppiTipoChange"
                />
                <Button
                  v-if="canFatturare"
                  :label="t('vendite.dashboard_competenza.fattura_selezionati', { n: selezioneGruppi.length })"
                  icon="pi pi-file-export"
                  size="small"
                  :loading="giroMirataInCorso"
                  :disabled="selezioneGruppi.length === 0 || azioneLoading || giroMirataInCorso"
                  @click="fatturaGruppi(selezioneGruppi)"
                />
              </div>
            </div>

            <!-- Aggancio al lotto (§5.2): dopo l'emissione l'operatore deve
                 poterci arrivare per numerare. Sono N e non uno: un gruppo con
                 righe di tipo doc fiscale diverso finisce in lotti diversi. -->
            <div v-if="lottiEmessi.length" class="app-dash-lotti-emessi">
              <span>{{ t('vendite.dashboard_competenza.lotti_emessi', { n: lottiEmessi.length }) }}</span>
              <Button
                v-for="lotto in lottiEmessi"
                :key="lotto.lotto_id"
                link
                class="app-cell-link"
                :label="t('vendite.dashboard_competenza.vai_al_lotto', { id: lotto.lotto_id })"
                @click="apriLotto(lotto.lotto_id)"
              />
            </div>

            <!-- Riga di totali: viene dal BE (aggrega la stessa vista della
                 lista), non dalla somma della pagina corrente — che sarebbe un
                 parziale con l'aria di un totale. -->
            <div class="app-dash-totali app-dash-totali--inner">
              <span>
                {{ t('vendite.dashboard_competenza.tot_gruppi') }}
                <strong>{{ gruppiRiepilogo.n_gruppi }}</strong>
              </span>
              <span>
                {{ t('vendite.dashboard_competenza.tot_attivita') }}
                <strong>{{ gruppiRiepilogo.n_attivita }}</strong>
              </span>
              <span>
                {{ t('vendite.dashboard_competenza.tot_valore') }}
                <strong>{{ formatCurrency(Number(gruppiRiepilogo.valore ?? 0)) }}</strong>
              </span>
              <span v-if="gruppiRiepilogo.n_gruppi_oneri > 0">
                {{ t('vendite.dashboard_competenza.tot_gruppi_oneri') }}
                <strong>{{ gruppiRiepilogo.n_gruppi_oneri }}</strong>
              </span>
            </div>

            <ListaConfigurabile
              v-if="gruppiCount > 0 || gruppiLoading"
              ref="listaGruppiRef"
              codice="vendite.dash_competenza_gruppi"
              data-key="gruppo_key"
              :rows="gruppi"
              :total="gruppiCount"
              :loading="gruppiLoading"
              :paginator-options="gruppiPaginatorOptions"
              :page="gruppiPage"
              :sort-field="gruppiOrderBy"
              :sort-order="gruppiSortOrder"
              @page="onGruppiPage"
              @sort="onGruppiSort"
            >
              <!-- Selezione dell'emissione mirata: chrome del BB (slot
                   dedicato), non colonna di catalogo. PrimeVue 4 non ha piu'
                   il predicato per-riga sul selectionMode: la checkbox e'
                   custom (BB useSelezioneToggle). -->
              <template v-if="canFatturare" #selection-header>
                <!-- Pagina senza righe selezionabili (tutte bloccate): il
                     toggle sarebbe un no-op silenzioso — meglio spento che
                     un click che «sembra non fare nulla». -->
                <Checkbox
                  binary
                  :model-value="tuttiGruppiSelezionati"
                  :indeterminate="alcuniGruppiSelezionati"
                  :disabled="!gruppiSelezionabili.length"
                  @update:model-value="toggleTuttiGruppi"
                />
              </template>
              <template v-if="canFatturare" #selection="{ data }">
                <!-- Riga a testata bloccata: non spuntabile (il guard del BB
                     la tiene comunque fuori dalla selezione). -->
                <Checkbox
                  binary
                  :model-value="isGruppoSelezionato(data)"
                  :disabled="!isGruppoEmittibile(data)"
                  @update:model-value="toggleGruppo(data)"
                />
              </template>

              <template #cell-riferimento="{ data }">
                <strong>{{ gruppoRiferimento(data) }}</strong>
                <!-- Segnalare, non nascondere (brief emittibilita' §3.1): la
                     testata non ammette fatturazione — lucchetto col motivo,
                     accanto al nome che l'operatore sta gia' leggendo. -->
                <i
                  v-if="!isGruppoEmittibile(data)"
                  class="pi pi-lock app-dash-gruppo-bloccato"
                  v-tooltip.bottom="t('vendite.dashboard_competenza.gruppo_bloccato_tooltip', {
                    stato: data.commessa_stato_descrizione ?? data.commessa_stato_codice_interno ?? '?',
                  })"
                />
              </template>
              <template #cell-tipo_gruppo="{ data }">
                <Tag
                  :value="gruppoTipoLabel(data)"
                  :severity="data.ha_oneri ? 'warn' : 'secondary'"
                />
              </template>
              <template #cell-cliente_display="{ data }">
                {{ data.cliente_display ?? '—' }}
              </template>
              <template #cell-commessa_codice="{ data }">
                {{ data.commessa_codice ?? '—' }}
              </template>
              <template #cell-n_attivita="{ data }">
                <Tag
                  :value="String(data.n_attivita)"
                  severity="secondary"
                  v-tooltip.bottom="t('vendite.dashboard_competenza.n_attivita_tooltip', { n: data.n_attivita })"
                />
              </template>
              <!-- valore non ha slot: il seed dichiara `currency_eur`. -->
              <template #cell-data_attivita_max="{ data }">
                <span v-if="data.data_attivita_min">
                  {{ displayDate(data.data_attivita_min) }}<template v-if="data.data_attivita_max && data.data_attivita_max !== data.data_attivita_min"> – {{ displayDate(data.data_attivita_max) }}</template>
                </span>
                <span v-else>—</span>
              </template>

              <template #actions="{ data, compact }">
                <RowActionsMenu :row="data" :actions="buildGruppoRowActions(data)" :force-compact="compact" />
              </template>
            </ListaConfigurabile>
            <!-- Empty-state ONESTO (regola del BB usePagedDashFetch): «nessun
                 gruppo» si dice solo dopo una fetch RIUSCITA. Prima — o dopo un
                 errore di rete — la lista e' vuota per ignoranza, non per
                 assenza di lavoro, e dichiararlo sarebbe una bugia che invita a
                 chiudere il mese. -->
            <div v-else-if="gruppiLoaded" class="app-empty-state">
              <i class="pi pi-check-circle" />
              <p>{{ t('vendite.dashboard_competenza.nessun_gruppo') }}</p>
            </div>
          </template>

          <template v-else-if="stadioSelezionato">
            <div class="app-page-toolbar">
              <h4 class="app-dash-fermi-title">
                {{ t('vendite.dashboard_competenza.commesse_titolo', { stadio: stadioSelezionatoLabel }) }}
              </h4>
              <label class="app-dash-filter-toggle">
                <Checkbox v-model="soloRitardo" binary @change="onSoloRitardoChange" />
                {{ t('vendite.dashboard_competenza.solo_ritardo') }}
              </label>
            </div>
            <ListaConfigurabile
              v-if="commesseCount > 0 || commesseLoading"
              ref="listaCommesseRef"
              codice="vendite.dash_competenza_commesse"
              data-key="commessa_id"
              :rows="commesse"
              :total="commesseCount"
              :loading="commesseLoading"
              :paginator-options="commessePaginatorOptions"
              :page="commessePage"
              :sort-field="commesseOrderBy"
              :sort-order="commesseSortOrder"
              @page="onCommessePage"
              @sort="onCommesseSort"
            >
              <template #cell-commessa_codice="{ data }">
                {{ data.commessa_codice ?? `#${data.commessa_id}` }}
              </template>
              <template #cell-cliente_display="{ data }">
                {{ data.cliente_display ?? '—' }}
              </template>
              <template #cell-n_attivita="{ data }">
                <Tag :value="String(data.n_attivita)" severity="secondary" v-tooltip.bottom="t('vendite.dashboard_competenza.n_attivita_tooltip', { n: data.n_attivita })" />
              </template>
              <!-- valore_tot e valore_fatturato_tot non hanno slot: il seed
                   dichiara `currency_eur` per entrambe. -->
              <template #cell-data_attivita_max="{ data }">
                <span v-if="data.data_attivita_min">
                  {{ displayDate(data.data_attivita_min) }}<template v-if="data.data_attivita_max && data.data_attivita_max !== data.data_attivita_min"> – {{ displayDate(data.data_attivita_max) }}</template>
                </span>
                <span v-else>—</span>
              </template>
              <template #cell-n_in_ritardo="{ data }">
                <span v-if="data.n_in_ritardo > 0" class="app-dash-ritardo">
                  <i class="pi pi-clock" /> {{ data.n_in_ritardo }}
                </span>
                <span v-else>—</span>
              </template>

              <!-- Azioni riga (Fase A cockpit): Approva (solo DA_APPROVARE,
                   l'intera commessa) + Apri commessa (drawer col dettaglio). -->
              <template #actions="{ data, compact }">
                <RowActionsMenu :row="data" :actions="buildCommessaRowActions(data)" :force-compact="compact" />
              </template>
            </ListaConfigurabile>
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

    <!-- Host del drawer di dettaglio del DOCUMENTO sorgente del gruppo
         (kebab «Apri ...»): il tipo arriva dal registry, l'id dal BE. -->
    <DocumentoDrawerHost
      :visible="docDrawerVisible"
      :tipo-codice="docDrawerTipo"
      :doc-id="docDrawerId"
      @update:visible="onDocDrawerVisible" />

    <!-- Scelta formato export (CSV/XLSX) del drill-down VISIBILE: il file
         copia la lista a video, filtri e ordinamento compresi. -->
    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />
  </div>
</template>
