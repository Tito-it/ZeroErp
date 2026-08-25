<script setup>
// Scopo: Drawer diagnostico del lotto di fatturazione (cockpit Fase B, B-3/B-4).
//        Il posto dove si capisce in pochi secondi se un lotto è sano o bloccato
//        e lo si sblocca: testata + step corrente, tab fatture / task-run
//        (tentativi ed esiti) / segnalazioni, e le azioni di governo — avanza
//        step, rerun su ERRORE, riporta a bozza (demolizione pre-fiscale),
//        reset singola fattura DRAFT. Nessuna logica: la macchina step/gate/
//        rollback vive nel motore DB/BE (fail-visible sugli errori parlanti).
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
// ⚠️ DataTable/Column «a mano» e NON `<ListaConfigurabile>`, che e' quello che
// usano le altre tre schede: la storia non ha (e non deve avere) una
// definizione a catalogo — non e' una lista che l'operatore personalizza, e'
// un giornale. ⛔ Senza questi due import il pannello non darebbe nessun
// errore: Vue renderebbe due elementi sconosciuti e la scheda resterebbe
// vuota.
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Message from 'primevue/message'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import SelectButtonGravita from '../../core/components/SelectButtonGravita.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import BersaglioAzioni from '../../core/components/BersaglioAzioni.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ErroreRigaInfo from '../../core/components/ErroreRigaInfo.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
import { useListaDrawerPaginata } from '../../core/composables/useListaDrawerPaginata'
import PdfDocumentiSorgenteDialog from '../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import FatturaDrawer from './FatturaDrawer.vue'
import NumerazioneDataDialog from './NumerazioneDataDialog.vue'
import { useDocumentiPerSorgenteStore } from '../../documenti/stores/documentiPerSorgente'
import { SORGENTE_CODES } from '../../documenti/constants'
import { downloadBlob } from '../../core/utils/download'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { mapAvailableActionsToDrawerActions } from '../../core/composables/useDrawerActions'
import {
  useLottoAzioni,
  LOTTO_AZIONE_PERMESSO,
  LOTTO_AZIONE_PIPELINE_UI,
} from '../composables/useLottoAzioni'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { extractApiError } from '../../core/utils/apiError'
import {
  gravitaGiornaleSeverity,
  naturaDocSeverity,
  statoEsecuzioneFatturaSeverity,
  statoLottoSeverity,
  statoTaskRunSeverity,
} from '../../core/utils/severity'
import {
  getLotto,
  listLottoFatture,
  listLottoTaskRuns,
  getLottoSegnalazioni,
  listLottoSegnalazioni,
  exportLottoFatture,
  exportLottoTaskRuns,
  exportLottoSegnalazioni,
  eliminaFatturaDaLotto,
  getLottoGiornale,
} from '../api/lotti'

const props = defineProps({
  visible: { type: Boolean, default: false },
  lottoId: { type: [Number, null], default: null },
  // Ispezione pura (feedback_drawer_readonly): nasconde ogni azione di governo.
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'changed'])
// `te` serve a `mapAvailableActionsToDrawerActions`: chiave i18n mancante →
// mostra il codice macchina invece del path (fail-visible).
const { t, te } = useI18n()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const docStore = useDocumentiPerSorgenteStore()

// Readonly effettivo: area in LETTURA (inject dal provider della view) o prop
// di ispezione. In readonly le azioni di governo spariscono (il BE resta il
// guard vero, questo e' UX coerente col pattern protect).
const parentReadonly = useInjectReadonly()
const isReadonly = computed(() => parentReadonly.value || props.readonly)

// Gate azioni di riga fattura. I permessi delle azioni di GOVERNO del lotto non
// si leggono più qui: viaggiano come `action` sulle entry della barra e li
// filtra `DrawerActionsBar` (`auth.isActionAllowed`), un solo meccanismo per
// tutti i drawer.
const { isAllowed: canResetFattura } = useActionPermission('reset_lotto_fattura_draft')

const lotto = ref(null)
// ⭐ I TRE TAB SONO TRE LISTE, non tre dettagli di un master: dal 2026-08-22
// montano `<ListaConfigurabile>` (seed 45/46/47), quindi paginazione,
// ordinamento server-side e colonne personalizzabili come tutte le altre.
// Lo stato paginato lo tiene un composable solo, usato tre volte: scritto a
// mano tre volte sarebbero state tre occasioni di dimenticare l'azzeramento
// della pagina al cambio ordinamento.
const listaDocumenti = useListaDrawerPaginata(({ page, pageSize, sortBy, sortDir }) =>
  listLottoFatture(props.lottoId, {
    page, page_size: pageSize, ...(sortBy ? { sort_by: sortBy, sort_dir: sortDir } : {}),
  }))
// ⭐ Ordinamento iniziale «Fine» DESC: la diagnostica si legge dall'ULTIMA cosa
//    successa. Senza, la funzione DB ripiega su `started_at` e il frontend manda
//    `asc` — cioe' il piu' VECCHIO in cima, e su un lotto ripreso otto volte
//    l'esito che interessa sta in fondo all'ultima pagina.
// ⚠️ L'`ORDER BY` della funzione ha `NULLS LAST` in entrambi i versi e
//    `ended_at` e' NULL su un task IN_ESECUZIONE: quello finirebbe ultimo,
//    ed e' proprio quello che si vorrebbe vedere per primo. Oggi non morde
//    (289 task_runs, zero senza fine); se un giorno mordesse, la colonna da
//    usare e' `started_at`, che NULL non e' mai.
// ⭐ LE TRE AMPIEZZE della scheda Task, e non sono una scala di gravità: sono
//    QUANTO si guarda. Il default esclude gli ANNULLATO perché sono i residui
//    delle passate precedenti — sul lotto 6260 sono 80 righe su 90, e l'unico
//    errore vero sta in mezzo. È il taglio consigliato dal team DB col
//    changeSet `20260824-11`, e non dipende da nessuna definizione di «giro».
// ⚠️ `TUTTI` è `null` e non un elenco: «nessuno stato scelto» e «tutti gli
//    stati» sono la stessa domanda, e mandare l'elenco completo obbligherebbe
//    a tenerlo allineato al vocabolario del DB — che è esattamente ciò che il
//    backend evita non validandolo.
const AMPIEZZE_TASK = {
  RILEVANTI: ['ERRORE', 'COMPLETATO', 'IN_ESECUZIONE'],
  ERRORI: ['ERRORE'],
  TUTTI: null,
}
const ampiezzaTask = ref('RILEVANTI')
// Quante righe i filtri lasciano fuori. ⭐ È ciò che rende ONESTO un default
// che nasconde: senza questo numero una lista filtrata e una lista vuota si
// leggono uguali — lo stesso mestiere di `segnalazioniFuoriJob` qui sotto.
const esclusiTask = ref(0)

const listaTask = useListaDrawerPaginata(
  async ({ page, pageSize, sortBy, sortDir }) => {
    const res = await listLottoTaskRuns(props.lottoId, {
      page, pageSize, orderBy: sortBy, orderDir: sortDir,
      taskStato: AMPIEZZE_TASK[ampiezzaTask.value],
    })
    // Letto QUI e non nel composable: è un campo extra di questo endpoint, e
    // il BB delle liste in drawer non deve sapere che questa è speciale.
    esclusiTask.value = res?.data?.data?.esclusi_count ?? 0
    return res
  },
  { sortBy: 'ended_at', sortDir: -1 },
)
// Le RIGHE arrivano da un endpoint suo, separato dai conteggi: quello alimenta
// il banner ed e' piccolo, questo pagina e ordina e serve solo a scheda aperta.
// ⭐ Ordinamento iniziale «Quando» DESC. ⚠️ Non cambia l'ordine a video, lo
//    DICHIARA: il filtro per livello ha sempre una voce selezionata
//    (`allowEmpty: false`), quindi il rango di gravita' del default DB e'
//    costante e a decidere restava gia' il tiebreak `data_ora DESC`. Mancava
//    la freccia sull'intestazione — cioe' l'operatore non poteva sapere con
//    che criterio stava leggendo.
// ⛔ Per questo si passa dal rango a `data_ora` senza perdere niente: la
//    gravita' la fa il FILTRO, non l'ordinamento.
const listaSegnalazioni = useListaDrawerPaginata(
  ({ page, pageSize, sortBy, sortDir }) =>
    listLottoSegnalazioni(props.lottoId, {
      livello: livelloSegnalazioni.value, page, pageSize, orderBy: sortBy, orderDir: sortDir,
    }),
  { sortBy: 'data_ora', sortDir: -1 },
)

// Azioni di lista (personalizza colonne + esporta): lo stesso BB delle altre
// liste standard, una istanza per tab.
// ⭐ L'export riceve gli STESSI filtri e lo STESSO ordinamento della lista a
// video: il file E' la lista, non una seconda query che le somiglia.
const listaDocumentiRef = ref(null)
const listaTaskRef = ref(null)
const listaSegnalazioniRef = ref(null)

// Scopo: la voce «ricarica» che ogni lista dell'applicazione ha, composta con
//        quelle del BB. ⚠️ `kind: 'utility'`: sul piccolo schermo finisce nel
//        kebab insieme alle altre — e' il meccanismo standard di
//        `PageActionsBar`, non una scelta di questa schermata.
function conRicarica(azioniBB, ricarica) {
  return computed(() => [
    {
      key: 'reload',
      kind: 'utility',
      label: t('common.reload_list'),
      icon: MANAGE_ICONS.RELOAD,
      command: ricarica,
    },
    ...azioniBB.value,
  ])
}

const azioniDocumenti = useListaAzioni(() => listaDocumentiRef.value, {
  exportFn: (params) => exportLottoFatture(props.lottoId, params),
  getExportParams: (formato) => ({
    formato,
    ...(listaDocumenti.sortField.value
      ? {
          sort_by: listaDocumenti.sortField.value,
          sort_dir: listaDocumenti.sortOrder.value === -1 ? 'desc' : 'asc',
        }
      : {}),
  }),
})
const azioniTask = useListaAzioni(() => listaTaskRef.value, {
  exportFn: (params) => exportLottoTaskRuns(props.lottoId, params),
  getExportParams: (formato) => ({
    formato,
    // ⚠️ L'ampiezza è un FILTRO della scheda: senza, il file conterrebbe le 90
    // righe mentre a video se ne vedono 10 — e finirebbe in mano a qualcuno
    // come «i task di quel lotto».
    ...(AMPIEZZE_TASK[ampiezzaTask.value]
      ? { task_stato: AMPIEZZE_TASK[ampiezzaTask.value].join(',') }
      : {}),
    ...(listaTask.sortField.value
      ? {
          order_by: listaTask.sortField.value,
          order_dir: listaTask.sortOrder.value === -1 ? 'desc' : 'asc',
        }
      : {}),
  }),
})
const azioniSegnalazioni = useListaAzioni(() => listaSegnalazioniRef.value, {
  exportFn: (params) => exportLottoSegnalazioni(props.lottoId, params),
  getExportParams: (formato) => ({
    formato,
    // ⚠️ Il livello e' un FILTRO della scheda: senza, il file conterrebbe
    // tutte le segnalazioni mentre a video se ne vede un livello solo.
    ...(livelloSegnalazioni.value ? { livello: livelloSegnalazioni.value } : {}),
    ...(listaSegnalazioni.sortField.value
      ? {
          order_by: listaSegnalazioni.sortField.value,
          order_dir: listaSegnalazioni.sortOrder.value === -1 ? 'desc' : 'asc',
        }
      : {}),
  }),
})

// Le tre barre a video: «ricarica» davanti, poi personalizza e esporta.
const barraDocumenti = conRicarica(azioniDocumenti.azioniLista, () => listaDocumenti.carica())
const barraTask = conRicarica(azioniTask.azioniLista, () => listaTask.carica())
const barraSegnalazioni = conRicarica(azioniSegnalazioni.azioniLista, caricaSegnalazioni)
const segnalazioni = ref(null)
const tabLoading = ref(false)
// Dialog archivio documenti fattura (C-8). Dichiarati QUI, PRIMA del watch
// immediate che li resetta: una ref toccata da un watch immediate dichiarata
// dopo va in TDZ silenziosa (memoria feedback_vue_watch_immediate_tdz).
const pdfDialogVisible = ref(false)
const pdfFatturaId = ref(null)
// Drawer di consultazione fattura: stessa regola di dichiarazione anticipata
// (il watch immediate sotto lo resetta).
const fatturaDrawerVisible = ref(false)
const fatturaDrawerId = ref(null)

// Capability dal BE (`script.fn_available_actions_lotto`, 2026-08-04): quali
// verbi di governo esistono su QUESTO lotto, quali sono abilitati e — se non lo
// sono — perché. Le condizioni fiscali (DRAFT / EMESSA / DEFINITIVA) NON si
// scrivono più qui: erano cinque `computed` che ricopiavano in JavaScript
// precondizioni scritte in PL/pgSQL, e avevano già prodotto un pulsante-vicolo
// cieco («Annulla lotto» visibile da EMESSA, trovato in-app il 2026-07-31).
// Ora la sorgente è una sola: le stesse `fn_check_*` da cui le funzioni di
// mutazione sollevano. Resta al frontend il solo gate di pipeline (avanza /
// rilancia), che il DB non espone di proposito: vive in `useLottoAzioni`,
// condiviso col kebab della lista.
const availableActions = computed(() => lotto.value?.available_actions ?? [])

// Segnalazioni bloccanti: mostra il banner se il lotto ha criticità.
const haSegnalazioniCritiche = computed(() => (segnalazioni.value?.critical_count ?? 0) > 0)

// Tab attiva CONTROLLATA (era fissa a "fatture"): serve al link del banner, che
// porta l'operatore sulla scheda invece di dirgli dove guardare.
const tabAttiva = ref('fatture')

// ------------------------------------------------------ la STORIA del lotto
// ⭐ La quarta scheda (Passo A, seconda meta'). Non e' un altro elenco di
//    problemi: le altre tre dicono COSA C'E' ORA — i documenti, i tentativi, le
//    segnalazioni aperte — questa dice COSA E' SUCCESSO, in che ordine,
//    comprese le cose andate bene e i tentativi poi superati.
// ⛔ Non era scrivibile prima del 2026-08-24 19:33. Qui i registri sono TRE, e
//    con l'orario di TRANSAZIONE le righe di una stessa transazione uscivano
//    tutte con lo stesso istante: una timeline che mostra una sequenza mai
//    avvenuta, e che guardandola non sembra rotta (R-1, risolto dal team DB).
const GIORNALE_PAGE_SIZE = 50
const giornale = ref([])
const giornaleTotale = ref(0)
const giornaleInfo = ref(0)
const giornaleRitirate = ref(0)
// ⛔ Senza questo flag, un elenco vuoto perche' la fetch e' fallita e uno vuoto
//    perche' non e' successo niente si leggono uguali — e il secondo e'
//    un'informazione, il primo no.
const giornaleCaricato = ref(false)
const giornaleSortField = ref('gravita')
const giornaleSortOrder = ref(-1)
// ⭐ Le righe di routine si nascondono ma si CONTANO. Sul 6260 sono 173 su 286:
//    mostrarle tutte seppellisce le 113 che dicono qualcosa, nasconderle senza
//    dirlo fa credere che il lotto abbia avuto solo problemi.
const giornaleInfoVisibili = ref(false)

// ⚠️ Niente `severity` sulle due voci: non sono livelli di gravita' e il BB del
// colore direbbe una cosa falsa — «Tutto» non e' piu' grave di «Solo problemi»,
// e' piu' largo. Stessa ragione del filtro ampiezza dei task.
const opzioniGiornaleInfo = computed(() => [
  { value: false, label: t('vendite.lotti.giornale_solo_problemi') },
  { value: true, label: t('vendite.lotti.giornale_tutto') },
])

// Livello dell'elenco segnalazioni. Parte dalle CRITICHE perché sono quelle che
// fermano il lotto — chi apre la scheda ci arriva per quelle.
const LIVELLI_SEGNALAZIONE = { CRITICHE: 'C', AVVISI: 'W', ATTENZIONI: 'I' }
const livelloSegnalazioni = ref(LIVELLI_SEGNALAZIONE.CRITICHE)
// Il livello di cui abbiamo GIA' l'elenco in mano. Serve al watch qui sotto per
// non rifare la stessa domanda: alla riapertura il drawer rimette il filtro sul
// default e ricarica tutto — senza questo confronto la scheda partirebbe con
// due chiamate identiche.
const livelloCaricato = ref(null)

// Le tre voci del filtro, con il CONTEGGIO nell'etichetta: il numero non è un
// di più, è ciò che dice se vale la pena guardare quel livello — e così i
// conteggi non hanno bisogno di una riga tutta loro.
// ⚠️ `severity` e non il livello grezzo: il BB parla il linguaggio delle
// severity PrimeVue (le stesse di `core/utils/severity.js`), e la traduzione
// dal vocabolario del DB (`status` di `fatture_log`) si fa QUI, una volta sola.
const opzioniLivello = computed(() => [
  {
    value: LIVELLI_SEGNALAZIONE.CRITICHE,
    severity: 'danger',
    label: `${t('vendite.lotti.critical')} (${segnalazioni.value?.critical_count ?? 0})`,
  },
  {
    value: LIVELLI_SEGNALAZIONE.AVVISI,
    severity: 'warn',
    label: `${t('vendite.lotti.warning')} (${segnalazioni.value?.warning_count ?? 0})`,
  },
  {
    value: LIVELLI_SEGNALAZIONE.ATTENZIONI,
    severity: 'info',
    label: `${t('vendite.lotti.attention')} (${segnalazioni.value?.attention_count ?? 0})`,
  },
])

// Scopo: la severity di un livello di segnalazione. ⚠️ Stessa scala del filtro
//        (`SelectButtonGravita`) e dell'icona di riga (`ErroreRigaInfo`): tre
//        rese diverse dello stesso dato devono dire lo stesso colore.
const SEVERITY_PER_LIVELLO = { C: 'danger', W: 'warn', I: 'info' }
function severitaLivelloSegnalazione(livello) {
  return SEVERITY_PER_LIVELLO[livello] || 'secondary'
}
// Quante segnalazioni restano fuori dall'ultima corsa di pipeline: senza questo
// numero un elenco filtrato e uno vuoto si leggono uguali.
// ⚠️ Non e' `count`, che e' il totale della pagina corrente di filtro: e' un
// conteggio a parte che la funzione DB ripete su ogni riga.
const segnalazioniFuoriJob = ref(0)

// Scopo: il link del banner — porta sulla scheda già filtrata sulle critiche.
//        Rimette il livello anche se l'operatore l'aveva cambiato prima: il
//        banner parla di quelle, e atterrare sugli avvisi sarebbe una risposta
//        a un'altra domanda.
async function apriSegnalazioni() {
  tabAttiva.value = 'segnalazioni'
  if (livelloSegnalazioni.value !== LIVELLI_SEGNALAZIONE.CRITICHE) {
    livelloSegnalazioni.value = LIVELLI_SEGNALAZIONE.CRITICHE
  }
}

// ------------------------------------------------------------------ load
async function loadLotto() {
  const res = await loadDetailOrClose(() => getLotto(props.lottoId))
  if (res == null) return false
  lotto.value = res.data?.data ?? null
  return true
}

// Scopo: l'elenco segnalazioni + il contatore «fuori dall'ultima corsa», che
//        viaggia con le righe e non con i conteggi di testata.
async function caricaSegnalazioni() {
  await listaSegnalazioni.carica()
  const res = await listLottoSegnalazioni(props.lottoId, {
    livello: livelloSegnalazioni.value, page: 1, pageSize: 1,
  })
  segnalazioniFuoriJob.value = res.data?.data?.fuori_job_count ?? 0
  livelloCaricato.value = livelloSegnalazioni.value
}

// Scopo: carica la storia del lotto — il lotto PIU' le sue fatture.
// ⚠️ Silenziosa e best-effort, come sulla fattura: un giornale che non arriva
//    non deve impedire di leggere il lotto, e il pannello lo dice da se'
//    restando su «non caricato» invece di affermare «non e' successo niente».
async function caricaGiornale() {
  if (!props.lottoId) return
  try {
    const res = await getLottoGiornale(props.lottoId, {
      pageSize: GIORNALE_PAGE_SIZE,
      sortBy: giornaleSortField.value,
      sortDir: giornaleSortOrder.value === 1 ? 'asc' : 'desc',
      info: giornaleInfoVisibili.value,
    })
    // ⚠️ Qui si passa DIRETTAMENTE dall'api, non da `useApiHandler.execute`:
    //    quindi la response axios arriva intera e si scarta l'envelope a mano
    //    (`res.data.data`). ⛔ Sul drawer fattura e' il contrario, e i due non
    //    si copiano a vicenda: la' `execute` restituisce il payload gia'
    //    scartato, e un unwrap di troppo produsse un elenco vuoto con il flag
    //    «caricato» a true — il pannello che afferma «nessun evento» su un
    //    documento che ne aveva tre.
    const d = res.data?.data ?? {}
    giornale.value = d.results ?? []
    giornaleTotale.value = Number(d.count ?? 0)
    giornaleInfo.value = Number(d.info_count ?? 0)
    giornaleRitirate.value = Number(d.ritirate_count ?? 0)
    giornaleCaricato.value = true
  } catch {
    // Volutamente muto: vedi sopra.
  }
}

// Scopo: riordina la storia RICHIEDENDOLA AL SERVER.
// ⛔ Il `lazy` della tabella non e' un dettaglio di resa: senza, PrimeVue
//    ordinerebbe l'array gia' caricato — cioe' la sola pagina — e «il piu'
//    grave» diventerebbe «il piu' grave fra i primi 50».
function onGiornaleSort(event) {
  giornaleSortField.value = event.sortField || 'gravita'
  giornaleSortOrder.value = event.sortOrder ?? -1
  caricaGiornale()
}

// Mostrare/nascondere le righe di routine e' una nuova DOMANDA al server, non
// un filtro in memoria: l'elenco e' paginato, e filtrare qui filtrerebbe la
// sola pagina caricata.
watch(giornaleInfoVisibili, () => {
  if (!props.visible || !props.lottoId) return
  caricaGiornale()
})

async function loadTabs() {
  tabLoading.value = true
  try {
    const [sRes] = await Promise.all([
      getLottoSegnalazioni(props.lottoId),
      listaDocumenti.carica(),
      listaTask.carica(),
      caricaSegnalazioni(),
      caricaGiornale(),
    ])
    segnalazioni.value = sRes.data?.data ?? null
  } catch (err) {
    // Fail-visible: un tab vuoto per errore non deve sembrare "nessun dato".
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    tabLoading.value = false
  }
}

async function reloadAll() {
  if (await loadLotto()) await loadTabs()
}

// Cambio livello = nuova domanda al backend. ⚠️ NON si filtra in memoria: la
// risposta porta l'elenco di UN livello per volta, quindi filtrare qui
// mostrerebbe solo ciò che è già stato scaricato — cioè, su un livello mai
// chiesto, un elenco vuoto accanto a un contatore che dice il contrario.
// Le tre voci del filtro ampiezza. ⚠️ Niente `severity`: non sono livelli di
// gravità e il BB del colore direbbe una cosa falsa — «Rilevanti» non è più
// grave di «Tutti», è più stretto.
const opzioniAmpiezzaTask = computed(() => [
  { value: 'RILEVANTI', label: t('vendite.lotti.task_ampiezza_rilevanti') },
  { value: 'ERRORI', label: t('vendite.lotti.task_ampiezza_errori') },
  { value: 'TUTTI', label: t('vendite.lotti.task_ampiezza_tutti') },
])

watch(ampiezzaTask, async () => {
  if (!props.visible || !props.lottoId) return
  // ⚠️ Si torna a pagina 1, come sul filtro delle segnalazioni: cambiare
  // ampiezza stando a pagina 3 lascerebbe l'operatore in mezzo a un elenco che
  // non è più quello di prima.
  listaTask.page.value = 1
  await listaTask.carica()
})

watch(livelloSegnalazioni, async (livello) => {
  if (!props.visible || !props.lottoId) return
  if (livello === livelloCaricato.value) return
  // ⚠️ Si torna a pagina 1: cambiare filtro stando a pagina 3 lascerebbe
  // l'operatore in mezzo a un elenco che non e' piu' quello di prima.
  listaSegnalazioni.page.value = 1
  await caricaSegnalazioni()
})

// Scopo: reload mirato post reset-fattura — cambiano solo testata (step/stato)
//        e lista fatture; task-run e segnalazioni restano com'erano.
async function reloadFatture() {
  tabLoading.value = true
  try {
    if (await loadLotto()) await listaDocumenti.carica()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    tabLoading.value = false
  }
}

watch(
  () => [props.visible, props.lottoId],
  async ([visible]) => {
    // Il dialog documenti e' teleported (fuori dal DOM del drawer): senza
    // chiusura esplicita resterebbe aperto orfano alla chiusura del drawer.
    // Stessa ragione per il drawer fattura, anch'esso teleported.
    pdfDialogVisible.value = false
    fatturaDrawerVisible.value = false
    if (!visible || !props.lottoId) return
    lotto.value = null
    segnalazioni.value = null
    segnalazioniFuoriJob.value = 0
    listaDocumenti.reset()
    listaTask.reset()
    listaSegnalazioni.reset()
    // Riapertura = si riparte dai DOCUMENTI, sempre. Senza questo reset il
    // drawer riapriva sulla scheda dove l'operatore era finito l'ultima volta
    // (tipicamente «Segnalazioni», dove l'aveva portato il link del banner):
    // un drawer che si apre in un punto diverso a ogni giro fa perdere il
    // riferimento. Stessa ragione per il livello del filtro.
    tabAttiva.value = 'fatture'
    livelloSegnalazioni.value = LIVELLI_SEGNALAZIONE.CRITICHE
    livelloCaricato.value = null
    // Stessa ragione del livello: il drawer riapre sempre dallo stesso punto.
    ampiezzaTask.value = 'RILEVANTI'
    esclusiTask.value = 0
    // Stessa ragione: la storia riparte dal suo default (i piu' gravi, senza
    // le righe di routine) invece che da dove l'operatore l'aveva lasciata.
    giornale.value = []
    giornaleTotale.value = 0
    giornaleInfo.value = 0
    giornaleRitirate.value = 0
    giornaleCaricato.value = false
    giornaleInfoVisibili.value = false
    giornaleSortField.value = 'gravita'
    giornaleSortOrder.value = -1
    await reloadAll()
  },
  { immediate: true },
)

// ------------------------------------------------- barra azioni di governo
// Le azioni (conferme, chiamate, toast) vivono nel composable condiviso col
// kebab della lista lotti: una sola sede — estratto alla seconda occorrenza
// (regola del 2, ok Tid 2026-08-04). Qui resta solo il refresh post-azione,
// che è del drawer.
const {
  esegui: eseguiAzione,
  verbiPipeline,
  loading: azioniLoading,
  // FE-2: il dialog della data documento. Lo STATO vive nel composable (una
  // sede sola, condivisa col kebab della lista); qui si rende soltanto.
  numeraDialog,
  confermaNumera,
} = useLottoAzioni({
  onDone: async () => {
    await reloadAll()
    emit('changed')
  },
})

// Scopo: azioni del drawer — quelle di stato dal blob capability, più i due
//        verbi di pipeline che il DB deliberatamente NON espone (avanza e
//        rilancia): il loro gate è fatto di step successivo, criticità attive e
//        distinzione avanza/rilancio dello stesso step, e vive per intero nel
//        runner Python. Finché sta lì, resta gate del frontend — farne scendere
//        solo un pezzo creerebbe la seconda copia della regola che questo
//        lavoro elimina (risposta DB 2026-08-04 §5).
const drawerActions = computed(() => {
  const azioni = mapAvailableActionsToDrawerActions({
    availableActions: availableActions.value,
    t,
    te,
    readonly: isReadonly,
    onAction: (action) => eseguiAzione(props.lottoId, action.key),
  }).map((a) => ({
    ...a,
    ...(LOTTO_AZIONE_PERMESSO[a.key] ? { action: LOTTO_AZIONE_PERMESSO[a.key] } : {}),
    // La numerazione è uno STEP di pipeline: con criticità attive il runner la
    // rifiuta (`blocks_next_step`). Il DB non conosce le segnalazioni, quindi
    // questo disabilitato lo aggiunge chi le ha: noi. Non sovrascrive un
    // `disabled` già vero arrivato dalle `fn_check_*` (né il suo tooltip,
    // che spiega il motivo del DB).
    ...(a.key === 'numera' && haSegnalazioniCritiche.value && !a.disabled
      ? { disabled: true, tooltip: t('vendite.lotti.blocca_step') }
      : {}),
  }))

  if (isReadonly.value) return azioni

  // I due verbi di pipeline, con la stessa regola che usa il kebab della lista
  // (sede unica nel composable). Il rilancio dello stesso step è ammesso ANCHE
  // con criticità attive (D-Q p.1): è la via d'uscita — si corregge il dato a
  // monte e si ri-esegue. L'avanzamento no, quello lo blocca il runner.
  for (const key of verbiPipeline(lotto.value)) {
    const ui = LOTTO_AZIONE_PIPELINE_UI[key]
    // ⚠️ SOLO `avanza_step`, ed è una condizione scritta apposta e non un
    // effetto di come è scritta: `rigenera_bozza` è un rilancio dello STESSO
    // step, che con criticità attive il runner ammette (è la via d'uscita).
    // Bloccarlo qui toglierebbe l'unica strada per uscire dalle criticità
    // proprio ai lotti riaperti.
    const bloccato = key === 'avanza_step' && haSegnalazioniCritiche.value
    azioni.unshift({
      key,
      kind: 'state',
      label: t(ui.label_key),
      icon: ui.icon,
      severity: ui.severity,
      action: LOTTO_AZIONE_PERMESSO[key],
      disabled: bloccato,
      tooltip: bloccato ? t('vendite.lotti.blocca_step') : undefined,
      command: () => eseguiAzione(props.lottoId, key),
    })
  }
  return azioni
})

// Scopo: elimina una singola fattura dal lotto (lotto e fattura pre-fiscali).
//        La conferma dice esplicitamente che il documento viene CANCELLATO:
//        non esiste un archivio di fatture «estratte» (RD-7).
function eliminaFattura(row) {
  confirmAction({
    title: t('vendite.lotti.reset_fattura_header'),
    // Stesso avviso degli altri due percorsi di reset: la chiave e' una sola.
    message: `${t('vendite.lotti.reset_fattura_conferma')} `
      + t('vendite.lotti.reset_avviso_accrediti'),
    danger: true,
    acceptLabel: t('vendite.lotti.azione_reset_fattura'),
    onAccept: async () => {
      const res = await execute(() => eliminaFatturaDaLotto(props.lottoId, row.fattura_id))
      if (res !== null) {
        notify.success(t('vendite.lotti.reset_fattura_esito', {
          attivita: res?.updated_attivita ?? 0,
          riemesse: res?.riemesse_attivita ?? 0,
        }))
        await reloadFatture()
        emit('changed')
      }
    },
  })
}

// ---------------------------------------------------------------- stampa (C-8)
// Stampa/ristampa di una fattura via il motore documentale (sorgente FATTURA).
// La stampa è una LETTURA (I-4: legge le tabelle e renderizza, non edita):
// disponibile anche in sola lettura, a differenza delle azioni di governo.

// Scopo: anteprima PDF sincrona on-the-fly (nessun record, download immediato).
//        Render della fattura corrente (context builder FATTURA → template).
async function anteprimaFattura(row) {
  docStore.setSorgente(SORGENTE_CODES.FATTURA, row.fattura_id)
  const result = await execute(() => docStore.anteprima({}))
  if (result) downloadBlob(result.blob, result.fileName)
}

// Scopo: apre il dialog archivio documenti generati della fattura
//        (lista + download). Le ref del dialog sono dichiarate in testa
//        (prima del watch immediate che le resetta).
function apriDocumentiFattura(row) {
  pdfFatturaId.value = row.fattura_id
  pdfDialogVisible.value = true
}

// Scopo: apre il drawer di consultazione della fattura (documento a video).
//        Il drawer si sovrappone a questo: e' consultazione pura e alla
//        chiusura si torna al lotto senza ricaricare nulla.
function apriFattura(row) {
  fatturaDrawerId.value = row.fattura_id
  fatturaDrawerVisible.value = true
}

// Azioni di riga fattura: consultazione e stampa (anteprima + archivio) sempre
// disponibili (lettura); l'eliminazione dal lotto solo fuori sola-lettura, col
// permesso, e dentro il perimetro pre-fiscale. I gate usano il codice stabile
// (codice_interno), MAI la descrizione display.
function buildFatturaActions(row) {
  const actions = [
    {
      // Apre il documento a video (testata + righe + riepilogo IVA): fino a
      // ieri la fattura si poteva solo scaricare in PDF per sapere cosa c'e'
      // dentro. Prima voce del kebab perche' e' la consultazione, non
      // un'azione — le due voci di stampa restano sotto.
      key: 'apri',
      label: t('vendite.lotti.azione_apri_fattura'),
      icon: MANAGE_ICONS.INSPECT,
      command: () => apriFattura(row),
    },
    {
      key: 'anteprima',
      label: t('vendite.lotti.azione_anteprima_fattura'),
      icon: MANAGE_ICONS.PDF,
      command: () => anteprimaFattura(row),
    },
    {
      key: 'documenti',
      label: t('vendite.lotti.azione_documenti_fattura'),
      icon: MANAGE_ICONS.ARCHIVE,
      command: () => apriDocumentiFattura(row),
    },
  ]
  // Perimetro pre-fiscale, cioe' non numerato: DRAFT **o EMESSA**. Vale per la
  // fattura (allargato dal DB il 2026-08-02, D-T: restringere a DRAFT
  // nasconderebbe l'azione proprio nel caso che la motiva — la fattura critica
  // rimasta indietro) **e per il lotto** (slice 6-B del 2026-08-04: il DB ha un
  // codice dedicato, `E_LOTTO_NON_PRE_FISCALE`, quindi il caso lo considera
  // raggiungibile). Le due condizioni sono separate a DB e vanno lette
  // entrambe: guardare solo la riga rimetterebbe in scena il
  // pulsante-vicolo-cieco che questo cantiere ha appena tolto altrove.
  // Il presidio vero resta fiscale e sta a DB — qui si evita soltanto di
  // proporre un'azione destinata a fallire.
  const PRE_FISCALI = ['DRAFT', 'EMESSA']
  const fatturaPreFiscale = PRE_FISCALI.includes(row.stato_doc_fiscale_codice)
  const lottoPreFiscale = PRE_FISCALI.includes(lotto.value?.stato_doc_fiscale_codice)
  if (!isReadonly.value && canResetFattura.value && fatturaPreFiscale && lottoPreFiscale) {
    actions.push({
      key: 'elimina',
      label: t('vendite.lotti.azione_reset_fattura'),
      // ⭐ «Riporta in lavorazione», non «Elimina dal lotto» (rilievo di Tid,
      // 2026-08-21): quel nome descriveva il MECCANISMO e suggeriva uno
      // sgancio — «tolgo il documento dal lotto, poi lo rimetto in un altro» —
      // che non esiste. Il verbo si chiama ora come l'INTENZIONE, la stessa
      // del gemello sul lotto intero: questo va rifatto.
      // ⚠️ L'intenzione e' la stessa, l'effetto NO, e lo dice la conferma: qui
      // il lavoro rientra nel giro SUCCESSIVO, mentre sul lotto intero e' lo
      // stesso lotto a rigenerare. Icona `UNDO` come il gemello — stesso
      // verbo, granularita' diversa.
      // 📌 Il cestino se n'e' andato con la frase che lo motivava: «il
      // contenuto non e' recuperabile, `vendite.fatture` non e' storicizzata».
      // Misurato il 2026-08-21: `storicizza` e' TRUE su 16 fatture su 16, il
      // trigger `trg_fatture_z90_storico_upd_dlt` c'e', e `storico.fatture`
      // conserva 9 snapshot da DELETE. Il contenuto si recupera a DB.
      icon: MANAGE_ICONS.UNDO,
      severity: 'danger',
      command: () => eliminaFattura(row),
    })
  }
  return actions
}

function fatturaNumero(row) {
  if (!row.numero) return '—'
  const serie = row.serie ? `${row.serie} ` : ''
  return `${serie}${row.numero}`
}
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :dismissable="true"
    @update:visible="(v) => { if (!v) onClose() }"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :title="t('vendite.lotti.drawer_titolo')" icon="pi pi-server" />
    </template>

    <div class="app-drawer-content">
      <template v-if="contentReady && lotto">
        <DrawerEntityHeader>
          <Tag :value="lotto.codice" severity="secondary" />
          <span class="text-color-secondary">{{ lotto.tipo_lotto }}</span>
          <span v-if="lotto.competenza_mese" class="text-color-secondary">
            {{ displayDate(lotto.competenza_mese) }}
          </span>
          <template #status>
            <Tag :value="lotto.stato_lotto" :severity="statoLottoSeverity(lotto.stato_lotto)" />
          </template>
        </DrawerEntityHeader>

        <!-- Step corrente (stato doc fiscale del lotto). -->
        <div class="app-lotto-step">
          <span class="text-color-secondary">{{ t('vendite.lotti.step_corrente') }}:</span>
          <Tag :value="lotto.stato_doc_fiscale_descrizione ?? '—'" severity="info" />
          <span v-if="lotto.stato_operativo" class="text-color-secondary">· {{ lotto.stato_operativo }}</span>
        </div>

        <!-- Banner segnalazioni critiche (blocca l'avanzamento). -->
        <Message v-if="haSegnalazioniCritiche" severity="error" :closable="false" class="app-mt-1">
          {{ t('vendite.lotti.segnalazioni_bloccanti', { n: segnalazioni.critical_count }) }}
          <!-- Il banner dice QUANTE sono; il dettaglio sta in una scheda sola,
               e il link ci porta invece di chiedere all'operatore di cercarla.
               Apre già filtrata sulle critiche: sono quelle di cui parla. -->
          <Button
            link
            size="small"
            class="app-lotto-segn-link"
            :label="t('vendite.lotti.segnalazioni_apri')"
            @click="apriSegnalazioni" />
        </Message>


        <!-- Azioni di governo del lotto. Quali esistono, quali sono abilitate e
             perché no lo dice il BE (`available_actions`): qui si rende e si
             chiama. In sola lettura la barra resta vuota. -->
        <DrawerActionsBar
          :actions="drawerActions"
          :info-key="lotto?.stato_info_key || ''"
          :disabled="loading || azioniLoading"
        />

        <Tabs v-model:value="tabAttiva" class="app-mt-1">
          <TabList>
            <!-- ⚠️ «Documenti», non «fatture»: dal 2026-08 un lotto puo'
                 contenere anche NOTE DI CREDITO, e il verbo «numera» le numera
                 entrambe sui rispettivi registri (§12.4-bis.8 del brief nota di
                 credito). Un conteggio che dice «3 fatture» su 2 fatture e una
                 nota e' un numero giusto con il nome sbagliato. -->
            <!-- ⚠️ Il conteggio e' il TOTALE del server, non le righe caricate:
                 con la paginazione «(25)» su 137 documenti sarebbe la
                 dimensione della pagina spacciata per quantita'. -->
            <Tab value="fatture">{{ t('vendite.lotti.tab_documenti') }} ({{ listaDocumenti.totale.value }})</Tab>
            <Tab value="task">{{ t('vendite.lotti.tab_task') }} ({{ listaTask.totale.value }})</Tab>
            <Tab value="segnalazioni">{{ t('vendite.lotti.tab_segnalazioni') }}</Tab>
            <!-- ⭐ La quarta scheda risponde a una domanda che le altre tre non
                 fanno: le prime dicono COSA C'E' ORA, questa COSA E' SUCCESSO.
                 Il conteggio nell'etichetta dice se vale la pena entrare. -->
            <Tab value="storia">
              {{ t('vendite.lotti.tab_storia') }}
              <template v-if="giornaleTotale"> ({{ giornaleTotale }})</template>
            </Tab>
          </TabList>
          <TabPanels>
            <!-- ⭐ I TRE TAB SONO TRE LISTE CONFIGURABILI (seed 45/46/47, FE-2
                 del brief liste drawer lotto). Le colonne arrivano dal
                 catalogo: qui restano solo gli slot delle celle che hanno una
                 resa propria (Tag, icona errore, kebab). Aggiungere una
                 colonna e' ora un seed, non una riga di `.vue`. -->
            <TabPanel value="fatture">
              <!-- ⭐ Contenitore STANDARD delle liste: filtri a sinistra, azioni a
                   destra. Non un allineamento scritto a mano — `app-page-toolbar` e' lo
                   stesso di ogni pagina lista.
                   ⚠️ Sul piccolo schermo le icone collassano nel kebab da se':
                   `PageActionsBar` lo fa al breakpoint, non serve nulla qui. -->
              <div class="app-page-toolbar">
                <!-- Spaziatore: `space-between` con un figlio solo allineerebbe
                     a SINISTRA. Questa lista non ha filtri propri. -->
                <span class="app-page-filters" />
                <PageActionsBar :actions="barraDocumenti">
                  <template #suffix>
                    <ListaConfigStatusTag :dirty="azioniDocumenti.dirty.value" />
                  </template>
                </PageActionsBar>
              </div>
              <ListaConfigurabile
                ref="listaDocumentiRef"
                codice="vendite.lotto_fatture"
                data-key="fattura_id"
                :rows="listaDocumenti.righe.value"
                :total="listaDocumenti.totale.value"
                :loading="tabLoading || listaDocumenti.loading.value"
                :paginator-options="listaDocumenti.paginatorOptions.value"
                :page="listaDocumenti.page.value"
                :sort-field="listaDocumenti.sortField.value"
                :sort-order="listaDocumenti.sortOrder.value"
                @page="listaDocumenti.onPage"
                @sort="listaDocumenti.onSort"
                @config-loaded="listaDocumenti.onConfigLoaded"
              >
                <!-- Numero componibile serie+numero: il seed dichiara `numero`,
                     l'etichetta a video la compone il FE. -->
                <template #cell-numero="{ data }">{{ fatturaNumero(data) }}</template>
                <!-- ⚠️ La nota di credito non e' un'anomalia: severity neutra,
                     mai `danger` — e il totale negativo si mostra com'e',
                     perche' e' il documento a essere di segno opposto. -->
                <template #cell-natura_doc_descrizione="{ data }">
                  <Tag v-if="data.natura_doc_codice"
                    :value="data.natura_doc_descrizione || data.natura_doc_codice"
                    :severity="naturaDocSeverity(data.natura_doc_codice)" />
                  <span v-else>—</span>
                </template>
                <template #cell-stato_doc_fiscale_descrizione="{ data }">
                  <Tag :value="data.stato_doc_fiscale_descrizione ?? '—'" severity="info" />
                </template>
                <template #cell-stato_esecuzione="{ data }">
                  <span class="app-lotto-esecuzione-cella">
                    <Tag :value="data.stato_esecuzione" :severity="statoEsecuzioneFatturaSeverity(data.stato_esecuzione)" />
                    <!-- Il PERCHE' accanto al CHE COSA: senza, «ERRORE» e' una
                         bandiera senza messaggio. Il componente si nasconde da
                         solo quando non c'e' errore. -->
                    <ErroreRigaInfo
                      :messaggio="data.errore_messaggio"
                      :codice="data.errore_codice"
                      :quando="data.errore_quando"
                      :livello="data.errore_livello"
                      :bersagli="data.errore_bersagli || []"
                      :entita-corrente="{ tipo: 'FATTURA', id: data.fattura_id }"
                      :titolo="t('vendite.lotti.errore_documento_titolo')"
                    />
                  </span>
                </template>
                <!-- ⛔ LO SLOT SI CHIAMA `actions`, NON `cell-azioni`.
                     `ListaConfigurabile` rende la colonna delle azioni SOLO se
                     la config la dichiara **e** il caller fornisce lo slot
                     `#actions` (`haAzioni`).
                     🔴 Col nome sbagliato la condizione e' falsa e la colonna
                     non viene resa affatto: nessun kebab, e nessun errore da
                     nessuna parte.
                     ⚠️ `compact` va accettato: e' il flag con cui il BB
                     comprime le azioni quando lo spazio si stringe. -->
                <template #actions="{ data, compact }">
                  <RowActionsMenu :row="data" :actions="buildFatturaActions(data)" :force-compact="compact" />
                </template>
                <!-- Empty-state TRADOTTO: senza lo slot il BB lascia il default
                     PrimeVue, che e' in inglese. -->
                <template #empty>
                  <div class="app-empty-state"><i class="pi pi-inbox" /><p>{{ t('vendite.lotti.nessuna_fattura') }}</p></div>
                </template>
              </ListaConfigurabile>
            </TabPanel>

            <TabPanel value="task">
              <!-- ⭐ Contenitore STANDARD delle liste: filtri a sinistra, azioni a
                   destra. Non un allineamento scritto a mano — `app-page-toolbar` e' lo
                   stesso di ogni pagina lista, quindi queste tre si comportano come le
                   altre anche quando la regola cambia.
                   ⚠️ Sul piccolo schermo le icone collassano nel kebab da se':
                   `PageActionsBar` lo fa al breakpoint, non serve nulla qui. -->
              <!-- ⚠️ Il numero che rende ONESTO il filtro: il default nasconde
                   gli annullati (sul 6260 sono 80 righe su 90), e senza questa
                   riga un elenco filtrato e un elenco corto si leggono uguali. -->
              <Message
                v-if="esclusiTask > 0"
                severity="secondary"
                :closable="false"
                class="app-mb-1"
              >
                {{ t('vendite.lotti.task_esclusi', { n: esclusiTask }) }}
              </Message>

              <div class="app-page-toolbar">
                <div class="app-page-filters">
                  <!-- Filtro di AMPIEZZA, a sinistra come i filtri di ogni
                       lista. Non è il gemello del filtro gravità delle
                       segnalazioni: là si sceglie un livello, qui quanto si
                       guarda. -->
                  <SelectButton
                    v-model="ampiezzaTask"
                    :options="opzioniAmpiezzaTask"
                    option-label="label"
                    option-value="value"
                    :allow-empty="false"
                    size="small"
                  />
                </div>
                <PageActionsBar :actions="barraTask">
                  <template #suffix>
                    <ListaConfigStatusTag :dirty="azioniTask.dirty.value" />
                  </template>
                </PageActionsBar>
              </div>
              <ListaConfigurabile
                ref="listaTaskRef"
                codice="vendite.lotto_task_runs"
                data-key="id"
                :rows="listaTask.righe.value"
                :total="listaTask.totale.value"
                :loading="tabLoading || listaTask.loading.value"
                :paginator-options="listaTask.paginatorOptions.value"
                :page="listaTask.page.value"
                :sort-field="listaTask.sortField.value"
                :sort-order="listaTask.sortOrder.value"
                @page="listaTask.onPage"
                @sort="listaTask.onSort"
                @config-loaded="listaTask.onConfigLoaded"
              >
                <!-- La fase e' l'etichetta leggibile del passo; su un task senza
                     fase a catalogo si ripiega sul codice, che almeno lo
                     identifica. -->
                <template #cell-fase="{ data }">{{ data.fase || data.task_code }}</template>
                <template #cell-task_stato="{ data }">
                  <Tag :value="data.task_stato" :severity="statoTaskRunSeverity(data.task_stato)" />
                </template>
                <template #empty>
                  <div class="app-empty-state"><i class="pi pi-inbox" /><p>{{ t('vendite.lotti.nessun_task') }}</p></div>
                </template>
              </ListaConfigurabile>
            </TabPanel>

            <TabPanel value="segnalazioni">
              <div v-if="segnalazioni">
                <Message
                  v-if="segnalazioni.blocks_next_step"
                  severity="warn"
                  :closable="false"
                  class="app-mb-1"
                >
                  {{ t('vendite.lotti.blocca_step') }}
                </Message>

                <!-- ⚠️ Il numero che rende onesto l'elenco: senza, una lista che
                     mostra solo l'ultima corsa e una lista vuota si leggono
                     uguali. -->
                <Message
                  v-if="segnalazioniFuoriJob > 0"
                  severity="secondary"
                  :closable="false"
                  class="app-mb-1"
                >
                  {{ t('vendite.lotti.segn_fuori_job', { n: segnalazioniFuoriJob }) }}
                </Message>

                <!-- ⭐ Contenitore STANDARD delle liste: filtri a sinistra, azioni a
                     destra. Non un allineamento scritto a mano — `app-page-toolbar` e' lo
                     stesso di ogni pagina lista, quindi queste tre si comportano come le
                     altre anche quando la regola cambia.
                     ⚠️ Sul piccolo schermo le icone collassano nel kebab da se':
                     `PageActionsBar` lo fa al breakpoint, non serve nulla qui. -->
                <div class="app-page-toolbar">
                  <div class="app-page-filters">
                    <!-- Filtro per livello, a sinistra come i filtri di ogni
                         lista. Il CONTEGGIO sta nell'etichetta: dice se vale la
                         pena guardare quel livello. -->
                    <SelectButtonGravita
                      v-model="livelloSegnalazioni"
                      :options="opzioniLivello"
                    />
                  </div>
                  <PageActionsBar :actions="barraSegnalazioni">
                    <template #suffix>
                      <ListaConfigStatusTag :dirty="azioniSegnalazioni.dirty.value" />
                    </template>
                  </PageActionsBar>
                </div>
                <ListaConfigurabile
                  ref="listaSegnalazioniRef"
                  codice="vendite.lotto_segnalazioni"
                  data-key="riga_key"
                  :rows="listaSegnalazioni.righe.value"
                  :total="listaSegnalazioni.totale.value"
                  :loading="tabLoading || listaSegnalazioni.loading.value"
                  :paginator-options="listaSegnalazioni.paginatorOptions.value"
                  :page="listaSegnalazioni.page.value"
                  :sort-field="listaSegnalazioni.sortField.value"
                  :sort-order="listaSegnalazioni.sortOrder.value"
                  @page="listaSegnalazioni.onPage"
                  @sort="listaSegnalazioni.onSort"
                  @config-loaded="listaSegnalazioni.onConfigLoaded"
                >
                  <!-- Il livello col colore della sua gravita', la stessa scala
                       del filtro qui sopra. -->
                  <template #cell-livello="{ data }">
                    <Tag :value="data.livello" :severity="severitaLivelloSegnalazione(data.livello)" />
                  </template>
                  <!-- ⭐ IL MESSAGGIO, E IL MODO DI ARRIVARCI. Questa scheda e'
                       la superficie dove l'errore si legge DOPO — a giro
                       finito, magari il mattino seguente: e' il lettore che il
                       §1 del brief chiama «l'operatore cinque minuti dopo».
                       ⛔ Il gesto NON si costruisce su `fattura_id`, che pure
                       sta nella riga: quello e' il documento che ha FALLITO e
                       che l'operatore sta gia' guardando qui; il bersaglio e'
                       dove deve ANDARE.
                       ⭐ E dal `T-3b` (2026-08-24) `fattura_id` torna utile
                       proprio per QUESTO: il bersaglio porta ora anche il
                       documento su cui l'errore e' successo — che su una riga
                       e' la riga stessa — e passandolo come `entitaCorrente`
                       quel pulsante si nasconde. Non e' il gesto: e' cio' che
                       il gesto NON deve essere.
                       ⚠️ Le righe di LOTTO non hanno documento: li' `null`,
                       cioe' nessun filtro. -->
                  <template #cell-messaggio="{ data }">
                    <div class="app-segn-messaggio">
                      <span>{{ data.messaggio }}</span>
                      <BersaglioAzioni
                        :bersagli="data.target"
                        :entita-corrente="data.fattura_id ? { tipo: 'FATTURA', id: data.fattura_id } : null"
                      />
                    </div>
                  </template>
                  <!-- Sulle righe di LOTTO non c'e' documento: si mostra la
                       fase invece di un trattino muto. -->
                  <template #cell-documento_display="{ data }">
                    <span v-if="data.documento_display">{{ data.documento_display }}</span>
                    <span v-else class="text-color-secondary">{{ data.fase || t('vendite.lotti.segn_origine_lotto') }}</span>
                  </template>
                  <template #empty>
                    <div class="app-empty-state">
                      <i class="pi pi-check-circle" />
                      <p>{{ t('vendite.lotti.nessuna_segnalazione_livello') }}</p>
                    </div>
                  </template>
                </ListaConfigurabile>
              </div>
              <div v-else class="app-empty-state"><i class="pi pi-check-circle" /><p>{{ t('vendite.lotti.nessuna_segnalazione') }}</p></div>
            </TabPanel>
            <TabPanel value="storia">

              <!-- ⭐ LA STORIA DEL LOTTO — «cosa è successo, in che ordine».
                   Sorgente `script.vw_giornale_entita`: sul lotto rispondono
                   TRE registri (`EVENT_LOG`, `LOTTO_LOG`, `TASK_RUN`) più
                   `FATTURA_LOG` per i documenti che contiene.
                   ⭐ Le righe della FATTURA ci sono di proposito: il lotto
                   ripete «Esito fatture lotto · WARN» e il motivo sta sul
                   documento, perché la sua entità è la fattura. Un pannello
                   limitato al lotto sarebbe onesto e nel giorno in cui serve
                   non conterrebbe la risposta.
                   ⛔ Non è la scheda «Segnalazioni»: quella elenca i problemi
                   APERTI da risolvere, qui c'è anche ciò che è andato bene.
                   ⚠️ Sola lettura tranne il filtro: sta dentro
                   `app-drawer-content`, che diventa `.app-readonly` quando
                   l'area è in LETTURA — il toggle va quindi in `app-escape`, o
                   sarebbe visibile e non cliccabile (memoria
                   `feedback_app_escape_pannelli_processo`). -->
              <div class="app-page-toolbar">
                <div class="app-page-filters app-escape">
                  <!-- ⚠️ Nuova DOMANDA al server, non un filtro in memoria:
                       l'elenco è paginato. -->
                  <SelectButton
                    v-model="giornaleInfoVisibili"
                    :options="opzioniGiornaleInfo"
                    option-label="label"
                    option-value="value"
                    :allow-empty="false"
                  />
                </div>
              </div>

              <DataTable
                v-if="giornale.length"
                :value="giornale"
                data-key="riga_key"
                class="app-datatable app-datatable--inner"
                size="small"
                lazy
                :sort-field="giornaleSortField"
                :sort-order="giornaleSortOrder"
                @sort="onGiornaleSort"
              >
                <Column
                  field="quando"
                  sortable
                  :header="t('vendite.lotti.col_giornale_quando')"
                  style="width: 150px;"
                >
                  <template #body="{ data }">{{ displayTimestamp(data.quando) }}</template>
                </Column>
                <Column
                  field="gravita"
                  sortable
                  :header="t('vendite.lotti.col_giornale_gravita')"
                  style="width: 110px;"
                >
                  <template #body="{ data }">
                    <!-- ⚠️ `gravita` può essere NULL, e la vista lo dichiara
                         come il segnale che «un vincolo si è allargato e la
                         mappa è rimasta indietro»: si mostra il buco. È anche
                         il motivo per cui il filtro «non-INFO» la LASCIA
                         passare. -->
                    <Tag
                      :value="data.gravita ?? '—'"
                      :severity="gravitaGiornaleSeverity(data.gravita)"
                    />
                  </template>
                </Column>
                <!-- ⭐ DI CHI è la riga: è l'informazione che rende utile questo
                     pannello — «il lotto dice che è andata male, la fattura
                     dice perché». Senza, le due frasi sono indistinguibili. -->
                <Column :header="t('vendite.lotti.col_giornale_entita')" style="width: 140px;">
                  <template #body="{ data }">
                    <Tag
                      v-if="data.entity_type === 'FATTURA'"
                      :value="t('vendite.lotti.giornale_entita_fattura', { id: data.entity_id })"
                      severity="info"
                    />
                    <Tag
                      v-else
                      :value="t('vendite.lotti.giornale_entita_lotto')"
                      severity="secondary"
                    />
                  </template>
                </Column>
                <Column field="registro" :header="t('vendite.lotti.col_giornale_registro')" style="width: 120px;">
                  <template #body="{ data }">
                    <span class="app-drawer-header-muted">{{ data.registro }}</span>
                  </template>
                </Column>
                <Column field="cosa" :header="t('vendite.lotti.col_giornale_cosa')">
                  <template #body="{ data }">
                    <span class="app-giornale-cosa">{{ data.cosa }}</span>
                  </template>
                </Column>
                <Column :header="t('vendite.lotti.col_giornale_chi')" style="width: 120px;">
                  <template #body="{ data }">{{ data.user_insert ?? '—' }}</template>
                </Column>
              </DataTable>

              <!-- ⛔ QUATTRO vuoti diversi, e vanno detti diversi: «non sono
                   riuscito a chiederlo», «è successo tutto ed è routine», «è
                   successo tutto ed è stato superato», «non è successo
                   niente». I due di mezzo, su un elenco filtrato, sono il caso
                   in cui la distinzione conta di più — e sono anche i due che
                   un pannello frettoloso confonde con l'ultimo. -->
              <div v-else class="app-empty-state">
                <i :class="giornaleCaricato ? 'pi pi-check-circle' : 'pi pi-inbox'" />
                <p v-if="!giornaleCaricato">{{ t('vendite.lotti.giornale_non_caricato') }}</p>
                <p v-else-if="giornaleInfo > 0">
                  {{ t('vendite.lotti.giornale_solo_info', { n: giornaleInfo }) }}
                </p>
                <p v-else-if="giornaleRitirate > 0">
                  {{ t('vendite.lotti.giornale_solo_ritirate', { n: giornaleRitirate }) }}
                </p>
                <p v-else>{{ t('vendite.lotti.giornale_vuoto') }}</p>
              </div>

              <!-- Il conto di ciò che il filtro toglie. ⛔ È metà del mestiere
                   di nascondere: un elenco filtrato e uno completo si leggono
                   uguali, e «tre problemi» vs «tre problemi e 173 passi andati
                   bene» sono due schermate diverse. -->
              <p
                v-if="giornaleInfo > 0 && giornale.length"
                class="app-drawer-header-muted"
              >
                {{ t('vendite.lotti.giornale_info_nascoste', { n: giornaleInfo }) }}
              </p>
              <p
                v-if="giornaleRitirate > 0 && giornale.length"
                class="app-drawer-header-muted"
              >
                {{ t('vendite.lotti.giornale_ritirate', { n: giornaleRitirate }) }}
              </p>

              <!-- Il conto, quando la pagina non basta: un elenco troncato che
                   non lo dice si legge come completo. -->
              <p v-if="giornaleTotale > giornale.length" class="app-drawer-header-muted">
                {{ t('vendite.lotti.giornale_parziale', {
                  n: giornale.length, tot: giornaleTotale,
                }) }}
              </p>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </template>

      <FormFooter close-only @cancel="onClose" />
    </div>

    <!-- I tre dialog di export (uno per lista): scelta del formato e download.
       ⚠️ Fuori dal drawer nel markup ma dentro il componente: sono teleported
       e devono sopravvivere al cambio di tab. -->
  <ExportDialog
    v-model:visible="azioniDocumenti.exportDialogVisible.value"
    :loading="azioniDocumenti.exportLoading.value"
    @export="azioniDocumenti.onExportConfirm"
  />
  <ExportDialog
    v-model:visible="azioniTask.exportDialogVisible.value"
    :loading="azioniTask.exportLoading.value"
    @export="azioniTask.onExportConfirm"
  />
  <ExportDialog
    v-model:visible="azioniSegnalazioni.exportDialogVisible.value"
    :loading="azioniSegnalazioni.exportLoading.value"
    @export="azioniSegnalazioni.onExportConfirm"
  />

  <!-- Archivio documenti generati della fattura selezionata (sorgente FATTURA). -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialogVisible"
      :sorgente-code="SORGENTE_CODES.FATTURA"
      :sorgente-id="pdfFatturaId"
      :title="t('vendite.lotti.documenti_fattura_titolo')"
    />

    <!-- Consultazione della fattura a video (documento completo). -->
    <FatturaDrawer
      v-model:visible="fatturaDrawerVisible"
      :fattura-id="fatturaDrawerId"
    />

    <!-- FE-2: «Rendi definitive» non chiede «sei sicuro?», chiede CON QUALE
         DATA — e mostra il pavimento del sezionale, cioè il primo giorno in cui
         quei documenti possono prendere un numero. -->
    <NumerazioneDataDialog
      v-model:visible="numeraDialog.visible"
      :lotto-id="numeraDialog.lottoId"
      @conferma="confermaNumera"
    />
  </Drawer>
</template>

<style scoped>
/* Il messaggio e il suo gesto: testo sopra, pulsanti sotto. Affiancarli
   comprimerebbe la frase proprio dove serve leggerla — i nostri messaggi
   citano numeri di documento e la via d'uscita. */
.app-segn-messaggio {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  align-items: flex-start;
}

.app-lotto-step {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
}
.app-mt-1 {
  margin-top: 1rem;
}
.app-lotto-segn-link {
  padding: 0 0 0 0.35rem;
}
.app-lotto-segn-messaggio {
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
  /* I messaggi del DB portano DETAIL e HINT su righe proprie: schiacciarli
     toglierebbe la separazione fra «cos'è successo» e «cosa fare». */
  white-space: pre-line;
}
.app-lotto-esecuzione-cella {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}
.app-lotto-errori-testata {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.app-lotto-segnalazioni {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem 0;
}
.app-lotto-segn-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
</style>
