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
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import NumerazioneDataDialog from '../components/NumerazioneDataDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import BersaglioAzioni from '../../core/components/BersaglioAzioni.vue'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
import {
  exportDashboardCompetenzaCommesse,
  exportDashboardCompetenzaErrori,
  exportDashboardCompetenzaGruppi,
  exportDashboardCompetenzaResidui,
} from '../api/dashboardCompetenza'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import DashMesiSidebar from '../../core/components/dash/DashMesiSidebar.vue'
import DashMeseStepper from '../../core/components/dash/DashMeseStepper.vue'
import DonutTransito from '../../core/components/charts/DonutTransito.vue'
import Button from 'primevue/button'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ErroreRigaInfo from '../../core/components/ErroreRigaInfo.vue'
import { BERSAGLIO_TIPI } from '../../core/bersagli'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import CommessaGestioneDrawer from '../components/CommessaGestioneDrawer.vue'
import DocumentoDrawerHost from '../../core/components/DocumentoDrawerHost.vue'
import LottoDrawer from '../components/LottoDrawer.vue'
import { useDashMesiNav } from '../../core/composables/useDashMesiNav'
import { useReadonlyMode, useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { useDebouncedAction } from '../../core/composables/useDebouncedAction'
import { useJobPolling } from '../../core/composables/useJobPolling'
import { useChiaveGesto } from '../../core/composables/useChiaveGesto'
import { useRigheInGiro } from '../../core/composables/useRigheInGiro'
import { MANAGE_ICONS, READONLY_DOMAINS, STATUS_ICONS } from '../../core/constants'
import { MODO_DATA_DOCUMENTO, STATO_EMISSIONE_ATTIVITA, STATO_ESECUZIONE_LOTTO } from '../constants'
import { extractApiError } from '../../core/utils/apiError'
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { statoDocFiscaleSeverity, statoEsecuzioneLottoSeverity } from '../../core/utils/severity'
import { approvaCompetenza } from '../api/commesse'
import { getFatturazioneRun, runFatturazione } from '../api/lotti'
import { useDocumentoDrawer } from '../../core/composables/useDocumentoDrawer'
import { buildApriDocumentoAction } from '../dashboardAree'
import { useSelezioneToggle } from '../../core/composables/useSelezioneToggle'
import { checkRiportabili, riportaDaEmettere } from '../api/attivitaFatturabili'
import { misureOpzioni } from '../../core/misurePagina'
import {
  GRUPPI_CLIENTE_NON_DETERMINABILE,
  GRUPPI_REGISTRO_NON_RISOLVIBILE,
  STADIO_GRUPPI,
  STADIO_RESIDUI,
  useDashboardCompetenzaStore,
} from '../stores/dashboardCompetenza'

const { t, te } = useI18n()
const router = useRouter()
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

// Permesso del verbo che sblocca DAVVERO la commessa («Rendi pronta», dentro il
// drawer di governo). Serve qui, non solo là: senza, «Sblocca commessa»
// porterebbe in un drawer dove il verbo non compare — la capability lo NASCONDE
// a chi non ha l'azione della riga, `cambia_stato_commessa` — e la chiave
// (`SBLOCCA`) prometterebbe una via d'uscita che non esiste. Misurato in app il 2026-08-16: peggio di non offrire niente, perche'
// il vicolo cieco lo si scopre solo dopo averlo imboccato.
const { isAllowed: canCambiareStatoCommessa } = useActionPermission('cambia_stato_commessa')
const canNumerare = computed(() => canNumerareFatture.value && !areaReadonly.value)
// Gate del verbo «Riporta da emettere»: permesso DEDICATO
// (`config.azioni_processo` 33) + readonly d'area. ⛔ Non si riusa
// `reset_lotto_fattura_draft`: legare un verbo di RECUPERO a chi puo'
// CANCELLARE documenti sarebbe mettere insieme due mestieri diversi. Il gate e'
// lo stesso dell'endpoint, e qui serve perche' senza permesso la selezione non
// deve nemmeno comparire — una checkbox che porta a un 403 e' un vicolo cieco.
const { isAllowed: canRiportareDaEmettere } = useActionPermission('riporta_da_emettere')
const canRiportare = computed(() => canRiportareDaEmettere.value && !areaReadonly.value)
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
  gruppiCliente,
  gruppiRegistro,
  gruppiRegistri,
  gruppiPerimetroN,
  gruppiFiltriApi,
  gruppiClienti,
  gruppiSearch,
  residui,
  residuiCount,
  residuiPage,
  residuiPageSize,
  residuiLoading,
  residuiLoaded,
  residuiOrderBy,
  residuiOrderDir,
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
    // ⭐ E ULTIMO, dopo TUTTI i reset, si riapre sulla card di default: il mese
    //    nuovo si presenta come quello vecchio, con davanti la lista che si
    //    lavora.
    // ⛔ L'ordine non è estetico: qui sopra si azzera, e aprire prima
    //    significherebbe caricare una lista e poi passarle sopra l'azzeramento.
    //    Oggi `azzeraStatoGruppi` tocca la sola selezione e non farebbe danno —
    //    ma è una riga che può crescere, e allora il difetto sarebbe una fetch
    //    che sparisce senza fallire.
    apriStadioDefault()
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
    // La quota che CHIEDE UN'AZIONE dentro lo stadio. Contratto simmetrico: il
    // campo c'e' su ogni card e vale 0 dove non si applica — il FE rende, non
    // deduce quali stadi ce l'abbiano.
    nResidui: cella.n_residui ?? 0,
    valoreResidui: Number(cella.valore_residui ?? 0),
    // ⭐ La quota che un GIRO IN CORSO sta trattenendo, e che `nAttivita` NON
    // conta più (DB `20260909-67`). Stessa forma della quota residua: la card
    // deve dire due cose — quanto lavoro si può prendere, e quanto ce n'è che
    // non si può prendere perché è già in mano a un giro.
    // ⛔ Senza, il numero cala e nessuno sa di quanto: era il difetto del
    // collaudo 09-09 girato di 180 gradi (là la card diceva 4 su un elenco di
    // 3; qui direbbe 3 senza spiegare il quarto).
    nTrattenute: cella.n_trattenute ?? 0,
    valoreTrattenuto: Number(cella.valore_trattenuto ?? 0),
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
//
// ⭐ DUE MISURE, NON UNA (2026-08-20). `fatturato`/`daFatturare` sono il NETTO —
// la verita' contabile del mese, rettifiche comprese — e restano per le voci di
// riepilogo. `copertura*` e' la stessa cosa SENZA le rettifiche, ed e' l'unica
// che puo' finire in un grafico parte-su-tutto.
// ⚠️ Il motivo non e' il «101%» che si vedeva ad agosto: quello e' il sintomo
// innocuo. Il residuo era una somma con segno, quindi una nota di credito da
// emettere COMPENSAVA una fattura da emettere — con due importi pari il residuo
// va a zero e il grafico direbbe «niente da fare» con due documenti da produrre.
// La compensazione nascondeva lavoro. Rilievo in-app di Tid.
const totaliMese = computed(() => {
  const tot = meseCorrente.value?.totali ?? {}
  return {
    teorico: Number(tot.valore_teorico ?? 0),
    fatturato: Number(tot.valore_fatturato ?? 0),
    daFatturare: Number(tot.valore_da_fatturare ?? 0),
    nInRitardo: tot.n_in_ritardo ?? 0,
    coperturaFatturato: Number(tot.copertura_fatturato ?? 0),
    // Il residuo intero: e' il «fermo» del donut, e vale
    // `daAddebitare + daAccreditare`. Le due voci NON stanno fuori dal conto —
    // sono la sua lettura, non una nota a margine.
    coperturaDaFatturare: Number(tot.copertura_da_fatturare ?? 0),
    // ⭐ Due voci SIMMETRICHE: lo stesso verbo — produrre un documento — nei due
    // versi. Il segno vive nella parola («accreditare») e nel colore, mai nel
    // numero: e' la regola §5.4 del pannello merce, dove un importo negativo a
    // video si legge come un guasto anche quando descrive il mondo com'e'.
    daAddebitare: Number(tot.copertura_da_addebitare ?? 0),
    daAccreditare: Number(tot.copertura_da_accreditare ?? 0),
  }
})

const nErroriMese = computed(() => meseCorrente.value?.n_errori ?? 0)

// Mese del titolo di pagina. ⚠️ `Intl.DateTimeFormat(..., {month:'long'})` in
// italiano rende «agosto» minuscolo: corretto in una frase, sbagliato in un
// titolo. La maiuscola si mette QUI e non nel dizionario, o servirebbero dodici
// stringhe tradotte a mano al posto di una formattazione che gia' conosce la
// lingua dell'utente.
const meseTitolo = computed(() => {
  const nome = nomiMesi.value[meseIdx.value] ?? ''
  return nome.charAt(0).toUpperCase() + nome.slice(1)
})

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

// Scopo: carica la pagina corrente dei RESIDUI del mese (drill-down della card
//        «Emesse non fatturate»: le attivita' su cui si preme «Riporta da
//        emettere»).
async function loadResidui() {
  try {
    await store.fetchResidui(competenzaCorrente.value)
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Ogni card scende sull'unita' del PROPRIO verbo: «Da emettere» sui gruppi
// fatturabili (si fattura un documento), «Emesse non fatturate» sui residui (si
// riporta un'attivita'), le altre sulle commesse. Un solo punto di smistamento,
// cosi' non puo' capitare che una card carichi una lista e ne mostri un'altra —
// ed e' anche l'unico posto da toccare quando una card cambia unita'.
function loadDrillDown() {
  if (stadioSelezionato.value === STADIO_GRUPPI) return loadGruppi()
  if (stadioSelezionato.value === STADIO_RESIDUI) return loadResidui()
  return loadCommesse()
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

// ── Le due liste della pagina stanno in TAB, non impilate ────────────────
//
// 🔴 PRIMA ERANO SOVRAPPOSTE, e il difetto era di lettura: il pannello errori
//    apriva il mese (giusto), ma poi restava SOPRA e spingeva in basso l'area
//    che l'operatore selezionava — clicchi «Da emettere» e la tua lista compare
//    sotto un blocco che non stavi guardando. Rilievo di Tid, 2026-08-24.
//
// ⭐ La regola e' «in primo piano cio' che hai scelto»: il tab dell'AREA e' il
//    primo, e la selezione di uno stadio ce lo porta davanti da sola. Gli
//    errori restano a un click, con il loro conteggio sempre visibile
//    nell'etichetta — non spariscono, smettono di intromettersi.
//
// ⚠️ I due tab ci sono SEMPRE, anche a zero errori. Un tab che appare e
//    scompare col dato farebbe saltare il layout a ogni cambio mese, ed e' lo
//    stesso difetto un gradino piu' in la': «zero errori nel mese» e'
//    un'informazione, non un motivo per cambiare la forma della pagina.
const TAB_AREA = 'area'
const TAB_ERRORI = 'errori'
// ⭐ SI APRE SULL'AREA, non sugli errori (Tid, 2026-09-09). Vedi
//    `apriStadioDefault`: adesso una card è sempre scelta, quindi il tab
//    dell'area ha sempre qualcosa da mostrare — che è la premessa che mancava.
const tabAttiva = ref(TAB_AREA)

// Scopo: click sul corpo di una card = SELEZIONE ESCLUSIVA dello stadio.
//
// ⛔ NON e' un toggle, e non deve tornare a esserlo. Un secondo click sulla
//    stessa card chiudeva la lista: la card si comportava da interruttore, e
//    qui il difetto era piu' grave che sulla Situazione aperta — quella ha la
//    card «Tutte le aree» per tornare indietro, questa non ha NESSUN gesto di
//    ritorno, quindi il toggle-off era l'unico modo di svuotare la pagina e
//    ri-cliccare l'unico modo di riempirla. Rilievo in-app di Tid.
//    Stessa regola gia' scritta in `SituazioneApertaView.selezionaArea`
//    («selezione esclusiva, non piu' toggle»): qui era rimasta indietro.
//
// ⚠️ Ma il secondo click NON e' un no-op come li', ed e' la sola differenza:
//    questa pagina ha i TAB, e la regola «in primo piano cio' che hai scelto»
//    vale anche quando la selezione non cambia — chi e' passato al tab errori
//    e ri-clicca la propria card si aspetta di rivedere la propria lista.
// ⛔ Senza ricaricare, pero': una fetch sulla card gia' scelta perderebbe
//    pagina, ordinamento, filtri e le spunte gia' messe dall'operatore, che e'
//    lavoro suo — e su «Da emettere» sono le righe che sta per fatturare.
// Scopo: ⭐ LA CARD CHE SI APRE DA SOLA — «Da emettere» (Tid, 2026-09-09).
//
// ⭐ Perché quella: è l'unica card AZIONABILE del funnel — è lì che si preme
//    «Fattura» — ed è la domanda con cui si apre un mese di competenza. Le
//    altre si guardano; questa si lavora.
// ⚠️ `STADIO_GRUPPI` **è** `'DA_EMETTERE'`: si usa la costante e non il
//    letterale, che in questo file compare già scritto a mano due volte.
//
// ⛔ NON passa da `selezionaStadio`, e la differenza è una sola riga: quella
//    fa `scrollIntoView`, giusto dopo un CLICK e sbagliato all'apertura o al
//    cambio mese — la pagina scenderebbe da sola sotto le card che l'operatore
//    stava guardando.
// ⚠️ Idempotente: se una card è già scelta non la sostituisce. Serve perché
//    `onActivated` scatta a ogni rientro in foreground, e la scelta
//    dell'operatore è sua (memoria feedback_keepalive_onactivated).
function apriStadioDefault() {
  if (stadioSelezionato.value) return
  stadioSelezionato.value = STADIO_GRUPPI
  tabAttiva.value = TAB_AREA
  loadDrillDown()
}

function selezionaStadio(stadio) {
  const cambiaStadio = stadioSelezionato.value !== stadio
  if (cambiaStadio) {
    store.resetCommesse()
    azzeraStatoGruppi()
    // ⚠️ E la selezione dei residui: e' stato dell'operatore legato a UNA card, e
    //    sopravvivere al cambio di card la renderebbe invisibile ma ancora
    //    contata nel pulsante.
    selezioneResidui.value = []
    stadioSelezionato.value = stadio
  }
  // ⭐ Scegliere un'area la porta davanti: e' il senso della modifica.
  tabAttiva.value = TAB_AREA
  if (cambiaStadio) loadDrillDown()
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

// ⛔ QUI C'ERA UN `watch` CHE RIPORTAVA AL TAB ERRORI a ogni cambio mese, e la
//    sua ragione era scritta: «nessuna area resta selezionata, il tab dell'area
//    mostrerebbe il vuoto». ⭐ Quella premessa non c'è più — `apriStadioDefault`
//    ne sceglie sempre una — e una regola che sopravvive alla propria ragione
//    combatte con chi l'ha sostituita: il tab sarebbe tornato agli errori
//    subito dopo che il default ha aperto l'area.
// ⚠️ Gli errori non si perdono: il badge del mese resta acceso e il tab è a un
//    click (rilievo di Tid, 2026-09-09).

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

// Scopo: ⭐ IL DOCUMENTO È TRATTENUTO DA UN LOTTO VIVO — il verdetto arriva in
//        riga (`20260909-24`), non si ricava qui.
//
// ⛔ E NON SI RICAVA DA `ultimo_esito`, che sembrava bastare e risponde giusto
//    PER CASO: misurato il 2026-09-08, due documenti su tre in `DA_EMETTERE`
//    avevano `COMPLETED` col lotto ANNULLATO — cioè erano liberi. Dedurlo qui
//    avrebbe tenuto bloccato per sempre il contenuto di ogni lotto annullato,
//    e sarebbe stata la seconda sede di «questo documento è in gioco?».
// ⚠️ `labelOrCode` e non `t()` secco: il vocabolario dei motivi vive a
//    database ed è estensibile — una chiave che i locales non conoscono ancora
//    mostra il codice grezzo invece del vuoto.
function motivoTrattenuto(row) {
  if (!row.emissione_blocco_reason) return undefined
  return labelOrCode(
    t, te, row.emissione_blocco_reason_key, row.emissione_blocco_reason,
  )
}

// Scopo: si può PRENDERE questa riga per fatturarla? Due blocchi diversi, e
//        vanno tenuti distinti perché hanno due vie d'uscita diverse: la
//        testata non emittibile si sblocca cambiando stato alla commessa, il
//        documento trattenuto si sblocca togliendolo dal giro del suo lotto.
function isGruppoPrendibile(row) {
  return isGruppoEmittibile(row) && !row.emissione_blocco_reason
}

// Scopo: il lotto che trattiene, come BERSAGLIO. ⭐ La frase dice cosa fare, il
//        bersaglio ci porta: senza, l'operatore ricopia un codice e poi lo
//        cerca a mano.
// ⛔ Elenco vuoto quando non c'è: `BersaglioAzioni` non disegna niente — mai un
//    pulsante che porta in un vicolo cieco (§4.3).
function bersagliLottoTrattiene(row) {
  return row.emissione_blocco_lotto_id
    ? [{ type: BERSAGLIO_TIPI.LOTTO, id: row.emissione_blocco_lotto_id }]
    : []
}

// Gruppi attualmente IN LAVORAZIONE, per GIRO: `jobId → gruppo_key[]`.
// ⭐ La macchina (mappa per giro + sostituzione invece di mutazione, con le due
//    trappole che ne sono la ragione) e' stata estratta il 2026-08-27 nel BB
//    `useRigheInGiro`: era la stessa che serviva alla lista Lotti per i lotti
//    dentro un giro di numerazione. Qui resta il solo nome di dominio.
// ⚠️ Dichiarato QUI e non piu' accanto ai verbi: alimenta `gruppiSelezionabili`
// poche righe sotto, e in `<script setup>` una const usata piu' in alto e' una
// TDZ silenziosa (memoria feedback_vue_watch_immediate_tdz).
const {
  chiaviInGiro: gruppiInCorso,
  marca: marcaGiro,
  smarca: smarcaGiro,
} = useRigheInGiro()

// Selezionabile = testata emittibile E non gia' presa da un giro vivo. Il
// secondo pezzo e' la difesa contro la sovrapposizione parziale, e deve stare
// QUI perche' il backend non ce l'ha: due giri con perimetri che si
// intersecano ([A,B] poi [B,C]) sono due job distinti e nessuno li ferma —
// B verrebbe sottomesso due volte e il secondo giro lo troverebbe gia' preso,
// riportandolo come «non servito» per una ragione che non e' un problema.
const gruppiSelezionabili = computed(
  () => gruppi.value.filter(
    (row) => isGruppoPrendibile(row) && !gruppiInCorso.value.has(row.gruppo_key),
  ),
)

// Scopo: elenco leggibile in un toast/conferma — primi 3 per esteso, il resto
//        riassunto da «…». Stessa soglia del compositore BE
//        (_MAX_GRUPPI_NEL_MESSAGGIO): un toast non regge un elenco puntato.
function elencoTroncato(items, fmt, sep = ', ') {
  return items.slice(0, 3).map(fmt).join(sep) + (items.length > 3 ? '…' : '')
}

const selezioneGruppi = ref([])
const {
  // ⭐ IL PREDICATO DELLA CASELLA VIENE DAL BB, non da una copia. Fino al
  //    2026-09-12 il `:disabled` leggeva `isGruppoPrendibile` — che non sa
  //    niente dei giri in corso — mentre il guard del BB e il prune leggevano
  //    `gruppiSelezionabili`, che li esclude. Risultato in-app (rilievo di
  //    Tid): riga con la rotella «in lavorazione» e casella ACCESA; il click
  //    non selezionava (il guard tiene) ma non lo diceva — un gesto offerto
  //    e rifiutato in silenzio. Il contratto del BB e' scritto in testa al
  //    file: «`:disabled` viene da `isSelectable`». Una seconda sede della
  //    stessa regola era gia' divergente.
  isSelectable: isGruppoSelezionabile,
  isSelected: isGruppoSelezionato,
  toggleRow: toggleGruppo,
  // ⚠️ La terna «in pagina», non `toggleAll`/`anySelected`: questa lista e'
  //    PAGINATA e la selezione vive attraverso le pagine. Vedi il blocco in
  //    fondo a `useSelezioneToggle`.
  allInPagina: tuttiGruppiSelezionati,
  anyInPagina: alcuniGruppiSelezionati,
  toggleAllInPagina: toggleTuttiGruppi,
} = useSelezioneToggle({
  selected: selezioneGruppi,
  selezionabili: gruppiSelezionabili,
  rowKey: 'gruppo_key',
})

// La selezione sopravvive alle pagine e ai reload DI PROPOSITO — ma una riga
// selezionata puo' smettere di essere selezionabile sotto i piedi: tornare
// BLOCCATA a un refresh (un collega riporta la commessa in BOZZA), oppure
// entrare in un giro avviato nel frattempo. Senza questo prune resterebbe
// spuntata con la checkbox disabilitata — il guard del BB rende il de-toggle un
// no-op — quindi non rimovibile, contata nel pulsante e ri-sottomessa a ogni
// giro. Il prune toglie dalla selezione le chiavi che la pagina dichiara non
// piu' selezionabili: la checkbox si spegne a video, che e' la comunicazione
// onesta.
// ⚠️ Sorvegliati ENTRAMBI i motivi: il secondo non dipende da una fetch, quindi
// un watch sul solo `gruppi` non scatterebbe quando parte un giro.
watch([gruppi, gruppiInCorso], ([rows]) => {
  const nonSelezionabili = new Set(
    (rows ?? [])
      // ⚠️ `isGruppoPrendibile` e non `isGruppoEmittibile`: dal 2026-09-09 i
      //    motivi di blocco sono DUE, e il prune deve conoscerli entrambi. Con
      //    il solo primo, una riga che diventa TRATTENUTA mentre è spuntata
      //    resta selezionata con la casella spenta — non rimovibile, contata
      //    dal pulsante e ri-sottomessa: il contatore che mente, che è
      //    precisamente il difetto per cui questo prune esiste.
      .filter((r) => !isGruppoPrendibile(r) || gruppiInCorso.value.has(r.gruppo_key))
      .map((r) => r.gruppo_key),
  )
  if (!nonSelezionabili.size) return
  selezioneGruppi.value = selezioneGruppi.value.filter(
    (r) => !nonSelezionabili.has(r.gruppo_key),
  )
})

// Lotti prodotti dalle emissioni mirate: sono N per giro, non uno (un gruppo
// con righe di tipo doc fiscale diverso finisce in lotti diversi). Alimentano
// l'aggancio «vai al lotto» — senza, l'operatore dovrebbe cercarsi a mano nella
// lista lotti il contenitore appena creato per andare a numerarlo.
// Ogni voce porta la COMPETENZA del giro che l'ha prodotta: con piu' giri in
// volo un giro puo' concludersi DOPO che l'operatore ha cambiato mese, e i suoi
// link si appoggerebbero al mese sbagliato — su una schermata il cui passo
// successivo e' numerare, cioe' un atto fiscale, e' un'informazione falsa nel
// punto peggiore. Non si cancellano al cambio mese: ricompaiono tornando sul
// loro.
const lottiEmessi = ref([])

const lottiEmessiVisibili = computed(
  () => lottiEmessi.value.filter((l) => l.competenza === competenzaCorrente.value),
)

// Scopo: registra i lotti di un giro concluso senza duplicati (`lotto_id` e'
//        univoco) e senza perdere quelli dei giri precedenti — con piu' giri
//        concorrenti sovrascrivere significherebbe buttare via l'aggancio del
//        giro che ha finito per primo.
function registraLottiEmessi(lotti, competenza) {
  const gia = new Set(lottiEmessi.value.map((l) => l.lotto_id))
  const nuovi = lotti
    .filter((l) => !gia.has(l.lotto_id))
    .map((l) => ({ ...l, competenza }))
  if (!nuovi.length) return
  lottiEmessi.value = [...lottiEmessi.value, ...nuovi]
}

// Scopo: azzera lo stato di selezione che vive nella view (lo store azzera il
//        suo). Dichiarata come `function` per essere invocabile dai callback
//        registrati piu' in alto (nessun watch immediate la chiama in setup:
//        `useDashMesiNav` scatta solo su azione utente).
// ⚠️ NON tocca `lottiEmessi` ne' le marcature dei giri vivi: i primi sono
//    filtrati per mese e devono sopravvivere all'andata e ritorno, le seconde
//    appartengono a job che stanno ancora girando — spegnerle qui le farebbe
//    sparire da una lista in cui il lavoro e' ancora in corso.
function azzeraStatoGruppi() {
  selezioneGruppi.value = []
}

// ─────────────────────────────────────────────────────────────────────────
// RESIDUI: selezione e verbo «Riporta da emettere».
// ⭐ Ogni riga della lista e' selezionabile per costruzione: il BACKEND filtra
//    `motivo_non_fatturata = 'RESIDUO'`, cioe' esattamente il perimetro del
//    verbo. Non si ri-filtra qui — sarebbe una seconda implementazione di un
//    predicato che vive nel database, e la divergenza sarebbe silenziosa.
const selezioneResidui = ref([])
const residuiSelezionabili = computed(() => residui.value ?? [])
const {
  // Stesso contratto della lista sorella: la casella legge `isSelectable`.
  // Oggi ogni residuo e' selezionabile per costruzione, quindi non cambia
  // niente a video — ma il giorno che un motivo di esclusione entra in
  // `residuiSelezionabili`, la casella lo segue senza una seconda modifica.
  isSelectable: isResiduoSelezionabile,
  isSelected: isResiduoSelezionato,
  toggleRow: toggleResiduo,
  // ⛔ La terna «in pagina», e la prima stesura aveva preso quella sbagliata:
  //    `toggleAll` SOSTITUISCE la selezione con la pagina corrente, quindi
  //    spuntare «tutti» a pagina 2 buttava via quanto spuntato a pagina 1 —
  //    in silenzio, e con la lista sorella dei gruppi cento righe piu' su che
  //    faceva gia' la cosa giusta.
  allInPagina: tuttiResiduiSelezionati,
  anyInPagina: alcuniResiduiSelezionati,
  toggleAllInPagina: toggleTuttiResidui,
} = useSelezioneToggle({
  selected: selezioneResidui,
  selezionabili: residuiSelezionabili,
  rowKey: 'attivita_fatturabile_id',
})

const residuiSortOrder = computed(() => (residuiOrderDir.value === 'desc' ? -1 : 1))

// Scopo: paginazione della lista residui. La selezione NON si azzera al cambio
//        pagina: le chiavi sono di dominio, non indici di riga, e la selezione
//        si compone su piu' pagine.
function onResiduiPage(event) {
  store.applyResiduiPage(event)
  loadResidui()
}

function onResiduiSort(event) {
  store.applyResiduiSort(event)
  residuiPage.value = 1
  loadResidui()
}

// Scopo: l'etichetta del motivo. ⚠️ `labelOrCode`: il vocabolario lo decide
//        il DB ed e' gia' cambiato due volte (quattro valori col `20260826-54`,
//        tre dal `20260912-36`), quindi un valore nuovo deve mostrarsi COM'E'
//        invece di sparire — mai il path della chiave a video, mai una cella
//        vuota. ⚠️ La chiave e' costruita dinamicamente: il cancello i18n non
//        la vede (punto cieco dichiarato), e' il ripiego a renderla visibile.
// Scopo: l'etichetta di un motivo OSTATIVO (quelli di `riportabili/`).
// ⭐ Il patto dei tre livelli: il DB emette l'indirizzo (`reason_key`), il BE lo
//    trasporta intatto, il FE lo risolve. Qui non si traduce un codice in una
//    frase — si risolve l'indirizzo che arriva, e se il vocabolario cresce la
//    frase nuova compare senza toccare il frontend. Il ripiego e' il `codice`,
//    mai il path della chiave e mai una cella vuota.
function motivoOstacoloLabel(motivo) {
  return labelOrCode(t, te, motivo?.reason_key ?? '', motivo?.codice ?? '—')
}

function motivoLabel(codice) {
  if (!codice) return '—'
  return labelOrCode(
    t, te,
    `vendite.dashboard_competenza.motivo_${String(codice).toLowerCase()}`,
    codice,
  )
}

const riportoInCorso = ref(false)

// Scopo: «Riporta da emettere» sulle righe spuntate — rimette il lavoro in coda
//        di fatturazione. Sincrono: due scritture e una transazione lato DB,
//        nessun job da seguire.
// ⚠️ La conferma c'e' anche se l'azione e' REVERSIBILE (si rifattura e si e' al
//    punto di prima): non protegge da un danno, dichiara quante righe sta per
//    toccare — un verbo di massa che parte al primo click su una lista paginata
//    e' il modo di riportare indietro piu' di quanto si e' guardato.
function riportaSelezionati() {
  const righe = [...selezioneResidui.value]
  if (!righe.length) return
  confirmAction({
    header: t('vendite.dashboard_competenza.riporta_header'),
    message: t('vendite.dashboard_competenza.riporta_conferma', { n: righe.length }),
    acceptLabel: t('vendite.dashboard_competenza.riporta_header'),
    onAccept: async () => {
      riportoInCorso.value = true
      try {
        const ids = righe.map((r) => r.attivita_fatturabile_id)
        // ⭐ SI RI-GUARDA PRIMA DI AGIRE, ed e' il catalogo a chiederlo: il
        //    codice `E_ATTIVITA_GIA_DA_EMETTERE` porta scritto che incontrarlo
        //    significa che l'elenco mostrato era invecchiato, e che il verbo va
        //    gate-ato sui motivi invece di essere proposto sempre. Fra il
        //    momento in cui la pagina si e' caricata e questo click puo' essere
        //    passato un giro di fatturazione, o un altro operatore.
        // ⚠️ Senza questo passo il rifiuto arriverebbe comunque — la madre DB
        //    non si fida di nessuno — ma come UN errore per l'intero elenco,
        //    che e' atomico: l'operatore non saprebbe QUALE riga lo ha fermato
        //    ne' perche', e riproverebbe.
        const check = await execute(() => checkRiportabili(ids))
        if (check === null) return
        const ostacoli = check?.motivi ?? []
        if (ostacoli.length) {
          notify.warn(t('vendite.dashboard_competenza.riporta_ostacoli', {
            n: ostacoli.length,
            motivo: motivoOstacoloLabel(ostacoli[0]),
          }))
          // L'elenco era vecchio: si azzera e si ri-legge, invece di lasciare
          // in mano una selezione che si e' appena dimostrata falsa.
          selezioneResidui.value = []
          await Promise.all([loadResidui(), store.fetchMensile()])
          return
        }
        const res = await execute(() => riportaDaEmettere(ids))
        // ⚠️ `res !== null` e non `if (res)`: un envelope valido puo' essere
        //    falsy, e `useApiHandler` restituisce `null` SOLO in errore. Con
        //    `if (res)` un esito legittimo verrebbe scambiato per un fallimento.
        if (res === null) return
        const d = res ?? {}
        const riportate = Number(d.riportate ?? 0)
        if (riportate > 0) {
          notify.success(t('vendite.dashboard_competenza.riporta_esito', {
            riportate,
            riemesse: Number(d.riemesse_attivita ?? 0),
          }))
        } else {
          // ⛔ Zero riportate non e' un successo da annunciare in verde: vuol
          //    dire che l'elenco a schermo era invecchiato.
          notify.warn(t('vendite.dashboard_competenza.riporta_nulla'))
        }
        selezioneResidui.value = []
        // Il lavoro e' uscito dai residui ed e' rientrato in «Da emettere»:
        // vanno ricaricate ENTRAMBE le facce, o la card resta a raccontare il
        // minuto prima.
        await Promise.all([loadResidui(), store.fetchMensile()])
      } finally {
        riportoInCorso.value = false
      }
    },
  })
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

// Scopo: cambio di QUALUNQUE filtro della lista gruppi — riparte da pagina 1
//        (le pagine successive appartengono al perimetro precedente) e azzera
//        la selezione.
// ⚠️ L'azzeramento della selezione non e' prudenza: e' la regola che regge il
//    verbo. La selezione sopravvive al cambio PAGINA di proposito (le chiavi
//    sono di dominio, non indici di riga), ma al cambio di PERIMETRO no —
//    altrimenti si fattura roba che non si ha davanti, che e' esattamente
//    l'incidente da cui nasce tutto questo cantiere.
// Una sede sola per i tre filtri (tipo, cliente, ricerca): tre copie di queste
// tre righe sarebbero tre occasioni perche' una si dimentichi la selezione.
function applicaFiltroGruppi() {
  gruppiPage.value = 1
  selezioneGruppi.value = []
  loadGruppi()
}

// Debounce della ricerca libera (BB `useDebouncedAction`): ritardo standard e,
// soprattutto, cleanup su unmount/deactivate — un timer che scatta su un tab in
// background ricaricherebbe una lista che l'operatore ha lasciato.
const onGruppiSearchInput = useDebouncedAction(applicaFiltroGruppi)

// Voci del filtro CLIENTE (facet dal BE, sul perimetro del mese/stadio).
// L'etichetta porta SEMPRE il codice BA accanto alla ragione sociale, e non e'
// decorazione: lo stesso soggetto puo' avere piu' alberi di billing account
// — anche sotto emittenti diversi — con nome e codice fiscale identici, e
// quegli alberi finiscono su fatture diverse. Senza il codice la tendina
// mostrerebbe due voci uguali senza modo di distinguerle.
const opzioniCliente = computed(() => {
  const voci = gruppiClienti.value.map((c) => {
    // Cliente non determinabile (padre fuori scope): voce esplicita col suo
    // conteggio, non una riga che sparisce. E' la riga che sfugge — il caso da
    // cui nasce il filtro — e nasconderla sarebbe il difetto, non il rimedio.
    if (c.ba_fatturazione_id === null || c.ba_fatturazione_id === undefined) {
      return {
        value: GRUPPI_CLIENTE_NON_DETERMINABILE,
        label: t('vendite.dashboard_competenza.cliente_non_determinabile', { n: c.n_gruppi }),
      }
    }
    const nome = c.cliente_display || t('vendite.dashboard_competenza.cliente_senza_nome')
    const codice = c.ba_codice_fatturazione
    return {
      value: c.ba_fatturazione_id,
      label: `${codice ? `${nome} — ${codice}` : nome} (${c.n_gruppi})`,
    }
  })
  return [
    {
      value: null,
      label: t('vendite.dashboard_competenza.cliente_tutti', {
        n: gruppiClienti.value.reduce((acc, x) => acc + Number(x.n_gruppi ?? 0), 0),
      }),
    },
    ...voci,
  ]
})

// Voci del filtro SEZIONALE (facet dal BE, stesso perimetro base delle altre
// due tendine: deve restare possibile cambiare sezionale senza prima azzerare
// il filtro alla cieca).
// ⚠️ La somma dei conteggi puo' SUPERARE il numero di gruppi del perimetro, e
// non e' un errore: un gruppo che tocca due sezionali e' contato — e trovato —
// sotto entrambi. Per questo la voce «Tutti» non somma le voci: «Tutti (46)»
// starebbe sopra una lista di 39 righe.
// ⛔ E NEMMENO dal `riepilogo`, che e' la prima cosa che viene in mente e che
// SEGUE i filtri: scelto «Back-office», la voce «Tutti» scenderebbe a 32 —
// cioe' direbbe 32 di un'opzione che, premuta, ne mostra 39. Il numero arriva
// dal BE calcolato sul perimetro BASE, che e' lo stesso della facet.
// ⚠️ La tendina dei CLIENTI somma le sue voci e fa bene: li' ogni gruppo sta
// sotto una voce sola. La differenza non e' fra le due tendine, e' fra
// partizione e appartenenza multipla.
const opzioniRegistro = computed(() => {
  const voci = gruppiRegistri.value.map((r) => {
    if (r.registro_id === null || r.registro_id === undefined) {
      return {
        value: GRUPPI_REGISTRO_NON_RISOLVIBILE,
        label: t('vendite.dashboard_competenza.registro_non_risolvibile', { n: r.n_gruppi }),
      }
    }
    return {
      value: r.registro_id,
      label: `${r.codice || r.descrizione || r.registro_id} (${r.n_gruppi})`,
    }
  })
  return [
    {
      value: null,
      label: t('vendite.dashboard_competenza.registro_tutti', {
        n: gruppiPerimetroN.value,
      }),
    },
    ...voci,
  ]
})

// Scopo: etichetta leggibile di una `gruppo_key` NUDA — quella che l'esito del
//        job riporta (gruppi «fatturati altrove», gruppi non serviti), dove il
//        BE manda le sole chiavi. La chiave e' `<TIPO>:<uuid>`: scritta in un
//        toast non dice niente a nessuno. La riga a video ce l'ha ancora (il
//        lookup gira PRIMA del reload post-azione), quindi si riusa lo stesso
//        `riferimento` che la lista mostra nella colonna «Gruppo».
//
// ⭐ Il `ripiego` e' un PARAMETRO perche' i due percorsi hanno in mano cose
//    diverse quando la riga non c'e' piu': l'esito «non serviti» porta anche il
//    codice commessa, «fatturati altrove» le sole chiavi. Senza, il toast dei
//    non serviti nominava la COMMESSA mentre la lista sopra nomina il
//    DOCUMENTO — lo stesso gruppo con due nomi a seconda di dove lo si legge, e
//    la commessa che «sembra un valore legittimo» e' esattamente la forma di
//    difetto corretta a DB il 2026-09-01
//    (brief-db-riferimento-gruppi-lateral-costosa §3).
// ⚠️ Non passarla mai come `fmt` nudo a `elencoTroncato`: quello fa `.map(fmt)`,
//    che passerebbe l'INDICE come `ripiego`.
function etichettaGruppoKey(key, ripiego = null) {
  const row = gruppi.value.find((g) => g.gruppo_key === key)
  return row?.riferimento || ripiego || key
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

// ═══ IL SEGNO SU UN DOCUMENTO CHE UN GIRO HA GIÀ PROVATO A FATTURARE ═══════
//
// ⭐ IL CASO (brief-db-esito-gruppo-lotto, lotto LTF-0009578). Un lotto prende
//    in carico tre documenti e ne fattura due. Il terzo cade PRIMA di diventare
//    fattura, quindi non compare nel lotto — e qui restava fra quelli da
//    emettere, identico agli altri. Sembrava fatturabile, e chi guardava non
//    aveva modo di sapere che era già stato provato.
//
// ⛔ IL SEGNO NON SPEGNE LA RIGA (decisione di Tid, 2026-09-06): stadio e
//    emittibilità restano quelli di prima, la spunta resta spuntabile e
//    «Fattura questo» resta acceso. Dice «ci ho provato e non ci sono
//    riuscito», non «non si può fatturare» — il rimedio è correggere la
//    commessa e riprovare, non nascondere la riga.
//
// ⚠️ `null` non è «andata bene»: è «nessuno l'ha detto». Si accende SOLO su
//    `ERRORE`, mai sull'assenza — un segno su ogni riga mai tentata sarebbe
//    rumore su tutto il mese.

// Scopo: l'ultimo tentativo su questo documento è fallito?
function haUltimoEsitoErrore(row) {
  return row.ultimo_esito === STATO_ESECUZIONE_LOTTO.ERRORE
}

// Scopo: ⭐ IL GESTO CHE SEGUE IL SEGNO — «apri la commessa da correggere».
//        È il punto che decide se il lavoro è servito: nel caso reale la causa
//        non era un difetto del programma ma un dato mancante sulla commessa
//        34137, e un rosso che non porta lì lascia l'operatore a sapere di
//        avere un problema senza sapere che farci.
// ⚠️ Il bersaglio si compone QUI e non arriva dal backend, ed è la differenza
//        con l'icona del drawer lotto: là il bersaglio è PERSISTITO nel `meta`
//        della segnalazione perché la riga non sa a chi appartiene l'errore;
//        qui la commessa è una colonna della riga stessa — chiedere al backend
//        di rispedirla sarebbe lo stesso dato due volte.
// ⛔ Elenco vuoto senza commessa: `BersaglioAzioni` non disegna niente, e il
//        messaggio resta leggibile. Mai un pulsante che porta in un vicolo
//        cieco (regola §4.3 di `brief-db-bersaglio-errore`).
// ⭐ E il GESTO verso il lotto del tentativo si offre SOLO se quel lotto conta
//    ancora: un bersaglio verso un giro concluso o annullato è un pulsante in
//    un vicolo cieco, che api.md vieta esplicitamente.
// ⚠️ La commessa invece resta sempre: quella c'è comunque, ed è il gesto utile
//    quando il lotto non lo è più.
function bersagliUltimoEsito(row) {
  const bersagli = []
  if (row.ultimo_lotto_id && row.ultimo_lotto_pre_fiscale === true) {
    bersagli.push({ type: BERSAGLIO_TIPI.LOTTO, id: row.ultimo_lotto_id })
  }
  if (row.commessa_id) bersagli.push({ type: BERSAGLIO_TIPI.COMMESSA, id: row.commessa_id })
  return bersagli
}

// Scopo: il titolo del pannello dell'errore, che NOMINA il lotto in cui il
//        tentativo è avvenuto — e DICE SE quel tentativo conta ancora.
// ⭐ Rilievo di Tid sul collaudo del 2026-09-09: la colonna mostrava
//    LTF-0010332 su tre righe «anche se quel lotto è annullato», cioè un
//    tentativo concluso letto come uno ancora in corso.
// ⛔ Il dato NON si toglie — è l'unica traccia che spieghi perché il documento
//    è tornato disponibile. Quello che non reggeva era mostrarlo COME SE
//    CONTASSE ANCORA: ora il DB manda anche lo stato (`20260909-66`) e la
//    frase lo dice.
// ⚠️ `ultimo_lotto_pre_fiscale === false` e non `!...`: `null` significa
//    «nessun tentativo», che è un terzo caso e non «concluso».
function titoloUltimoEsito(row) {
  if (!row.ultimo_lotto_codice) return t('vendite.dashboard_competenza.ultimo_esito_titolo')
  return row.ultimo_lotto_pre_fiscale === false
    ? t('vendite.dashboard_competenza.ultimo_esito_titolo_lotto_concluso', {
        lotto: row.ultimo_lotto_codice,
        stato: row.ultimo_lotto_stato ?? '',
      })
    : t('vendite.dashboard_competenza.ultimo_esito_titolo_lotto', { lotto: row.ultimo_lotto_codice })
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
const listaResiduiRef = ref(null)
const erroriPaginatorOptions = computed(() => ({
  totalRecords: erroriCount.value,
  rows: erroriPageSize.value,
  first: (erroriPage.value - 1) * erroriPageSize.value,
  rowsPerPageOptions: misureOpzioni(),
}))
const gruppiPaginatorOptions = computed(() => ({
  totalRecords: gruppiCount.value,
  rows: gruppiPageSize.value,
  first: (gruppiPage.value - 1) * gruppiPageSize.value,
  rowsPerPageOptions: misureOpzioni(),
}))
const residuiPaginatorOptions = computed(() => ({
  totalRecords: residuiCount.value,
  rows: residuiPageSize.value,
  first: (residuiPage.value - 1) * residuiPageSize.value,
  rowsPerPageOptions: misureOpzioni(),
}))
const commessePaginatorOptions = computed(() => ({
  totalRecords: commesseCount.value,
  rows: commessePageSize.value,
  first: (commessePage.value - 1) * commessePageSize.value,
  rowsPerPageOptions: misureOpzioni(),
}))

// Scopo: display del numero documento della fattura in errore.
// ⛔ Non compone: legge la sede unica (`vendite.fn_numero_documento_fattura`,
// 20260829-15). Prima scriveva `serie numero/anno` — la terza forma delle tre
// che il frontend aveva per lo stesso documento.
// ⚠️ Due «vuoti» diversi e vanno tenuti distinti: nessuna fattura sull'evento
// (`fattura_id` assente) e fattura non ancora numerata. Il secondo caso arriva
// come NULL dal backend, ed e' giusto che si veda come il primo: da qui in poi
// e' l'evento a non avere un documento da nominare.
function fatturaDisplay(row) {
  if (!row.fattura_id) return '—'
  return row.fattura_numero_documento || '—'
}

// Azioni di lista (personalizza colonne + esporta). ⚠️ Questa pagina ha TRE
// liste configurabili e una toolbar sola: le azioni devono agire su quella che
// l'operatore sta davvero guardando, altrimenti personalizzerebbe o
// esporterebbe una lista che non ha davanti.
//
// ⭐ DAL 2026-08-24 LA DOMANDA HA UNA RISPOSTA SOLA: **quale tab e' aperto**.
//    Prima era una precedenza dedotta («il drill-down se c'e', altrimenti gli
//    errori»), ed era il meglio che si potesse fare con due liste impilate:
//    entrambe potevano essere a video insieme, e bisognava indovinare quale
//    l'operatore stesse guardando. Coi tab non c'e' piu' niente da indovinare —
//    e una sola delle due e' montata per davvero (`lazy`).
//
// ⚠️ Resta il difetto che questa computed esiste per evitare, misurato in app
//    il 2026-08-15: le azioni NON vanno legate al solo `stadioSelezionato`,
//    perche' sul tab errori non c'e' nessuno stadio e sparirebbero proprio li'.
const contestoLista = computed(() => {
  if (tabAttiva.value === TAB_ERRORI) {
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
  if (stadioSelezionato.value === STADIO_GRUPPI) {
    return {
      lista: listaGruppiRef.value,
      exportFn: exportDashboardCompetenzaGruppi,
      // ⚠️ TUTTI i filtri a video: un export che non corrisponde a ciò che si
      // ha davanti è peggio di nessun export — chi lo apre crede di avere quel
      // perimetro e non ha modo di accorgersi che non è così.
      // ⛔ E per questo i filtri NON si ricompongono qui: li dà lo store, che è
      //    lo stesso posto da cui li prende la lista. Finché erano due copie
      //    hanno divergito davvero — il filtro sezionale è finito nella lista
      //    e non nell'export, che avrebbe scritto un file con tutte le righe
      //    mentre a video ne restavano 32 (rilievo 2026-08-26).
      params: (formato) => ({
        formato,
        competenza_mese: competenzaCorrente.value,
        ...gruppiFiltriApi(),
      }),
    }
  }
  // ⛔ Il ramo dei RESIDUI viene PRIMA di quello generico, e senza di lui la
  //    card «Emesse non fatturate» cadeva nel ramo delle commesse: a video la
  //    lista dei residui, e «Esporta» che scaricava le COMMESSE. E' il difetto
  //    che il commento del ramo gruppi qui sopra dichiara di voler evitare —
  //    «un export che non corrisponde a cio' che si ha davanti e' peggio di
  //    nessun export» — rientrato dalla porta di servizio aggiungendo una lista
  //    e dimenticando lo smistamento.
  //    ⚠️ Anche «Personalizza colonne» ne dipende: puntava a `listaCommesseRef`,
  //    che su questa card non e' nemmeno montata.
  if (stadioSelezionato.value === STADIO_RESIDUI) {
    return {
      lista: listaResiduiRef.value,
      exportFn: exportDashboardCompetenzaResidui,
      // L'ordinamento a video entra nell'export: il file deve raccontare la
      // stessa coda, nello stesso ordine di urgenza.
      params: (formato) => ({
        formato,
        competenza_mese: competenzaCorrente.value,
        order_by: residuiOrderBy.value,
        order_dir: residuiOrderDir.value,
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
  // Tab area senza nessuno stadio scelto: non c'e' lista, non ci sono azioni.
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
  // ⛔ Nessun default da aprire qui: dopo un'azione una card è per forza già
  //    scelta — l'azione parte da una sua riga. Aggiungerlo sarebbe una fetch
  //    su un ramo irraggiungibile, cioè codice che nessuno può provare.
  if (stadioSelezionato.value) loadDrillDown()
}

// Scopo: verbo APPROVA a grana mese (A-2/D-3): conferma con contatore+valore
//        (WYSIWYG con la card), poi POST approva-competenza sul mese corrente.
function onApprovaMese() {
  const card = cardDaApprovare.value
  if (!card) return
  confirmAction({
    header: t('vendite.dashboard_competenza.approva_mese_header'),
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
// condividono il flusso: accoda (POST) → polling del job (GET
// run/<id>/) → esito + refresh. Estratto in un helper locale (regola del 2):
// cambiano solo API, testi e campi dell'esito. Ogni verbo ha il PROPRIO polling
// (loading del pulsante indipendente); vive sulla card del suo stadio (WYSIWYG),
// gate nel template. I-7: «Fattura» (pre-fiscale, ferma a EMESSA) e «Rendi
// definitive» (numerazione, atto fiscale) sono pulsanti SEPARATI su card diverse.
// Se il worker non e' schedulato il job resta PENDING → onTimeout avvisa "in
// coda" invece di girare all'infinito; colpi a vuoto del polling silenziosi.
// `avvia(opzioni)`: `apiOptions` per gli argomenti extra della chiamata (i
// gruppi, la data documento), `giro` per l'etichetta con cui l'esito verra'
// attribuito. Tutti vuoti = comportamento dei due verbi di perimetro.
// ⚠️ La CONFERMA non e' qui: la chiede il dialog della data documento, che tutti
// e tre i verbi attraversano (vedi `chiediDataECrea`).
//
// ⭐ CONCORRENZA (2026-08-17, brief-fe-fatturazione-job-concorrenti). L'emissione
// mirata ammette piu' giri in volo insieme (`maxConcurrent: Infinity`, decisione
// D1: nessun tetto); i due verbi di perimetro restano a uno per volta col
// default del BB. Il pezzo che rende la cosa sostenibile non e' il polling
// multi-job — quello e' la meccanica — ma il fatto che ogni giro si porti
// dietro il PROPRIO contesto (`gruppi`, `etichetta`, `competenza`) fino
// all'esito: senza, due esiti che arrivano a distanza di secondi sono
// indistinguibili, e un elenco di «non serviti» che non dice di quale giro sia
// non e' interpretabile.
// ⚠️ `keys` porta ora solo i testi degli ESITI (accodato / errore / in coda):
// header e conferma sono usciti insieme al ramo `confirmAction`. Lasciarli
// dentro avrebbe fatto credere che qualcuno li leggesse.
function useVerboFatturazione({ apiFn, keys, buildEsitoOk, maxConcurrent = 1 }) {
  // Scopo: chiude un giro — toglie le marcature dei SOLI suoi gruppi (gli altri
  //        giri stanno ancora lavorando) e riallinea i dati.
  function concludiGiro(context) {
    if (context?.jobId !== undefined && context?.jobId !== null) {
      smarcaGiro(context.jobId)
    }
    // Ricaricare sotto i piedi di un giro ancora vivo e' sicuro: le marcature
    // sono per chiave di dominio (`gruppo_key`), non per indice di riga, quindi
    // sopravvivono al reload. Cio' che cambia e' che le righe consumate
    // spariscono e le pagine scorrono — per questo il conteggio dei giri vivi
    // sta in TESTATA e non solo sulle righe.
    reloadDopoAzione()
  }

  // ⭐ La key del GESTO, una per verbo (`useChiaveGesto`): un «Fattura»
  //    ripremuto dopo un timeout con lo stesso mese, gli stessi gruppi e la
  //    stessa data rimanda la stessa key, e il backend restituisce il giro gia'
  //    accodato invece di accodarne un altro. Il dialog della data resta
  //    aperto fino all'esito, e aprirlo azzera la key (`azzeraGesto`).
  const gesto = useChiaveGesto()

  const { start, isFollowing, nJobsInCorso, resume } = useJobPolling({
    fetchStatus: (jobId) => getFatturazioneRun(jobId),
    maxConcurrent,
    onDone: (stato, context) => {
      if (stato.stato === 'FATTO') {
        buildEsitoOk(stato.result ?? {}, context)
      } else {
        // ERRORE/ANNULLATO: non andato a buon fine (payload, revoca…).
        // ⚠️ Il messaggio da solo non basta piu'. Un giro MIRATO che non
        // produce nessun lotto SOLLEVA (E_FATTURAZIONE_GIRO_NESSUN_LOTTO) e
        // porta i gruppi non serviti col loro motivo dentro
        // `ultimo_errore.context` — che fin qui veniva buttato via. Con un giro
        // per volta era raro; con piu' giri concorrenti e' l'esito TIPICO del
        // secondo giro che tocca gli stessi gruppi (le righe se le e' prese il
        // primo), e dire «errore» al posto di «quel gruppo l'ha fatturato
        // l'altro giro» manderebbe a cercare un guasto che non esiste.
        const nonServiti = normalizzaLista(stato.ultimo_errore?.context?.gruppi_non_serviti)
        if (nonServiti.length > 0) {
          notificaNonServiti(nonServiti, 0, context)
        } else {
          notify.error(stato.ultimo_errore?.message || t(keys.errore))
        }
      }
      concludiGiro(context)
    },
    onTimeout: (context) => {
      notify.warn(t(keys.inCoda))
      // ⚠️ Si sblocca anche qui: il job PROSEGUE in coda ma noi smettiamo di
      // seguirlo, e lasciare le righe marcate «in corso» per sempre sarebbe
      // peggio del silenzio — un'indicazione che non si spegne più non è
      // informazione, è un guasto apparente.
      concludiGiro(context)
    },
  })

  // ⭐ QUI NON SI CHIEDE PIU' CONFERMA, e la conferma non e' sparita: si e'
  //   spostata nel dialog della data documento (FE-1/FE-2), che tutti e tre i
  //   verbi attraversano e che porta con se' il testo del PESO
  //   dell'operazione. Chiederla due volte non sarebbe prudenza: e' l'attrito
  //   che insegna a premere «Sì» senza leggere.
  //   ⚠️ Il ramo `confirmAction` e i `messageParams` sono stati TOLTI, non
  //   lasciati spenti: un percorso morto accanto a uno vivo non si distingue
  //   leggendo, e il prossimo verbo non saprebbe quale dei due imitare.
  async function avvia({ apiOptions = null, giro = null } = {}) {
      // La competenza si congela QUI: il giro puo' concludersi dopo che
      // l'operatore ha cambiato mese, e i suoi lotti appartengono al mese in
      // cui e' partito, non a quello che si sta guardando all'arrivo.
      const competenza = competenzaCorrente.value
      const opzioni = apiOptions ?? {}
      const res = await execute(() => gesto.invia(
        { competenza, ...opzioni },
        (config) => apiFn(competenza, opzioni, config),
      ))
      if (res === null) return false
      // Stessa selezione ancora viva → il BE non crea un secondo job:
      // restituisce l'id di QUELLO in corso (chiave di idempotenza
      // competenza+scope+gruppi). Seguirlo di nuovo lo conterebbe due volte;
      // e all'operatore va detto che non ha avviato niente di nuovo.
      if (isFollowing(res.job_id)) {
        notify.info(t('vendite.dashboard_competenza.fattura_giro_gia_in_corso'))
        return true
      }
      const gruppiGiro = apiOptions?.gruppi ?? []
      const avviato = start(res.job_id, {
        jobId: res.job_id, competenza, giro, gruppi: gruppiGiro,
      })
      if (!avviato) {
        // Job accodato ma non seguito (tetto raggiunto sui verbi di
        // perimetro): il lavoro parte lo stesso, l'esito no — dirlo e' il
        // minimo, tacere lascerebbe credere che non sia successo nulla.
        notify.warn(t(keys.inCoda))
        return true
      }
      notify.success(t(keys.accodato))
      // Marcatura DOPO l'avvio riuscito: se il POST fallisce non devono
      // restare righe segnate per un giro che non è mai partito.
      if (gruppiGiro.length) {
        marcaGiro(res.job_id, gruppiGiro)
        // La selezione si libera ORA, non a fine giro: e' cio' che permette
        // di comporre subito il giro successivo senza aspettare — il punto
        // di tutto questo cantiere. Escono solo i gruppi di QUESTO giro.
        const inviati = new Set(gruppiGiro)
        selezioneGruppi.value = selezioneGruppi.value.filter(
          (r) => !inviati.has(r.gruppo_key),
        )
      }
      return true
  }
  // `avvia` risponde `true` se il giro e' partito (o era gia' in corso): lo
  // legge il dialog della data per chiudersi solo all'esito.
  return { avvia, nGiriInCorso: nJobsInCorso, resume, azzeraGesto: gesto.azzera }
}

// Scopo: lista dal payload BE, sempre un array (il campo puo' mancare del
//        tutto: `gruppi_non_serviti` esiste solo sui giri mirati).
function normalizzaLista(valore) {
  return Array.isArray(valore) ? valore : []
}

// Scopo: etichetta del giro per gli esiti. Con piu' giri in volo un toast che
//        dice «2 gruppi rimasti fuori» senza dire DI QUALE giro non e'
//        interpretabile: l'operatore ne ha due o tre aperti e non sa a quale
//        tornare. L'identita' del giro sono i riferimenti che ha spedito —
//        nessuna tabella di corrispondenza da consultare.
function etichettaGiro(context) {
  return context?.giro || t('vendite.dashboard_competenza.giro_senza_etichetta')
}

// Scopo: il messaggio dei gruppi richiesti ma rimasti FUORI, con il motivo
//        classificato dal BE. Un solo compositore per i due percorsi in cui la
//        stessa notizia arriva: nel `result` di un giro riuscito a meta', e nel
//        `ultimo_errore.context` di un giro che non ha prodotto NULLA (li' il
//        BE solleva). Scriverlo due volte significherebbe che prima o poi i due
//        rami raccontano la stessa cosa in modo diverso.
// Scopo: l'etichetta CORTA di un motivo di mancata fatturazione, concordata col
//        numero. Il vocabolario e' del BE (`_fatturazione_job_helpers`), e qui
//        si risolve l'indirizzo `motivo_<codice>` — stesso patto di
//        `motivoLabel`: se il BE ne aggiunge uno, a video compare il CODICE e
//        non una cella vuota, cosi' il buco si vede invece di sparire.
function etichettaMotivo(codice, n) {
  const chiave = `vendite.dashboard_competenza.motivo_${String(codice || '').toLowerCase()}`
  return te(chiave) ? t(chiave, n) : (codice || '—')
}

// Scopo: il messaggio dei gruppi richiesti ma NON fatturati.
//
// ⭐ RISCRITTO IL 2026-09-05 (rilievo di Tid). Diceva «{lotti} lotti prodotti e
//    {mancanti} gruppi rimasti fuori», e aveva due difetti che si sommavano:
//      1. ⛔ MESCOLAVA DUE UNITA' — lotti in uscita, gruppi in entrata — senza
//         dire il totale. Su tre gruppi «1 lotto prodotto e 1 gruppo fuori»
//         faceva sottrarre e concludere che il terzo fosse sparito: era dentro
//         il lotto insieme a un altro, perche' l'aggregazione mette piu' gruppi
//         nello stesso lotto. Adesso il totale sta davanti e i due lati sono
//         nella STESSA unita': il conto torna sempre.
//      2. ⛔ «rimasto fuori» non diceva SE fosse un guasto. Il BE classifica
//         dieci motivi e cinque non sono errori (gia' fatturato, da approvare,
//         rifiutato, fuori competenza, commessa non emittibile): chiamarli
//         «errore» manda a cercare un guasto che non c'e', chiamarli «fuori»
//         non dice niente. Adesso si nomina il motivo.
// ⚠️ Il motivo sta in TESTA quando e' uno solo — il caso normale — e allora il
//    dettaglio e' il solo nome del gruppo. Con motivi diversi la testa dice
//    «non fatturati» (il superinsieme vero) e ciascuno porta il suo.
// ⚠️ La prosa lunga del BE (`s.dettaglio`) NON entra piu' nel toast: un toast si
//    legge in un colpo d'occhio, e quel testo vive nell'esito del job e nel
//    registro del lotto, dove si va a guardare il perche'.
function notificaNonServiti(nonServiti, nLotti, context) {
  // Gruppi DISTINTI, non righe: la fotografia BE ha grana
  // `(gruppo_key, commessa_id)` e un gruppo su due commesse darebbe due
  // righe — «2 mancanti» per un solo gruppo non servito.
  const chiaviMancanti = new Set(nonServiti.map((s) => s.gruppo_key))
  const mancanti = chiaviMancanti.size
  // Il totale sono i gruppi SPEDITI, congelati all'avvio: la lista a video puo'
  // essersi gia' ricaricata quando l'esito arriva.
  const totale = normalizzaLista(context?.gruppi).length || mancanti
  const motiviDistinti = new Set(nonServiti.map((s) => s.motivo))
  const motivoUnico = motiviDistinti.size === 1 ? [...motiviDistinti][0] : null

  notify.warn(t('vendite.dashboard_competenza.fattura_gruppi_esito_non_serviti', {
    totale,
    fatturati: Math.max(totale - mancanti, 0),
    lotti: t('vendite.dashboard_competenza.n_lotti_prodotti', nLotti, { n: nLotti }),
    mancanti,
    motivo: motivoUnico
      ? etichettaMotivo(motivoUnico, mancanti)
      : t('vendite.dashboard_competenza.motivo_non_servito_misto', mancanti),
    // Il gruppo si nomina come nella lista — col `riferimento`, non col codice
    // commessa: e' lo STESSO gruppo, e chiamarlo in due modi manda a cercare due
    // oggetti. Il codice commessa resta come ripiego per le righe che nel
    // frattempo sono uscite dalla lista.
    // ⚠️ Primi 3 per esteso: un toast non regge un elenco, e i giri di massa ne
    //    hanno centinaia.
    dettagli: elencoTroncato(
      nonServiti,
      // ⭐ Se il gruppo è trattenuto, la voce NOMINA IL LOTTO. «Trattenuto»
      //    senza dire da cosa non è azionabile: chi legge non saprebbe dove
      //    andare a guardare. Il codice arriva strutturato dal BE
      //    (`lotto_codice`), non si ricava da nessuna frase.
      // ⚠️ Il GESTO «vai al lotto» sta sulla RIGA della lista, non qui: un
      //    pulsante dentro un toast che sparisce dopo cinque secondi non è un
      //    gesto, e la riga ce l'ha già (`bersagliLottoTrattiene`) e RESTA.
      //    Qui bastano le parole per sapere dove andare.
      (s) => {
        const base = motivoUnico
          ? etichettaGruppoKey(s.gruppo_key, s.commessa_codice)
          : `${etichettaGruppoKey(s.gruppo_key, s.commessa_codice)}: ${etichettaMotivo(s.motivo, 1)}`
        return s.lotto_codice ? `${base} (${s.lotto_codice})` : base
      },
      '; ',
    ),
  }))
}

// Verbo FATTURA (C-6): card DA_EMETTERE. Corsia differita → ferma a EMESSA,
// cumulativo su competenza ≤ M.
const {
  avvia: onFatturaMese, nGiriInCorso: nGiriMese, resume: resumeMese, azzeraGesto: azzeraGestoMese,
} = useVerboFatturazione({
  apiFn: runFatturazione,
  keys: {
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

// ⛔ IL VERBO «RENDI DEFINITIVE» NON VIVE PIU' QUI (2026-08-26). Agiva sui
// LOTTI e stava accanto a un elenco di COMMESSE: per sapere cosa si stava per
// rendere definitivo bisognava andarsene altrove. E' passato alla lista Lotti,
// dove quell'elenco esiste e dove si puo' anche scegliere QUALI.
// ⚠️ Qui resta il CONTEGGIO (`nDaNumerare`) e il rimando: la card deve
// continuare a dire quante fatture aspettano un numero — e' l'informazione che
// manda l'operatore dove il verbo adesso vive.
// ⚠️ Non e' rimasto niente di spento: il verbo, il suo dialog e il suo polling
// sono stati TOLTI, non lasciati inerti. Un percorso morto accanto a uno vivo
// non si distingue leggendo, e il prossimo verbo non saprebbe quale imitare.

// Verbo FATTURA MIRATA: stesso endpoint e stesso core del verbo di mese
// (I-1), ma con il perimetro ristretto ai gruppi selezionati. Si ferma a
// EMESSA come l'altro; l'esito porta gli N lotti prodotti, che diventano
// l'aggancio «vai al lotto».
// Con piu' giri concorrenti l'esito NON sovrascrive piu': accumula i lotti e
// nomina il giro di provenienza.
const {
  avvia: avviaFatturaGruppi, nGiriInCorso: nGiriMirata, resume: resumeMirata,
  azzeraGesto: azzeraGestoMirata,
} = useVerboFatturazione({
  apiFn: runFatturazione,
  // Nessun tetto (decisione D1, 2026-08-17): il verbo resta premibile con
  // giri vivi. Cio' che tiene leggibile la cosa non e' un divieto — e'
  // l'attribuzione degli esiti qui sotto e il conteggio in testata.
  maxConcurrent: Infinity,
  keys: {
    accodato: 'vendite.dashboard_competenza.fattura_gruppi_accodato',
    errore: 'vendite.dashboard_competenza.fattura_mese_errore',
    inCoda: 'vendite.dashboard_competenza.fattura_mese_in_coda',
  },
  buildEsitoOk: (r, context) => {
    const giro = etichettaGiro(context)
    const lotti = normalizzaLista(r.lotti)
    // Accumulo, non sostituzione: il giro che finisce per secondo non deve
    // cancellare l'aggancio «vai al lotto» di quello finito per primo.
    registraLottiEmessi(lotti, context?.competenza ?? competenzaCorrente.value)
    const falliti = Number(r.falliti ?? 0)
    // Gruppi richiesti ma rimasti FUORI dal giro (BE `gruppi_non_serviti`,
    // rev 2026-08-15): ognuno porta il motivo classificato dalla diagnosi.
    // Era il caso silenzioso — «2 su 3» sembrava un successo pieno e il
    // terzo restava fermo senza che nessuno lo cercasse.
    const nonServiti = normalizzaLista(r.gruppi_non_serviti)
    const altrove = normalizzaLista(r.gruppi_fatturati_altrove)
    // ⚠️ Non e' una catena else-if: falliti e non-serviti possono COESISTERE
    // (una terna fallita E un gruppo fuori perimetro nello stesso giro), e
    // subordinare il secondo al primo ricreerebbe proprio il silenzio che
    // questo esito e' nato per togliere — l'operatore ripara la terna e il
    // gruppo bloccato torna a sparire senza che nessuno lo nomini.
    if (falliti > 0) {
      notify.warn(t('vendite.dashboard_competenza.fattura_gruppi_esito_parziale', {
        giro, lotti: lotti.length, falliti,
      }))
    }
    if (nonServiti.length > 0) {
      notificaNonServiti(nonServiti, lotti.length, context)
    }
    // Terzo esito del consuntivo (BE `gruppi_fatturati_altrove`): il gruppo non
    // e' entrato in QUESTI lotti ma non resta nulla da emettere — le righe sono
    // gia' su fatture di altri lotti. NON e' un problema: e' informazione, e
    // raccontarlo come «non servito» manderebbe a cercare un guasto che non c'e'.
    if (altrove.length > 0) {
      notify.info(t('vendite.dashboard_competenza.fattura_gruppi_esito_altrove', {
        giro,
        n: altrove.length,
        // Il BE manda le CHIAVI (`ORDINE_VENDITA:<uuid>`): a video va il
        // riferimento leggibile della riga, come ovunque in questa lista. Il
        // lookup gira PRIMA di `reloadDopoAzione`, quindi le righe del giro
        // sono ancora quelle a video; fallback sulla chiave, mai una frase
        // monca.
        // ⚠️ Avvolta, non passata nuda: `elencoTroncato` fa `.map(fmt)` e
        // passerebbe l'indice come `ripiego` di `etichettaGruppoKey`.
        gruppi: elencoTroncato(altrove, (k) => etichettaGruppoKey(k), ', '),
      }))
    }
    // ⚠️ `altrove` NON entra nel gate del successo: e' informazione, non un
    // problema (lo dice il BE, lo dice il commento qui sopra). Togliere il
    // «N lotti prodotti» perche' un gruppo era gia' fatturato altrove
    // lascerebbe senza conferma un'emissione riuscita.
    if (falliti === 0 && nonServiti.length === 0) {
      if (lotti.length === 0) {
        // Zero lotti senza errori: nulla era davvero fatturabile (righe gia'
        // prese da un altro giro, o commessa non piu' emittibile). Va detto —
        // un «fatto» muto farebbe pensare a una fattura che non esiste.
        notify.warn(t('vendite.dashboard_competenza.fattura_gruppi_esito_vuoto', { giro }))
      } else {
        notify.success(t('vendite.dashboard_competenza.fattura_gruppi_esito', {
          giro,
          lotti: lotti.length,
        }))
      }
    }
  },
})

// ═══ FE-1 / FE-2 — LA DATA DOCUMENTO, CHIESTA PRIMA DELL'ATTO ═══════════════
//
// Due dialog, due domande diverse, lo stesso componente:
//   · CREAZIONE (verbi «Fattura»): la data e' FACOLTATIVA — vuota vuol dire
//     «la decide la politica del registro», che non e' «oggi». Questo dialog
//     ASSORBE la conferma secca di prima (`skipConfirm`), e con essa il testo
//     che dichiara il peso dell'operazione: senza, l'operatore perderebbe il
//     «3 gruppi, 47 attivita'» per guadagnare un campo data.
//   · NUMERAZIONE («Rendi definitive»): la data e' quella con cui i documenti
//     prenderanno il numero, e il dialog porta il PAVIMENTO del sezionale —
//     senza, sul Back-office (politica FINE_MESE_COMPETENZA) ogni mese
//     arretrato proporrebbe una data che il DB rifiuta.
const dialogDataCreazione = ref({ visible: false, perimetro: '', esegui: null })

// Scopo: apre il dialog della data prima di un verbo di CREAZIONE, portandosi
//        dietro la frase del perimetro e cosa fare alla conferma.
// ⭐ Aprire il dialog e' un GESTO NUOVO: la key si azzera qui, e il dialog
//    resta aperto fino all'esito (un reinvio dopo un timeout avviene dentro,
//    con la stessa key). Vedi la testa di `NumerazioneDataDialog`.
function chiediDataECrea(perimetro, esegui, azzeraGesto) {
  azzeraGesto()
  dialogDataCreazione.value = { visible: true, perimetro, esegui }
}

// `true` = il giro e' partito: il dialog si chiude.
async function confermaDataCreazione(dataDocumento) {
  const azione = dialogDataCreazione.value.esegui
  return (await azione?.(dataDocumento)) === true
}

// Verbo «Fattura mese»: la data prima, poi il giro (la conferma e' il dialog).
function onFatturaMeseClick() {
  chiediDataECrea(
    t('vendite.dashboard_competenza.fattura_mese_conferma', {
      mese: `${nomiMesi.value[meseIdx.value]} ${anno.value}`,
    }),
    (dataDocumento) => onFatturaMese({
      apiOptions: dataDocumento ? { dataDocumento } : null,
    }),
    azzeraGestoMese,
  )
}

// Scopo: avvia l'emissione mirata sui gruppi passati (una riga dal kebab,
//        oppure l'intera selezione). La conferma dichiara quanti gruppi e
//        quante attivita' si stanno per fatturare: e' il peso di cio' che sta
//        per succedere, prima che succeda.
function fatturaGruppi(righe) {
  if (!righe.length) return
  const nAttivita = righe.reduce((acc, r) => acc + Number(r.n_attivita ?? 0), 0)
  // I riferimenti servono due volte e vanno calcolati ORA, mentre le righe
  // sono ancora a video: sono il testo della conferma e, portati nel contesto
  // del giro, l'etichetta con cui l'esito verra' attribuito quando arrivera' —
  // magari dopo che la lista si e' gia' ricaricata e quelle righe non ci sono
  // piu'.
  const riferimenti = elencoTroncato(righe, (r) => r.riferimento)
  const gruppi = righe.map((r) => r.gruppo_key)
  chiediDataECrea(
    t('vendite.dashboard_competenza.fattura_gruppi_conferma', {
      n: righe.length,
      attivita: nAttivita,
      riferimenti,
    }),
    (dataDocumento) => avviaFatturaGruppi({
      apiOptions: dataDocumento ? { gruppi, dataDocumento } : { gruppi },
      giro: riferimenti,
    }),
    azzeraGestoMirata,
  )
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
// L'area del BB e' il codice della sorgente, cioe' `tipo_gruppo`, e vale solo
// se il documento ha una pagina (`documento_apribile`, da `config.sorgenti`):
// dal 2026-10-20 il BE non manda piu' il plurale `area_documento`
// (brief-db-grammatica-unica-documenti, 2d / L2d-1).
// I gruppi SOURCELESS (oneri di commessa) non hanno documento: `documento_id`
// e `documento_apribile` sono NULL e il BB nasconde da se' la voce — lasciando la
// sola commessa, che per loro E' il riferimento (il `riferimento` di quelle
// righe e' infatti il codice commessa).
// Scopo: il motivo del blocco, con la via d'uscita SOLO a chi puo' percorrerla.
//        Chi non ha `cambia_stato_commessa` non vedrebbe «Rendi pronta» nel
//        drawer: indicargliela sarebbe una promessa falsa, e il rimedio giusto
//        per lui e' sapere a chi chiedere.
function tooltipBloccato(row) {
  const stato = row.commessa_stato_descrizione
    ?? row.commessa_stato_codice_interno ?? '?'
  return canCambiareStatoCommessa.value
    ? t('vendite.dashboard_competenza.gruppo_bloccato_tooltip', { stato })
    : t('vendite.dashboard_competenza.gruppo_bloccato_tooltip_senza_permesso', { stato })
}

// ⚠️ MUTUA ESCLUSIONE COL VERBO DI MESE (2026-08-17). Il giro di mese non passa
// gruppi, quindi la sua chiave di idempotenza (competenza+scope+digest) non
// collide con quella di nessun giro mirato: il BE lo lascerebbe partire mentre i
// mirati sono vivi, e il suo perimetro li INGLOBA. Non nascono fatture doppie
// (il DB prende le attivita' con SKIP LOCKED e ricontrolla), ma i due si
// contendono le righe e chi perde torna come «non servito» per una ragione che
// non e' un guasto: manderebbe a cercare un problema inesistente. Sono quindi
// alternativi, e chi e' spento lo dice.
const giroMeseInCorso = computed(() => nGiriMese.value > 0)
const giriMirataInCorso = computed(() => nGiriMirata.value > 0)

// Scopo: motivo del pulsante «Fattura selezionati», soprattutto quando è
//        SPENTO. Le cause sono distinte e dirle è il punto: «nessuna selezione»
//        richiede un'azione dell'operatore, «giro di mese in corso» passa da sé.
//        Senza, il pulsante grigio si legge uguale nei due casi.
// ⚠️ Non c'è più il caso «un'altra fatturazione mirata è in corso»: da oggi non
//    è un motivo di blocco — i giri mirati convivono (decisione D1, nessun
//    tetto) e il pulsante resta premibile.
const tooltipFatturaSelezionati = computed(() => {
  if (giroMeseInCorso.value) {
    return t('vendite.dashboard_competenza.fattura_selezionati_attesa_mese_tooltip')
  }
  if (!selezioneGruppi.value.length) {
    return t('vendite.dashboard_competenza.fattura_selezionati_vuoto_tooltip')
  }
  return t('vendite.dashboard_competenza.fattura_selezionati_tooltip', {
    n: selezioneGruppi.value.length,
  })
})

// Scopo: motivo del verbo di MESE quando è spento perché ci sono emissioni
//        mirate in volo (l'altra faccia della mutua esclusione).
const tooltipFatturaMese = computed(() => (
  giriMirataInCorso.value
    ? t('vendite.dashboard_competenza.fattura_mese_attesa_mirata_tooltip', {
      n: nGiriMirata.value,
    })
    : t('vendite.dashboard_competenza.fattura_mese_tooltip')
))

function buildGruppoRowActions(row) {
  // Testata bloccata: «Fattura questo» nasce DISABILITATO col motivo (brief
  // emittibilita' §3.1 — partiva e non faceva nulla), e compare «Sblocca
  // commessa»: apre il drawer di governo, dove il verbo «Rendi pronta» e' gia'
  // esposto data-driven dalle capability (fn_available_actions_commessa,
  // enabled+reasons dalla stessa funzione pura del guard).
  const bloccato = !isGruppoEmittibile(row)
  // ⚠️ Il SECONDO motivo, e va tenuto separato dal primo: si esce dai due
  //    blocchi in due modi diversi — la testata si sblocca cambiando stato alla
  //    commessa, il documento trattenuto togliendolo dal giro del suo lotto.
  //    Fonderli in un `bloccato` solo farebbe comparire «Sblocca commessa» su
  //    una riga dove non c'è niente da sbloccare.
  const trattenuto = !!row.emissione_blocco_reason
  // Riga già in lavorazione: il motivo lo dice la riga stessa (chip «in
  // corso»), ma l'azione resta disabilitata col suo tooltip — chi apre il
  // kebab senza aver visto il chip deve leggere perché non può premere.
  const inCorso = gruppiInCorso.value.has(row.gruppo_key)
  // ⚠️ Fino al 2026-08-17 c'era anche un terzo motivo di blocco — «un'altra
  // fatturazione è in corso» — che spegneva OGNI riga per tutta la durata di un
  // qualsiasi giro. Non serviva contro il doppio invio (quello lo copre
  // `azioneLoading` durante la POST): serviva a non perdere l'esito del giro in
  // corso, perché il polling ne seguiva uno solo. Ora ne segue N, quindi il
  // blocco è caduto: resta solo ciò che riguarda QUESTA riga, più il verbo di
  // mese che è alternativo per costruzione.
  const attesaMese = !inCorso && giroMeseInCorso.value
  return [
    {
      key: 'fattura_gruppo',
      label: t('vendite.dashboard_competenza.azione_fattura_gruppo'),
      icon: MANAGE_ICONS.FATTURA_GENERA,
      visible: canFatturare.value,
      // Precedenza dei motivi: prima ciò che riguarda QUESTA riga (in corso,
      // testata bloccata), poi la causa di contesto (il giro di mese).
      tooltip: inCorso
        ? t('vendite.dashboard_competenza.gruppo_in_corso_tooltip')
        : bloccato
          ? tooltipBloccato(row)
          : trattenuto
            ? motivoTrattenuto(row)
            : attesaMese
              ? t('vendite.dashboard_competenza.fattura_selezionati_attesa_mese_tooltip')
              : '',
      // 🔴 `trattenuto` mancava, e il kebab offriva «Fattura questo» su una riga
      //    che un lotto vivo sta gia' tenendo — cioe' proprio il doppio giro che
      //    questo cantiere esiste per impedire. La casella era spenta e il kebab
      //    no: due superfici dello stesso verbo che dicevano cose diverse.
      disabled: azioneLoading.value || inCorso || bloccato || trattenuto
        || giroMeseInCorso.value,
      command: () => fatturaGruppi([row]),
    },
    {
      key: 'sblocca_commessa',
      label: t('vendite.dashboard_competenza.azione_sblocca_commessa'),
      icon: MANAGE_ICONS.SBLOCCA,
      // ⚠️ Gate sul permesso del verbo di DESTINAZIONE, non su quello di
      // fatturazione: chi non puo' cambiare stato non troverebbe «Rendi
      // pronta» nel drawer. Meglio nessuna scorciatoia che una che non porta
      // da nessuna parte.
      visible: bloccato && !!row.commessa_id
        && canFatturare.value && canCambiareStatoCommessa.value,
      command: () => apriCommessa(row),
    },
    buildApriDocumentoAction({
      area: row.documento_apribile ? row.tipo_gruppo : null,
      documentoId: row.documento_id,
      // `riferimento` senza ripiego: e' NOT NULL per contratto (vedi
      // `DashCompetenzaGruppoRow`), e questa voce si rende solo quando
      // `documento_id` c'e' — cioe' proprio sui gruppi dove il riferimento E'
      // il numero del documento. Un `?? ''` qui difenderebbe da un caso che il
      // contratto esclude, ed e' la forma tolta da questo file il 2026-09-01.
      label: t('vendite.dashboard_competenza.azione_apri_documento', {
        codice: row.riferimento,
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
    header: t('vendite.dashboard_competenza.approva_commessa_header'),
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

// Filtro stato emissione con cui aprire il drawer: lo STESSO stato della card
// da cui si arriva, cosi' il numero della card e le righe della lista
// raccontano la stessa cosa. Senza, «Fatturate» mostrava 1.089,00 e la
// commessa apriva 4 righe di cui 3 estranee a quel valore, senza che nulla
// spiegasse la differenza (rilievo di Tid, 2026-08-16).
// ⚠️ Solo i due stadi che vivono sull'asse EMISSIONE: `DA_APPROVARE` sta
// sull'asse approvazione e non ha una corrispondenza — li' non si filtra e la
// lista si apre completa, come prima. Il filtro resta comunque visibile e
// azzerabile nel drawer: e' un default, non un vincolo.
const FILTRO_EMISSIONE_PER_STADIO = Object.freeze({
  FATTURATA: STATO_EMISSIONE_ATTIVITA.EMESSA,
  [STADIO_GRUPPI]: STATO_EMISSIONE_ATTIVITA.NON_EMESSA,
})
const commessaDrawerStatoEmissione = computed(
  () => FILTRO_EMISSIONE_PER_STADIO[stadioSelezionato.value] ?? null,
)

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

// Scopo: porta alla lista Lotti sul MESE che si sta guardando — è dove vive
//        «Rendi definitive» da quando ha lasciato questa schermata.
// ⚠️ Il rimando porta la competenza e non «solo gli emessi»: il filtro di
//    quella lista è sullo stato del LAVORO, non del documento. Quali righe si
//    possano numerare lo dice la casella di selezione, riga per riga.
function vaiAiLottiDaNumerare() {
  router.push({
    name: 'vendite-lotti',
    query: { competenza: competenzaCorrente.value },
  })
}

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
      icon: MANAGE_ICONS.APPROVE,
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
  // ⚠️ O l'una o l'altra, mai tutte e due: `apriStadioDefault` carica già il
  //    drill-down, e chiamarle entrambe farebbe due fetch identiche a ogni
  //    rientro in foreground.
  if (stadioSelezionato.value) loadDrillDown()
  else apriStadioDefault()
  // ⚠️ Riprende il follow-up dei giri vivi. Il BB SOSPENDE i tick quando il tab
  // va in background (mai timer che girano su una pagina che nessuno guarda),
  // ma fino al 2026-08-17 li DIMENTICAVA: uscivi dal tab, il job finiva lato
  // server e il suo esito — lotti prodotti, gruppi non serviti col motivo — non
  // arrivava mai. La fatturazione era avvenuta e da qui non si vedeva.
  // Idempotente: senza giri vivi non fa nulla (memoria feedback_keepalive_onactivated).
  resumeMese()
  resumeMirata()
})
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-toolbar-start">
        <h2 style="margin: 0;">
          {{ t('vendite.dashboard_competenza.page_title', { mese: meseTitolo, anno }) }}
        </h2>
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
            {{ statiMesi[idx].errori }} <i :class="STATUS_ICONS.ERRORE" />
          </span>
          <span
            v-if="statiMesi[idx].aperti > 0"
            class="app-dash-mese-fermi"
            v-tooltip.right="t('vendite.dashboard_competenza.mese_aperti', { n: statiMesi[idx].aperti })"
          >
            {{ statiMesi[idx].aperti }} <i :class="STATUS_ICONS.ATTESA" />
          </span>
          <i
            v-if="statiMesi[idx].stato === 'ok'"
            class="app-dash-mese-ok" :class="STATUS_ICONS.TUTTO_OK"
            v-tooltip.right="t('vendite.dashboard_competenza.mese_ok')"
          />
          <i
            v-else-if="statiMesi[idx].stato === 'vuoto'"
            class="app-dash-mese-vuoto" :class="STATUS_ICONS.NON_APPLICABILE"
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
              {{ statoMeseCorrente.errori }} <i :class="STATUS_ICONS.ERRORE" />
            </span>
            <span v-if="statoMeseCorrente.aperti > 0" class="app-dash-mese-fermi">
              {{ statoMeseCorrente.aperti }} <i :class="STATUS_ICONS.ATTESA" />
            </span>
            <i v-if="statoMeseCorrente.stato === 'ok'" class="app-dash-mese-ok" :class="STATUS_ICONS.TUTTO_OK" />
            <i v-else-if="statoMeseCorrente.stato === 'vuoto'" class="app-dash-mese-vuoto" :class="STATUS_ICONS.NON_APPLICABILE" />
          </template>
        </DashMeseStepper>

        <div class="app-dash-cards">
          <!-- Copertura del mese: totali BE (fatturato = imponibile, DB-6).
               ⛔ NON SELEZIONABILE, e non è una dimenticanza: è un TOTALE, non
               uno stadio del funnel, e sotto non ha nessuna lista da aprire.
               La classe spegne mano del puntatore e bordo al passaggio — con
               quelle accese la card prometteva un drill-down che non arriva. -->
          <div class="app-dash-card app-dash-card--statica">
            <span class="app-dash-card-title">
              {{ t('vendite.dashboard_competenza.copertura_titolo') }}
            </span>
            <!-- ⚠️ NON «Emesso / Da emettere»: erano le STESSE PAROLE della
                 scheda di stadio `stadio_da_emettere`, che sulla stessa
                 schermata mostra lo stesso importo COL SEGNO (−29,50 ad
                 agosto). Due numeri identici e opposti sotto la stessa
                 etichetta erano la domanda senza risposta trovata in
                 collaudo. «Coperto / Scoperto» parla della COPERTURA — che e'
                 il titolo della card — e non di uno stadio del funnel. -->
            <DonutTransito
              :transitato="totaliMese.coperturaFatturato"
              :fermo="totaliMese.coperturaDaFatturare"
              format="currency"
              :label-transitato="t('vendite.dashboard_competenza.coperto')"
              :label-fermo="t('vendite.dashboard_competenza.scoperto')"
            />
            <!-- Le due voci del residuo, STESSA FORMA per entrambe: cambia la
                 parola e il colore, non la struttura. «Da accreditare» compare
                 solo quando c'e', ma quando c'e' e' una riga come l'altra —
                 non una nota a pie' di grafico. -->
            <dl class="app-dash-card-voci">
              <div>
                <dt>{{ t('vendite.dashboard_competenza.da_addebitare') }}</dt>
                <dd>{{ formatCurrency(totaliMese.daAddebitare) }}</dd>
              </div>
              <div v-if="totaliMese.daAccreditare > 0" class="is-accredito">
                <dt>{{ t('vendite.dashboard_competenza.da_accreditare') }}</dt>
                <!-- ⚠️ Col SEGNO, e non e' un ripensamento sul §5.4. Qui il
                     numero sta accanto a «Da addebitare», che e' di verso
                     opposto, e soprattutto sulla stessa schermata la scheda di
                     stadio DA_EMETTERE espone lo stesso importo come −29,50
                     (`valore_display`, il netto). Due numeri uguali con segno
                     diverso, a un palmo l'uno dall'altro, sono una domanda
                     senza risposta: qui il verso VA mostrato.
                     ⭐ Il valore assoluto resta dov'e' indispensabile — nel
                     RAPPORTO del donut, dove i due versi non devono
                     compensarsi. Geometria in assoluto, denaro col segno. -->
                <dd>{{ formatCurrency(-totaliMese.daAccreditare) }}</dd>
              </div>
            </dl>
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
                class="app-dash-card-hint" :class="STATUS_ICONS.INFO"
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
              <i :class="STATUS_ICONS.ERRORE" />
              {{ t('vendite.dashboard_competenza.n_fatture_errore') }}
            </span>
            <span class="app-dash-stat-euro">{{ formatCurrency(card.valoreDisplay) }}</span>
            <!-- Verbo APPROVA a grana mese (Fase A cockpit): solo sul card
                 DA_APPROVARE, gate permesso+readonly; @click.stop per non
                 attivare il drill-down della card. -->
            <Button
              v-if="card.stadio === 'DA_APPROVARE' && card.nAttivita > 0 && canApprova"
              :label="t('vendite.dashboard_competenza.approva_mese')"
              :icon="MANAGE_ICONS.APPROVE"
              size="small"
              :disabled="azioneLoading"
              style="margin-top: 0.5rem;"
              @click.stop="onApprovaMese"
            />
            <!-- Verbo FATTURA a grana mese (C-6): solo sul card DA_EMETTERE,
                 gate permesso+readonly; @click.stop per non attivare il
                 drill-down. Loading = giro in corso (polling non bloccante).
                 ⚠️ Spento anche mentre ci sono emissioni MIRATE in volo: i due
                 verbi sono alternativi (il mese ingloba i loro gruppi). Il
                 tooltip sta sul WRAPPER perché un bottone disabilitato non
                 riceve eventi del mouse — ed è spento che il motivo serve. -->
            <span
              v-if="card.stadio === 'DA_EMETTERE' && card.nAttivita > 0 && canFatturare"
              v-tooltip.bottom="tooltipFatturaMese"
              class="app-dash-fattura-wrap"
              style="margin-top: 0.5rem;"
            >
              <Button
                :label="t('vendite.dashboard_competenza.fattura_mese')"
                :icon="MANAGE_ICONS.FATTURA_GENERA"
                size="small"
                :loading="giroMeseInCorso"
                :disabled="azioneLoading || giroMeseInCorso || giriMirataInCorso"
                @click.stop="onFatturaMeseClick"
              />
            </span>
            <!-- ⭐ IL VERBO SE N'È ANDATO, e al suo posto c'è la strada per
                 raggiungerlo (2026-08-26). «Rendi definitive» agisce sui LOTTI
                 e viveva qui, accanto a un elenco di COMMESSE: per sapere cosa
                 si stava per rendere definitivo bisognava andarsene altrove.
                 Ora vive nella lista Lotti, dove quell'elenco esiste — e lì
                 si può anche scegliere QUALI.
                 ⛔ Il rimando porta con sé il FILTRO (mese + stato emessa): un
                 collegamento all'elenco nudo sarebbe un passo indietro, non
                 avanti. -->
            <Button
              v-if="card.stadio === 'FATTURATA' && nDaNumerare > 0 && canNumerare"
              :label="t('vendite.dashboard_competenza.vai_ai_lotti', { n: nDaNumerare })"
              :icon="MANAGE_ICONS.LOTTO"
              size="small"
              severity="warn"
              outlined
              v-tooltip.bottom="t('vendite.dashboard_competenza.vai_ai_lotti_tooltip')"
              style="margin-top: 0.5rem;"
              @click.stop="vaiAiLottiDaNumerare"
            />
            <!-- Difetto D3 (§6-bis): «Emesse non fatturate» NON e' un passaggio
                 del percorso — pull e generazione righe fattura avvengono nello
                 stesso step DRAFT, quindi le attivita' passano da «Da emettere»
                 direttamente a «Fatturate». Quello che si raccoglie qui sono
                 RESIDUI (AF sospese, posticipate, o rimaste indietro per un
                 giro interrotto). Dirlo evita che l'operatore aspetti un
                 avanzamento che non arrivera' da solo. -->
            <!-- ⭐ LA CARD DICE DUE COSE, e sono due perche' hanno rimedi
                 OPPOSTI. Dentro «Emesse non fatturate» ci sono tre
                 situazioni: il RESIDUO chiede un'azione, le altre due — giro
                 in corso, senza attivita' fatturabile — chiedono di
                 aspettare. Un numero solo per due rimedi opposti
                 era il difetto: la guida diceva «se c'e' un numero, qualcosa si
                 e' rotto», e non era vero per la parte in transito.
                 ⛔ Il conteggio arriva dal BE (`n_residui`), non si deduce
                 dalla lista: la lista e' paginata, e sommare la pagina darebbe
                 un parziale che sembra un totale. -->
            <span
              v-if="card.stadio === STADIO_RESIDUI && card.nAttivita > 0"
              class="app-dash-residui-hint"
              v-tooltip.bottom="t('vendite.dashboard_competenza.residui_tooltip')"
            >
              <i :class="STATUS_ICONS.INFO" />
              <template v-if="card.nResidui > 0">
                {{ t('vendite.dashboard_competenza.residui_di_cui', { n: card.nResidui }) }}
                · {{ formatCurrency(card.valoreResidui) }}
              </template>
              <template v-else>
                {{ t('vendite.dashboard_competenza.residui_nessuno_da_recuperare') }}
              </template>
            </span>
            <!-- ⭐ LA CARD «DA EMETTERE» DICE ANCHE CIÒ CHE NON PUÒ OFFRIRE.
                 Il numero è una PROMESSA su quanto lavoro si può prendere: fino
                 al 2026-09-09 comprendeva anche i documenti che un lotto ancora
                 in gioco stava trattenendo, e l'elenco sotto ne mostrava meno —
                 due cifre diverse sulla stessa schermata (collaudo di Tid).
                 ⛔ Adesso il numero li esclude, e QUESTA riga dice di quanti:
                 un numero che cala senza spiegare il calo è un numero che non
                 si sa leggere. Il conteggio arriva dal BE, non si deduce dalla
                 lista — che è paginata. -->
            <span
              v-if="card.nTrattenute > 0"
              class="app-dash-residui-hint"
              v-tooltip.bottom="t('vendite.dashboard_competenza.trattenuti_tooltip')"
            >
              <i :class="MANAGE_ICONS.LOTTO" />
              {{ t('vendite.dashboard_competenza.trattenuti_di_cui', { n: card.nTrattenute }) }}
              · {{ formatCurrency(card.valoreTrattenuto) }}
            </span>
            <span v-if="card.nInRitardo > 0" class="app-dash-ritardo">
              <i :class="STATUS_ICONS.IN_RITARDO" />
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

        <!-- Le due liste della pagina, in tab (blocco 4 + drill-down).
             ⭐ L'AREA e' il primo tab e la selezione di uno stadio ce la porta
             davanti: prima gli errori restavano SOPRA e spingevano in basso
             l'area appena scelta. Gli errori non spariscono — stanno a un
             click, col conteggio sempre in etichetta.
             ⚠️ `lazy`: monta solo il pannello attivo, ed e' cio' che rende
             `contestoLista` esatto invece che dedotto. -->
        <Tabs v-model:value="tabAttiva" lazy class="app-dash-tabs">
          <TabList>
            <Tab :value="TAB_AREA">
              <i :class="MANAGE_ICONS.LIST" />
              {{ stadioSelezionato
                  ? t('vendite.dashboard_competenza.tab_area', { stadio: stadioSelezionatoLabel })
                  : t('vendite.dashboard_competenza.tab_area_vuota') }}
            </Tab>
            <Tab :value="TAB_ERRORI">
              <i
                :class="[STATUS_ICONS.ERRORE, { 'app-dash-mese-errori': nErroriMese > 0 }]"
              />
              {{ t('vendite.dashboard_competenza.tab_errori', { n: nErroriMese }) }}
            </Tab>
          </TabList>
          <TabPanels>
            <TabPanel :value="TAB_ERRORI">
            <div v-if="nErroriMese > 0" class="app-dash-fermi">
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
            <div v-else class="app-empty-state">
              <i :class="STATUS_ICONS.TUTTO_OK" />
              <p>{{ t('vendite.dashboard_competenza.errori_nessuno') }}</p>
            </div>
            </TabPanel>

        <!-- Drill-down per COMMESSA in pagina (click su card stadio, DEC-4):
             una riga per commessa; il dettaglio a grana attivita' e' nel
             drawer di gestione (kebab «Apri commessa»). -->
            <TabPanel :value="TAB_AREA">
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
                      @change="applicaFiltroGruppi"
                    />
                    <!-- Filtro CLIENTE: scelta strutturata, mai testo libero. Il
                         valore è l'id del BA di FATTURAZIONE — lo stesso elemento
                         che il DB mette nella chiave della fattura — e l'etichetta
                         porta il codice BA accanto al nome perché lo stesso
                         soggetto può avere più alberi omonimi che finiscono su
                         fatture diverse. `filter` perché su un mese pieno la
                         tendina è lunga. -->
                    <Select
                      v-model="gruppiCliente"
                      :options="opzioniCliente"
                      option-label="label"
                      option-value="value"
                      filter
                      :filter-placeholder="t('vendite.dashboard_competenza.filtro_cliente_cerca')"
                      class="app-form-select app-dash-filtro-cliente"
                      :placeholder="t('vendite.dashboard_competenza.filtro_cliente')"
                      v-tooltip.bottom="t('vendite.dashboard_competenza.filtro_cliente_tooltip')"
                      @change="applicaFiltroGruppi"
                    />
                    <!-- Filtro SEZIONALE: quale registro fiscale prenderà il
                         documento. ⚠️ Il valore è l'ID del registro, non il
                         codice, ed è voluto: un gruppo che tocca più sezionali
                         il codice non ce l'ha (a video legge «Più sezionali»),
                         e deve comunque comparire scegliendo uno qualunque dei
                         suoi. Il filtro lavora sull'insieme, non sull'etichetta.
                         Niente `filter`: i sezionali sono pochi per costruzione
                         — crescono con gli emittenti, non coi clienti. -->
                    <Select
                      v-model="gruppiRegistro"
                      :options="opzioniRegistro"
                      option-label="label"
                      option-value="value"
                      class="app-form-select"
                      :placeholder="t('vendite.dashboard_competenza.filtro_registro')"
                      v-tooltip.bottom="t('vendite.dashboard_competenza.filtro_registro_tooltip')"
                      @change="applicaFiltroGruppi"
                    />
                    <!-- Ricerca libera: risponde a «dov'è finito ORD0005174», che è
                         una domanda diversa da «dammi tutto di Rossi» — per quella
                         c'è il filtro qui accanto. Sotto i 3 caratteri il backend la
                         ignora: la lista resta quella di prima invece di svuotarsi
                         dicendo «non c'è niente» mentre si sta ancora digitando. -->
                    <InputText
                      v-model="gruppiSearch"
                      class="app-dash-ricerca-gruppi"
                      :placeholder="t('vendite.dashboard_competenza.ricerca_gruppi')"
                      v-tooltip.bottom="t('vendite.dashboard_competenza.ricerca_gruppi_tooltip')"
                      @input="onGruppiSearchInput"
                    />
                    <!-- ⚠️ Il tooltip sta sul WRAPPER e non sul Button: un bottone
                         disabilitato non riceve eventi del mouse, quindi il
                         tooltip appeso a lui non comparirebbe mai — ed è proprio
                         quando è spento che il motivo serve. -->
                    <span
                      v-if="canFatturare"
                      v-tooltip.bottom="tooltipFatturaSelezionati"
                      class="app-dash-fattura-wrap"
                    >
                    <!-- ⚠️ `loading` sul solo `azioneLoading` (la POST), NON sui
                         giri in corso: da oggi il verbo resta PREMIBILE con giri
                         vivi (decisione D1, nessun tetto), e un pulsante «in
                         caricamento» che però si può premere è una contraddizione
                         a video. -->
                    <Button
                      :label="t('vendite.dashboard_competenza.fattura_selezionati', { n: selezioneGruppi.length })"
                      :icon="MANAGE_ICONS.FATTURA_GENERA"
                      size="small"
                      :loading="azioneLoading"
                      :disabled="selezioneGruppi.length === 0 || azioneLoading || giroMeseInCorso"
                      @click="fatturaGruppi(selezioneGruppi)"
                    />
                    </span>
                    <!-- Quante fatturazioni sono in volo. Senza tetto è l'UNICA cosa
                         che lo dice: le marcature stanno sulle righe, e quelle
                         scorrono di pagina a ogni ricarica post-esito. Sta in
                         testata proprio perché non dipende da cosa si ha davanti. -->
                    <span v-if="giriMirataInCorso" class="app-dash-giri-in-corso">
                      <i :class="STATUS_ICONS.CARICAMENTO" />
                      {{ t('vendite.dashboard_competenza.giri_in_corso', nGiriMirata, { n: nGiriMirata }) }}
                    </span>
                  </div>
                </div>

                <!-- Aggancio al lotto (§5.2): dopo l'emissione l'operatore deve
                     poterci arrivare per numerare. Sono N e non uno: un gruppo con
                     righe di tipo doc fiscale diverso finisce in lotti diversi. -->
                <div v-if="lottiEmessiVisibili.length" class="app-dash-lotti-emessi">
                  <span>{{ t('vendite.dashboard_competenza.lotti_emessi', { n: lottiEmessiVisibili.length }) }}</span>
                  <Button
                    v-for="lotto in lottiEmessiVisibili"
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
                  <!-- ⭐ E quanti ne sono stati TOLTI dai tre totali qui sopra:
                       i gruppi che un giro ancora in corso sta trattenendo.
                       ⛔ Restano VISIBILI nella lista (decisione D-1: una riga
                       che sparisce non insegna niente) ma non si possono
                       prendere, quindi non si contano — e la differenza fra
                       ciò che si vede e ciò che si conta va detta, o le due
                       cifre sembrano contraddirsi. -->
                  <span v-if="gruppiRiepilogo.n_gruppi_trattenuti > 0">
                    {{ t('vendite.dashboard_competenza.tot_gruppi_trattenuti') }}
                    <strong>{{ gruppiRiepilogo.n_gruppi_trattenuti }}</strong>
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
                    <!-- Non spuntabile se la riga non e' selezionabile PER IL BB:
                         testata bloccata, trattenuta da un lotto, o gia' dentro
                         un giro vivo (la rotella accanto al nome). Il guard del
                         BB la tiene comunque fuori dalla selezione; la casella
                         spenta e' cio' che lo DICE. -->
                    <Checkbox
                      binary
                      :model-value="isGruppoSelezionato(data)"
                      :disabled="!isGruppoSelezionabile(data)"
                      @update:model-value="toggleGruppo(data)"
                    />
                  </template>

                  <!-- `riferimento` si rende NUDO: e' gia' il
                       `COALESCE(numero documento, codice commessa, gruppo_key)`
                       della vista, e ripetere quella catena qui sarebbe la stessa
                       regola scritta due volte (i due termini di coda sarebbero
                       irraggiungibili per costruzione). -->
                  <template #cell-riferimento="{ data }">
                    <strong>{{ data.riferimento }}</strong>
                    <!-- Segnalare, non nascondere (brief emittibilita' §3.1): la
                         testata non ammette fatturazione — spia di blocco col motivo,
                         accanto al nome che l'operatore sta gia' leggendo. -->
                    <i
                      v-if="!isGruppoEmittibile(data)"
                      class="app-dash-gruppo-bloccato" :class="STATUS_ICONS.BLOCCATO"
                      v-tooltip.bottom="tooltipBloccato(data)"
                    />
                    <!-- ⭐ TRATTENUTO DA UN LOTTO VIVO: si spegne col MOTIVO e
                         si offre il GESTO, mai si nasconde la riga (D-1) —
                         sparire non spiega niente.
                         ⛔ Il segno del LOTTO e non un secondo lucchetto: le
                         due vie d'uscita sono diverse — là si cambia stato alla
                         commessa, qui si toglie il documento dal giro del suo
                         lotto — e su una riga che ha ENTRAMBI i blocchi due
                         lucchetti identici affiancati non distinguono niente.
                         L'icona dice CHI trattiene.
                         ⚠️ Il `v-if` guarda il DATO e non la traduzione: la
                         frase serve al tooltip, non a decidere. -->
                    <i
                      v-if="data.emissione_blocco_reason"
                      :class="[MANAGE_ICONS.LOTTO, 'app-dash-gruppo-bloccato']"
                      v-tooltip.bottom="motivoTrattenuto(data)"
                    />
                    <!-- Fatturazione in corso su QUESTA riga: il verbo è asincrono
                         (accoda + polling) e senza un segno qui la riga restava
                         identica per tutta la durata, spunta compresa. Sta accanto
                         al nome, dove l'occhio è già posato. -->
                    <i
                      v-if="gruppiInCorso.has(data.gruppo_key)"
                      class="app-spinner-in-corso" :class="STATUS_ICONS.CARICAMENTO"
                      v-tooltip.bottom="t('vendite.dashboard_competenza.gruppo_in_corso_tooltip')"
                    />
                    <!-- ⭐ L'ULTIMO TENTATIVO È FALLITO. Accanto al nome, dove
                         l'occhio è già posato: stesso posto del lucchetto, e
                         per la stessa ragione — segnalare, non nascondere.
                         ⛔ NON è una colonna di catalogo, ed è una scelta: le
                         cinque colonne dell'esito esistono (disponibili e
                         spente, per chi le vuole in lista o nell'export), ma il
                         segno deve esserci SEMPRE. Una colonna che nessuno ha
                         acceso è un segno che non c'è.
                         ⚠️ Il messaggio in un popover e non in una cella: il
                         testo cita numeri di documento e via d'uscita, e in una
                         colonna sarebbe troncato — cioè presente e inutile. -->
                    <ErroreRigaInfo
                      v-if="haUltimoEsitoErrore(data)"
                      :messaggio="data.ultimo_errore_messaggio"
                      :codice="data.ultimo_errore_codice"
                      :quando="data.ultimo_errore_quando"
                      :bersagli="bersagliUltimoEsito(data)"
                      :titolo="titoloUltimoEsito(data)"
                    />
                    <!-- ⭐ IL GESTO IN CODA, e i SEGNI tutti insieme prima: le
                         icone si leggono in fila accanto al nome, il pulsante —
                         l'unica cosa larga della cella — non si infila in mezzo
                         a separarle (rilievo di Tid, 2026-09-09).
                         ⚠️ E in un `<span>` inline: `BersaglioAzioni` ha una
                         radice `<div>` flex, cioè di BLOCCO, e in una cella di
                         contenuto inline mandava a capo tutto ciò che veniva
                         dopo — l'icona d'errore finiva su una seconda riga e la
                         riga cresceva in altezza. -->
                    <span v-if="data.emissione_blocco_reason" class="app-cella-gesto-inline">
                      <BersaglioAzioni :bersagli="bersagliLottoTrattiene(data)" />
                    </span>
                  </template>
                  <!-- Le cinque colonne dell'esito nascono SPENTE a catalogo
                       (D-4: si aggiungono al preset con `visibile = FALSE`, e
                       chi ne ha bisogno le accende). Solo l'esito ha uno slot:
                       è un vocabolario chiuso e vuole il suo colore. Codice,
                       motivo, data e lotto si rendono nudi — il seed dichiara
                       già `datetime_short` per la data.
                       ⚠️ Vuoto = MAI TENTATO, e si scrive «—» come ogni altra
                       assenza: dire «in attesa» su un documento che nessun giro
                       ha guardato sarebbe una promessa che nessuno ha fatto. -->
                  <template #cell-ultimo_esito="{ data }">
                    <Tag
                      v-if="data.ultimo_esito"
                      :value="data.ultimo_esito"
                      :severity="statoEsecuzioneLottoSeverity(data.ultimo_esito)"
                    />
                    <span v-else>—</span>
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

                  <!-- IL SEZIONALE PREVISTO (FE-1). Lo slot si nomina sul
                       `codice` della colonna a catalogo — `registro` — non sul
                       `campo_sorgente` (`registro_codice`), che serve al dato.
                       ⚠️ La frase del caso multi la ricompone il FE da
                       `registri_n`, e NON legge quella che il BE ha messo nel
                       campo: quella è italiana e serve all'export, che la
                       lingua del richiedente non la sa. Le due non possono
                       divergere perché dipendono dallo STESSO numero.
                       ⚠️ Il vuoto è «—» e non la frase: `registri_n <= 1` col
                       codice assente vuol dire «non lo so», che è un fatto
                       diverso da «sono più di uno» — succede sui gruppi il cui
                       tipo documento non è ancora stato scelto. -->
                  <template #cell-registro="{ data }">
                    <span
                      v-if="Number(data.registri_n) > 1"
                      class="app-dash-registro-multi"
                      v-tooltip.bottom="t('vendite.dashboard_competenza.col_registro_multi_tooltip')"
                    >
                      <i :class="STATUS_ICONS.MULTIPLI" />
                      {{ t('vendite.dashboard_competenza.col_registro_multi', { n: data.registri_n }) }}
                    </span>
                    <span v-else>{{ data.registro_codice || '—' }}</span>
                  </template>
                  <!-- data_documento_prevista non ha slot: il seed dichiara
                       `date_short`, e una data si formatta dove si formattano
                       tutte le altre. Vuota dove il documento esiste già
                       (D-9) — una previsione su un documento nato non ha senso. -->

                  <template #actions="{ data }">
                    <RowActionsMenu :row="data" :actions="buildGruppoRowActions(data)" />
                  </template>
                </ListaConfigurabile>
                <!-- Empty-state ONESTO (regola del BB usePagedDashFetch): «nessun
                     gruppo» si dice solo dopo una fetch RIUSCITA. Prima — o dopo un
                     errore di rete — la lista e' vuota per ignoranza, non per
                     assenza di lavoro, e dichiararlo sarebbe una bugia che invita a
                     chiudere il mese. -->
                <div v-else-if="gruppiLoaded" class="app-empty-state">
                  <i :class="STATUS_ICONS.TUTTO_OK" />
                  <p>{{ t('vendite.dashboard_competenza.nessun_gruppo') }}</p>
                </div>
              </template>

              <!-- Card «Emesse non fatturate»: il drill-down scende sui RESIDUI,
                   non sulle commesse. Motivo: qui il verbo e' «Riporta da
                   emettere» e agisce su un'ATTIVITA' — la commessa aggregata
                   non direbbe su cosa si sta per agire.
                   ⚠️ La lista mostra MENO della card, ed e' voluto: lo stadio
                   contiene tre situazioni e solo `RESIDUO` chiede
                   un'azione. Il numero grande e' «quanto lavoro e' fermo qui»,
                   la lista e' «su cosa si puo' agire» — e la card lo dichiara
                   con la riga «di cui N da recuperare». -->
              <template v-else-if="stadioSelezionato === STADIO_RESIDUI">
                <div class="app-page-toolbar">
                  <h4 class="app-dash-fermi-title">
                    {{ t('vendite.dashboard_competenza.residui_titolo') }}
                  </h4>
                  <!-- Il verbo di massa. Gate su permesso E readonly, come i
                       fratelli; spento a selezione vuota. Il tooltip sta sul
                       WRAPPER perche' un bottone disabilitato non riceve
                       eventi del mouse — ed e' spento che il motivo serve. -->
                  <span
                    v-if="canRiportare"
                    v-tooltip.bottom="t('vendite.dashboard_competenza.riporta_tooltip')"
                    class="app-dash-fattura-wrap"
                  >
                    <Button
                      :label="t('vendite.dashboard_competenza.riporta', { n: selezioneResidui.length })"
                      :icon="MANAGE_ICONS.RIPORTA"
                      size="small"
                      severity="warn"
                      :loading="riportoInCorso"
                      :disabled="selezioneResidui.length === 0 || riportoInCorso"
                      @click="riportaSelezionati"
                    />
                  </span>
                </div>
                <ListaConfigurabile
                  v-if="residuiCount > 0 || residuiLoading"
                  ref="listaResiduiRef"
                  codice="vendite.dash_competenza_residui"
                  data-key="attivita_fatturabile_id"
                  :rows="residui"
                  :total="residuiCount"
                  :loading="residuiLoading"
                  :paginator-options="residuiPaginatorOptions"
                  :page="residuiPage"
                  :sort-field="residuiOrderBy"
                  :sort-order="residuiSortOrder"
                  @page="onResiduiPage"
                  @sort="onResiduiSort"
                >
                  <!-- Selezione: chrome del BB (slot dedicato), non colonna di
                       catalogo. PrimeVue 4 non ha piu' il predicato per-riga sul
                       selectionMode, quindi la checkbox e' custom. -->
                  <template v-if="canRiportare" #selection-header>
                    <Checkbox
                      binary
                      :model-value="tuttiResiduiSelezionati"
                      :indeterminate="alcuniResiduiSelezionati"
                      :disabled="!residuiSelezionabili.length"
                      @update:model-value="toggleTuttiResidui"
                    />
                  </template>
                  <template v-if="canRiportare" #selection="{ data }">
                    <Checkbox
                      binary
                      :model-value="isResiduoSelezionato(data)"
                      :disabled="!isResiduoSelezionabile(data)"
                      @update:model-value="toggleResiduo(data)"
                    />
                  </template>

                  <template #cell-commessa_codice="{ data }">
                    {{ data.commessa_codice ?? `#${data.commessa_id}` }}
                  </template>
                  <template #cell-cliente_display="{ data }">
                    {{ data.cliente_display ?? '—' }}
                  </template>
                  <template #cell-articolo="{ data }">
                    {{ data.articolo_codice ?? '—' }}
                  </template>
                  <template #cell-articolo_descrizione="{ data }">
                    {{ data.articolo_descrizione ?? '—' }}
                  </template>
                  <!-- ⭐ Il lotto di PROVENIENZA: risponde a «da dove viene
                       questo residuo», che prima non si vedeva da nessuna
                       parte. Non e' `lotto_id` — quello nasce dalla catena
                       della fattura, e su un residuo la fattura non c'e'. -->
                  <template #cell-lotto_provenienza="{ data }">
                    <Button
                      v-if="data.lotto_provenienza_id"
                      link
                      class="app-cell-link"
                      :label="data.lotto_provenienza_codice ?? String(data.lotto_provenienza_id)"
                      v-tooltip.top="t('vendite.dashboard_competenza.apri_lotto')"
                      @click="apriLotto(data.lotto_provenienza_id)"
                    />
                    <span v-else>—</span>
                  </template>
                  <template #cell-motivo_non_fatturata="{ data }">
                    <Tag :value="motivoLabel(data.motivo_non_fatturata)" severity="warn" />
                  </template>
                  <!-- competenza_mese, data_attivita e valore non hanno slot:
                       il seed dichiara `date_short` e `currency_eur`. -->
                </ListaConfigurabile>
                <!-- ⚠️ `residuiLoaded` e non `!residuiLoading`: un empty-state
                     positivo su una fetch mai riuscita direbbe «non c'e' niente
                     da recuperare» quando invece non lo sappiamo. -->
                <div v-else-if="residuiLoaded" class="app-empty-state">
                  <i :class="STATUS_ICONS.TUTTO_OK" />
                  <p>{{ t('vendite.dashboard_competenza.residui_vuoto') }}</p>
                </div>
                <div v-else class="app-empty-state">
                  <i :class="STATUS_ICONS.VUOTO" />
                  <p>{{ t('vendite.dashboard_competenza.residui_placeholder') }}</p>
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
                      <i :class="STATUS_ICONS.IN_RITARDO" /> {{ data.n_in_ritardo }}
                    </span>
                    <span v-else>—</span>
                  </template>

                  <!-- Azioni riga (Fase A cockpit): Approva (solo DA_APPROVARE,
                       l'intera commessa) + Apri commessa (drawer col dettaglio). -->
                  <template #actions="{ data }">
                    <RowActionsMenu :row="data" :actions="buildCommessaRowActions(data)" />
                  </template>
                </ListaConfigurabile>
                <div v-else class="app-empty-state">
                  <i :class="STATUS_ICONS.TUTTO_OK" />
                  <p>{{ t('vendite.dashboard_competenza.nessuna_commessa') }}</p>
                </div>
              </template>
              <div v-else class="app-empty-state">
                <i :class="STATUS_ICONS.VUOTO" />
                <p>{{ t('vendite.dashboard_competenza.commesse_hint') }}</p>
              </div>
            </div>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </div>
    </div>

    <!-- Drawer di governo commessa (A-4): riapprovvigiona la dashboard al save. -->
    <CommessaGestioneDrawer
      v-model:visible="commessaDrawerVisible"
      :commessa-id="commessaDrawerId"
      :stato-emissione="commessaDrawerStatoEmissione"
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

    <!-- FE-1: la data documento dei lotti che stanno per nascere. Facoltativa:
         vuota = la decide la politica del registro. Questo dialog ha PRESO IL
         POSTO della conferma secca, quindi porta anche il testo che dichiara il
         peso dell'operazione (`perimetro-testo`). -->
    <NumerazioneDataDialog
      v-model:visible="dialogDataCreazione.visible"
      :modo="MODO_DATA_DOCUMENTO.CREAZIONE"
      :competenza-mese="competenzaCorrente"
      :perimetro-testo="dialogDataCreazione.perimetro"
      :azione="confermaDataCreazione"
    />

  </div>
</template>
