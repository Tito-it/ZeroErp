<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
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
import Tag from 'primevue/tag'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Message from 'primevue/message'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import SelectButtonGravita from '../../core/components/SelectButtonGravita.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import BersaglioAzioni from '../../core/components/BersaglioAzioni.vue'
import { labelOrCode } from '../../core/utils/i18nLabel'
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
import AppDialog from '../../core/components/AppDialog.vue'
import Textarea from 'primevue/textarea'
import { useDocumentiPerSorgenteStore } from '../../documenti/stores/documentiPerSorgente'
import { SORGENTE_CODES } from '../../documenti/constants'
import { downloadBlob } from '../../core/utils/download'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { mapAvailableActionsToDrawerActions } from '../../core/composables/useDrawerActions'
import {
  useLottoAzioni,
  LOTTO_AZIONE_PERMESSO,
  LOTTO_AZIONE_PIPELINE_UI,
} from '../composables/useLottoAzioni'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { extractApiError } from '../../core/utils/apiError'
import {
  statoEsecuzioneLottoSeverity,
  statoLottoSeverity,
  statoTaskRunSeverity,
} from '../../core/utils/severity'
import {
  getLotto,
  listLottoFatture,
  escludiDocumentiDaGiro,
  listLottoGruppi,
  listLottoTaskRuns,
  getLottoSegnalazioni,
  listLottoSegnalazioni,
  exportLottoFatture,
  exportLottoGruppi,
  exportLottoTaskRuns,
  exportLottoSegnalazioni,
  eliminaFatturaDaLotto,
} from '../api/lotti'
// ⭐ Il gesto «apri il documento / apri la commessa» del kebab dei documenti
// presi in carico passa dal RESOLVER GLOBALE dei bersagli, non da drawer
// montati qui: l'ospite è UNO SOLO, in `App.vue`, e la mappa tipo→destinazione
// applica già i guard dei permessi. Montarne di propri vorrebbe dire una
// seconda catena — e un pulsante che porta su «accesso negato» dove l'altra
// non lo mostra affatto.
import { BERSAGLIO_TIPI, normalizzaBersagli } from '../../core/bersagli'
import { azioniDaBersagli } from '../../core/bersaglioGesto'
import { useAuthStore } from '../../stores/auth'
import { STATO_ESECUZIONE_LOTTO, LOTTO_SCHEDE } from '../constants'
import { useSelezioneDocumentiLotto } from '../composables/useSelezioneDocumentiLotto'
import { scegliRamoBanner, conteggiDaSegnalazioni } from '../_shared/lotti/ramoBannerLotto'
import { AZIONE_RIGA_USCITA_DAL_GIRO } from '../uscitaDalGiro'
import { useAzioneRiga } from '../../core/composables/useAzioneRiga'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useContrattoFiltriLocali } from '../../core/composables/useContrattoFiltriLocali'
import GiornaleEntitaTab from '../_shared/giornale/GiornaleEntitaTab.vue'
import { useLottoGiornaleStore } from '../stores/giornaleEntita'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

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
// «Togli dal giro»: il motivo del pulsante spento dalle colonne che il registro
// delle azioni di riga nomina (FE-1). Lo stesso BB della casella di selezione.
const uscitaDalGiro = useAzioneRiga(AZIONE_RIGA_USCITA_DAL_GIRO)
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
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
const listaDocumenti = useListaDrawerPaginata(({ limit, offset, sortBy, sortDir }) =>
  listLottoFatture(props.lottoId, {
    limit, offset, ...(sortBy ? { order_by: sortBy, order_dir: sortDir } : {}),
  }))
// ⭐ LA QUARTA SCHEDA — I DOCUMENTI PRESI IN CARICO (brief-db-esito-gruppo-lotto).
//
// ⛔ NON è un doppione della scheda «Documenti», ed è la ragione per cui esiste.
//    Quella elenca `fatturazione_lotti_fatture`, che si aggancia a
//    `fattura_id`: un documento caduto PRIMA che una fattura esista non ha
//    niente a cui appendersi. Sul lotto LTF-0009578 se ne vedevano DUE su tre,
//    e il terzo era nominato solo da una segnalazione — per giunta con
//    l'identificativo della COMMESSA, così che la segnalazione sembrava
//    sbagliata mentre era l'unica cosa vera in giro.
//
// ⚠️ Le due liste non sono in corrispondenza 1:1 nemmeno a giro riuscito: una
//    fattura può raccogliere più documenti. Sono due domande diverse, non due
//    viste della stessa — per questo è una scheda e non una colonna in più.
//
// Nessun ordinamento iniziale dichiarato: il default lo decide il backend e
// mette in cima i FALLITI, che è la domanda con cui questa scheda si apre.
// ⛔ NIENTE FLAG «questo lotto dichiara un perimetro», e la sua sparizione è
//    il segno che il database ha risolto il problema invece di spostarlo
//    (rev 2026-09-07). Serviva perché la lista leggeva il solo PERIMETRO, che i
//    giri di massa non scrivono: zero righe voleva dire due cose. Ora legge
//    anche gli ESITI, che ci sono su entrambi i tipi di giro, e zero righe ne
//    vuol dire una sola.
const listaGruppi = useListaDrawerPaginata(
  ({ limit, offset, sortBy, sortDir }) =>
    listLottoGruppi(props.lottoId, { limit, offset, orderBy: sortBy, orderDir: sortDir }),
)

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
  async ({ limit, offset, sortBy, sortDir }) => {
    const res = await listLottoTaskRuns(props.lottoId, {
      limit, offset, orderBy: sortBy, orderDir: sortDir,
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
  ({ limit, offset, sortBy, sortDir }) =>
    listLottoSegnalazioni(props.lottoId, {
      livello: livelloSegnalazioni.value, limit, offset, orderBy: sortBy, orderDir: sortDir,
    }),
  { sortBy: 'data_ora', sortDir: -1 },
)

// Azioni di lista (personalizza colonne + esporta): lo stesso BB delle altre
// liste standard, una istanza per tab.
// ⭐ L'export riceve gli STESSI filtri e lo STESSO ordinamento della lista a
// video: il file E' la lista, non una seconda query che le somiglia.
const listaDocumentiRef = ref(null)
const listaGruppiRef = ref(null)
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
          order_by: listaDocumenti.sortField.value,
          order_dir: listaDocumenti.sortOrder.value === -1 ? 'desc' : 'asc',
        }
      : {}),
  }),
})
const azioniGruppi = useListaAzioni(() => listaGruppiRef.value, {
  exportFn: (params) => exportLottoGruppi(props.lottoId, params),
  getExportParams: (formato) => ({
    formato,
    // ⚠️ L'ordinamento viaggia col file: il file È la lista, non una seconda
    // query che le somiglia. Il verso si manda solo con la colonna — da solo
    // annullerebbe il default del backend, che mette i falliti in cima.
    ...(listaGruppi.sortField.value
      ? {
          order_by: listaGruppi.sortField.value,
          order_dir: listaGruppi.sortOrder.value === -1 ? 'desc' : 'asc',
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
// ⭐ LA SELEZIONE DELLA SCHEDA «DOCUMENTI»: chi si può togliere dal giro lo dice
//    il database in riga, e il telaio lo gira alle caselle. ⚠️ `abilitata` è
//    falsa in sola lettura: senza, la colonna delle caselle comparirebbe a chi
//    non può farci niente.
const selezioneDocumenti = useSelezioneDocumentiLotto({
  righeVisibili: computed(() => listaGruppi.righe.value),
  abilitata: computed(() => !isReadonly.value),
})

// ⭐ L'AZIONE DI MASSA compare SOLO con qualcosa spuntato, e porta il conteggio
//    nell'etichetta: un pulsante che dice «(3)» è già la conferma di ciò che
//    l'operatore ha selezionato, prima ancora della dialog.
// ⛔ Non è un secondo verbo: apre la STESSA conferma e chiama la STESSA API
//    della riga singola — che è una lista di uno.
// ⭐ IL SEGNO DEL VERBO «TOGLI DAL GIRO», in un posto solo — lo portano la voce
//    di riga e il pulsante di massa, che sono lo STESSO gesto: due segni diversi
//    per lo stesso atto si leggono come due atti.
//
// ⛔ NON `pi-sign-out`, che era la prima scelta ed era sbagliata (rilievo di
//    Tid): quella è **letteralmente** l'icona del logout, la stessa che
//    `AppTopbar` usa per uscire dall'applicazione. Un segno già impegnato
//    altrove non diventa disponibile perché la metafora torna.
// ⭐ Una X, e ROSSA: l'uscita è a senso unico (D-3) e cancella la bozza — per
//    rimettere tutto in un lotto solo si annulla il lotto e lo si rigenera.
//    L'arancio dice «attenzione», il rosso dice «non si torna indietro», ed è
//    lo stesso colore che la conferma porta già sul pulsante.
const ESCLUDI_ICON = MANAGE_ICONS.CANCEL
const ESCLUDI_SEVERITY = 'danger'

const barraGruppiBase = conRicarica(azioniGruppi.azioniLista, () => listaGruppi.carica())
const barraGruppi = computed(() => {
  // ⛔ LO STESSO CANCELLO DELLA COLONNA DELLE CASELLE, e non un secondo: quando
  //    `perLista` è `null` la selezione non è più offerta — sola lettura, o
  //    permesso assente — ma l'array di ciò che era già spuntato resta lì. Senza
  //    questa riga il pulsante di massa sopravviverebbe alle caselle che l'hanno
  //    riempito: un lotto che avanza di stato mentre lo si guarda toglierebbe i
  //    quadratini e lascerebbe un «Togli dal giro (3)» che nessuno può più
  //    disfare. È l'idioma già in uso su `CodaTabBase`.
  const n = selezioneDocumenti.perLista.value ? selezioneDocumenti.ids.value.length : 0
  if (!n) return barraGruppiBase.value
  return [
    {
      key: 'escludi-selezione',
      kind: 'primary',
      label: t('vendite.lotti.gruppo_escludi_n', { n }),
      icon: ESCLUDI_ICON,
      severity: ESCLUDI_SEVERITY,
      action: 'reset_lotto_fattura_draft',
      command: () => apriEsclusione({ chiavi: selezioneDocumenti.ids.value }),
    },
    ...barraGruppiBase.value,
  ]
})
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
// Il blob sta SOTTO `capabilities` (api.md §«Il blob sta SOTTO `capabilities`»).
const capabilities = computed(() => lotto.value?.capabilities ?? {})
const availableActions = computed(() => capabilities.value.available_actions ?? [])

// ⭐ IL LOTTO E' FERMO? LO DICE IL BACKEND, e qui si LEGGE — non si ricalcola.
//    `blocks_next_step` e' il verdetto di `LottoSegnalazioniService`: critiche
//    vive + fatture in errore + (dal 2026-09-12, D2) documenti il cui ultimo
//    esito e' ERRORE. Il DB non conosce le segnalazioni, il BE le somma agli
//    esiti, il FE rende.
// 🔴 Fino al 12-09 questo gate era `critical_count > 0`, cioe' una COPIA del
//    verdetto di allora. Coincidevano per costruzione, e D2 e' il giorno in cui
//    si sfilano: con soli esiti in errore la copia avrebbe acceso «Avanza» su
//    un lotto che il runner rifiuta, e nessun banner su un lotto in ERRORE —
//    il vicolo cieco, con il client che mente. Un gate in due sedi e' la copia
//    che il piano §9.3 toglie: non se ne tiene una «per compatibilita'».
// ⚠️ Fail-closed sul payload non ancora arrivato: `undefined` non e' «libero».
const lottoFermo = computed(() => segnalazioni.value?.blocks_next_step === true)

// Scopo: ⭐ LA FRASE DEL BANNER, che dal 2026-09-08 conta GESTI e non allarmi.
//
// 🔴 Il difetto che chiude: «3 segnalazioni critiche bloccano l'avanzamento» è
//    un numero VERO che descrive la cosa sbagliata. Un documento con tre
//    critiche resta UN documento, e il gesto che l'operatore ha davanti è uno
//    solo — «togli questo dal giro». Chi leggeva tre si preparava a tre.
//
// ⚠️ FORMA PLURALE, e la sceglie il numero che è SOGGETTO della frase. «1
//    documenti su 3» non è un dettaglio di stile: è la prima riga che si legge
//    su un lotto fermo, e una frase sgrammaticata lì fa sembrare rotto il resto.
// 🔴 L'ORDINE DEGLI ARGOMENTI È `t(chiave, {nomi}, plurale)` E NON IL CONTRARIO,
//    ed è un difetto già commesso qui: con `t(chiave, plurale, {nomi})` vue-i18n
//    legge il terzo posto come OPZIONI e ogni segnaposto DIVERSO da `n`
//    sparisce — a video usciva «fermo per 1 documento su : si toglie…», nessun
//    errore, solo un buco dove c'era il totale. ⚠️ E il `{n}` sopravviveva,
//    perché vue-i18n inietta da sé il conteggio con quel nome: è la trappola in
//    cui stanno gli altri 18 messaggi plurali del progetto, che funzionano solo
//    perché hanno il SOLO `{n}`.
//
// ⭐ IL GIRO E' ANCORA RIMEDIABILE? La soglia e' UNA SOLA e si LEGGE, non si
//    riscrive: `congela_fiscale` del catalogo, la stessa che `useLottoAzioni`
//    consulta per proporre i verbi. ⛔ Non `stato_doc_fiscale_codice !== 'DRAFT'`
//    — quella era l'ennesima copia, tolta da questo stesso file il 2026-08-31.
// ⚠️ Fail-closed (`=== false`): un dettaglio non ancora arrivato non conta come
//    «si puo' rimediare».
const giroRimediabile = computed(() => lotto.value?.stato_congela_fiscale === false)

// ⭐ LA SCELTA DEL RAMO VIVE IN UNA FUNZIONE PURA (`scegliRamoBanner`, F2-bis
//    del 2026-09-12): cinque rami su due assi — rimediabile × specie del blocco
//    (critiche di documento, critiche del giro, critiche del canale fattura,
//    esiti in errore, fatture in errore) — e ognuno ha il suo caso nella spec.
//    Qui resta solo `t()`: le regole di precedenza (le critiche vive vincono
//    sugli esiti, i conteggi non si sommano, il giro congelato parla al
//    passato senza proporre gesti) stanno la', con il loro perche'.
// ⚠️ I ramo `null` non e' un vuoto: e' «il backend blocca per una ragione che
//    questo client non conosce» — un quarto addendo futuro. Si rende con la
//    frase generica, cosi' si VEDE invece di sparire.
const ramoBanner = computed(() => {
  if (!lottoFermo.value) return null
  return scegliRamoBanner(conteggiDaSegnalazioni(segnalazioni.value, giroRimediabile.value))
})

const fraseBanner = computed(() => {
  const ramo = ramoBanner.value
  if (!ramo) return t('vendite.lotti.blocca_step')
  // ⚠️ `(chiave, {nomi}, plurale)` e non il contrario: con l'ordine inverso
  //    vue-i18n legge il terzo posto come OPZIONI e ogni segnaposto diverso da
  //    `n` sparisce — difetto gia' pagato qui. Le parti sono frasi INTERE
  //    giustapposte, mai frammenti: un pezzo senza soggetto non si traduce.
  return ramo.parti
    .map((p) => (p.plurale === undefined ? t(p.chiave, p.argomenti) : t(p.chiave, p.argomenti, p.plurale)))
    .join(' ')
})

// Tab attiva CONTROLLATA (era fissa a "fatture"): serve al link del banner, che
// porta l'operatore sulla scheda invece di dirgli dove guardare.
const tabAttiva = ref(LOTTO_SCHEDE.DOCUMENTI)

// ------------------------------------------------------ la STORIA del lotto
// ⭐ La quinta scheda (Passo A, seconda meta'). Non e' un altro elenco di
//    problemi: le altre dicono COSA C'E' ORA — i documenti, i tentativi, le
//    segnalazioni aperte — questa dice COSA E' SUCCESSO, in che ordine,
//    comprese le cose andate bene e i tentativi poi superati.
// ⭐ Dal 2026-09-27 e' la lista a catalogo `vendite.giornale` (la stessa del
//    giornale trasversale e della Storia della fattura), resa dal tab
//    condiviso `GiornaleEntitaTab`: colonne dal catalogo, paginatore,
//    personalizzazione — e il filtro «solo problemi», che e' solo del lotto,
//    dichiarato dal suo store. Qui resta lo store, da cui la scheda legge il
//    conteggio. Il tab si monta col lotto (i pannelli di `Tabs` non sono
//    lazy), quindi la storia si chiede all'apertura e riparte dal suo default
//    a ogni lotto — il tab si azzera da se' al cambio di entita'.
// ⛔ Non era scrivibile prima del 2026-08-24 19:33. Qui i registri sono TRE, e
//    con l'orario di TRANSAZIONE le righe di una stessa transazione uscivano
//    tutte con lo stesso istante: una timeline che mostra una sequenza mai
//    avvenuta, e che guardandola non sembra rotta (R-1, risolto dal team DB).
const giornaleStore = useLottoGiornaleStore()

// Scopo: il contratto dei filtri delle sotto-liste del lotto — chi sono, che
//        default hanno, il segno che mostrano e «Pulisci filtri».
// ⭐ Nascono VALORIZZATI (`RILEVANTI`, «solo problemi», `CRITICHE`): finche'
//    nessuno li tocca il numero e' GRIGIO — «ristretta come nasce» — e al primo
//    cambio diventa BLU. E' il caso per cui i due colori esistono.
// ⚠️ Nessun `onAzzera`: queste liste ricaricano da se', col `watch` sul filtro.
const {
  segno: segnoAmpiezzaTask,
  azzeraFiltri: azzeraAmpiezzaTask,
} = useContrattoFiltriLocali({
  // ⛔ `'TUTTI'` NON RESTRINGE, e va detto: `AMPIEZZE_TASK.TUTTI` e' `null`,
  //    cioe' nessun filtro di stato sui task. Senza, il segno contava 1 proprio
  //    sull'ampiezza piu' larga — lo stesso verso sbagliato del «mostra tutto»
  //    della Storia (oggi dichiarato come `filtriNeutri` del suo store).
  ampiezza: { rif: ampiezzaTask, default: 'RILEVANTI', neutro: 'TUTTI' },
})

// Livello dell'elenco segnalazioni. Parte dalle CRITICHE perché sono quelle che
// fermano il lotto — chi apre la scheda ci arriva per quelle.
const LIVELLI_SEGNALAZIONE = { CRITICHE: 'C', AVVISI: 'W', ATTENZIONI: 'I' }
const livelloSegnalazioni = ref(LIVELLI_SEGNALAZIONE.CRITICHE)
const {
  segno: segnoLivelloSegnalazioni,
  azzeraFiltri: azzeraLivelloSegnalazioni,
} = useContrattoFiltriLocali({
  livello: { rif: livelloSegnalazioni, default: LIVELLI_SEGNALAZIONE.CRITICHE },
})
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

// Scopo: il link del banner — porta sulla scheda DEL RAMO. Le critiche stanno
//        su «Segnalazioni», gia' filtrata su di loro (rimette il livello anche
//        se l'operatore l'aveva cambiato: il banner parla di quelle, atterrare
//        sugli avvisi sarebbe una risposta a un'altra domanda). Un documento il
//        cui ultimo esito e' ERRORE senza critica viva (D2) NON ha una riga la',
//        e nemmeno fra le fatture (se il pull e' fallito la fattura non e' mai
//        nata): la sua riga sta su «Presi in carico», con `ErroreRigaInfo` e
//        «Togli dal giro». ⛔ Mandarlo altrove aprirebbe un elenco che quella
//        riga non la contiene — il vicolo cieco che le linee guida vietano.
async function apriSegnalazioni() {
  const scheda = ramoBanner.value?.scheda ?? LOTTO_SCHEDE.SEGNALAZIONI
  tabAttiva.value = scheda
  if (scheda === LOTTO_SCHEDE.SEGNALAZIONI && livelloSegnalazioni.value !== LIVELLI_SEGNALAZIONE.CRITICHE) {
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
    livello: livelloSegnalazioni.value, limit: 1,
  })
  segnalazioniFuoriJob.value = res.data?.data?.fuori_job_count ?? 0
  livelloCaricato.value = livelloSegnalazioni.value
}

async function loadTabs() {
  tabLoading.value = true
  try {
    const [sRes] = await Promise.all([
      getLottoSegnalazioni(props.lottoId),
      listaDocumenti.carica(),
      listaGruppi.carica(),
      listaTask.carica(),
      caricaSegnalazioni(),
      // ⭐ La Storia si rilegge con le altre schede: `reloadAll` gira dopo ogni
      //    azione sul lotto (avanza, rilancia, uscita dal giro), e ciascuna
      //    scrive nel giornale. Senza, la scheda e il suo contatore restano a
      //    prima dell'azione. Pagina e filtri restano: e' un riallineamento,
      //    non un padre nuovo. ⚠️ Solo se gia' letta: la prima lettura (e
      //    quella di un lotto nuovo) la fa il tab, e qui sarebbe un doppione.
      giornaleStore.hasSearched ? giornaleStore.fetchList() : null,
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
    listaGruppi.reset()
    listaTask.reset()
    listaSegnalazioni.reset()
    // Riapertura = si riparte dai DOCUMENTI, sempre. Senza questo reset il
    // drawer riapriva sulla scheda dove l'operatore era finito l'ultima volta
    // (tipicamente «Segnalazioni», dove l'aveva portato il link del banner):
    // un drawer che si apre in un punto diverso a ogni giro fa perdere il
    // riferimento. Stessa ragione per il livello del filtro.
    tabAttiva.value = LOTTO_SCHEDE.DOCUMENTI
    // ⛔ I default vengono dalla SEDE UNICA (il contratto dei filtri), non
    //    riscritti qui: due letterali dello stesso default divergono al primo
    //    che qualcuno cambia, e il segno resterebbe a raccontare il vecchio.
    azzeraLivelloSegnalazioni()
    livelloCaricato.value = null
    // Stessa ragione del livello: il drawer riapre sempre dallo stesso punto.
    azzeraAmpiezzaTask()
    esclusiTask.value = 0
    // ⚠️ La storia NO: riparte dal suo default da se' — il BB del tab
    // (`useDrawerTabLista`) riparte da capo a ogni cambio di lotto.
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
    // La numerazione è uno STEP di pipeline: su un lotto fermo il runner la
    // rifiuta (`blocks_next_step`). Il DB non conosce le segnalazioni, quindi
    // questo disabilitato lo aggiunge chi ha il verdetto: noi, LEGGENDOLO. Non
    // sovrascrive un `disabled` già vero arrivato dalle `fn_check_*` (né il
    // suo tooltip, che spiega il motivo del DB).
    ...(a.key === 'numera' && lottoFermo.value && !a.disabled
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
    // step, che su un lotto fermo il runner ammette (è la via d'uscita — e
    // per gli esiti in errore di D2 è l'UNICA: il pull rivede il documento e
    // scrive l'esito nuovo). Bloccarlo qui toglierebbe l'unica strada per
    // uscire proprio ai lotti riaperti.
    const bloccato = key === 'avanza_step' && lottoFermo.value
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
    header: t('vendite.lotti.reset_fattura_header'),
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
  // ⭐ IL PERIMETRO NON SI RICALCOLA PIU' QUI (F5, 2026-08-31). Fino a oggi
  // questa funzione portava `const PRE_FISCALI = ['DRAFT','EMESSA']` e
  // confrontava a mano lo stato della riga e quello del lotto: era la NONA
  // copia della soglia di congelamento, l'ultima rimasta fuori dal database
  // dopo che `D33` aveva portato le altre sette a leggere
  // `config.stati_doc_fiscale.congela_fiscale`. Una copia in un template Vue
  // e' quella che il DB non puo' vedere: il giorno che il confine si sposta,
  // questa riga non se ne accorge e non fallisce — accende un pulsante che
  // fallira'.
  //
  // Ora il motivo arriva dalla riga (`can_reset_fattura*`), e lo produce
  // `script.fn_check_fattura_eliminabile_da_lotto`, cioe' la STESSA funzione
  // che il database usa per RIFIUTARE. Tooltip e rifiuto non «coincidono
  // oggi»: non possono divergere.
  //
  // ⚠️ PERMESSO => NASCONDI, STATO => DISABILITA COL MOTIVO. `canResetFattura`
  // e' il permesso e continua a nascondere la voce; lo stato invece la lascia
  // visibile e SPENTA, con il perche' — un pulsante grigio che non spiega
  // niente e' indistinguibile da un bug.
  if (!isReadonly.value && canResetFattura.value) {
    // Fail-closed: capability assente = azione spenta. Su un verbo che
    // CANCELLA il documento, «non lo so» non puo' voler dire «vai».
    const resetBloccato = row.can_reset_fattura !== true
    actions.push({
      key: 'elimina',
      label: t('vendite.lotti.azione_reset_fattura'),
      disabled: resetBloccato,
      // ⛔ Il testo del motivo non viaggia nel payload: viaggia la CHIAVE, e
      // il ripiego e' il codice macchina — chiave mancante => si vede il
      // codice, non un tooltip vuoto.
      // ⚠️ La chiave puo' NON esserci sul ramo fail-closed (payload vecchio,
      // capability assente): `labelOrCode` chiamata con `undefined` chiederebbe
      // a `te()` una chiave che non e' una stringa. Si passa il ripiego
      // direttamente — che e' il codice macchina, e in ultima istanza la label.
      tooltip: resetBloccato
        ? (row.can_reset_fattura_reason_key
          ? labelOrCode(
            t,
            te,
            row.can_reset_fattura_reason_key,
            row.can_reset_fattura_reason || t('vendite.lotti.azione_reset_fattura'),
          )
          : row.can_reset_fattura_reason || t('vendite.lotti.azione_reset_fattura'))
        : undefined,
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

const auth = useAuthStore()

// Scopo: le azioni del kebab sui DOCUMENTI PRESI IN CARICO — «apri il
//        documento» e «apri la commessa da correggere».
//
// ⭐ SI COSTRUISCONO DAL RESOLVER DEI BERSAGLI, non a mano. La mappa
//    tipo→destinazione vive in `core/bersagli.js`, applica i guard dei permessi
//    e apre l'ospite globale di `App.vue`: qui non si monta nessun drawer.
//    ⚠️ E `tipo_gruppo` È già il vocabolario di quella mappa — sono entrambi i
//    `config.sorgenti.codice_interno`. Non c'era una tabella da inventare, ce
//    n'era una da riconoscere.
//
// ⛔ Il degrado è dichiarato e va tenuto: un tipo senza destinazione (le voci
//    manuali, `ONERI_COMMESSA`), un documento fuori scope, un'area BLOCCATA →
//    nessuna voce. Mai un pulsante che porta in un vicolo cieco (§4.3 di
//    `brief-db-bersaglio-errore`).
//
// ⚠️ La commessa esce SOLO quando ce n'è una: `commesse_n > 1` significa che il
//    documento ne alimenta più d'una, e offrirne una a caso sarebbe una
//    scommessa travestita da regola — la stessa ragione per cui il backend
//    lascia `commessa_id` a NULL in quel caso.
function buildGruppoRowActions(row) {
  const bersagli = []
  if (row.documento_id && row.tipo_gruppo) {
    bersagli.push({ type: row.tipo_gruppo, id: row.documento_id })
  }
  bersagli.push(...bersaglioCommessa(row))
  const azioni = azioniDaBersagli(normalizzaBersagli(bersagli), auth).map((azione, i) => ({
    key: `bersaglio_${i}`,
    label: azione.label,
    icon: azione.icon,
    command: azione.esegui,
  }))
  if (isReadonly.value) return azioni
  azioni.push(azioneEscludi(uscitaDalGiro.motivo(row), row))
  return azioni
}

// Scopo: ⭐ IL VERBO «TOGLI DAL GIRO» IN UN POSTO SOLO — la voce di riga che
//        libera gli altri documenti del lotto. La rendono DUE schede, e questo
//        è ciò che le tiene la stessa azione invece di due che si somigliano:
//        stessa etichetta, stessa icona, stesso permesso, stesso comando.
//
// ⛔ SI SPEGNE COL MOTIVO, NON SI NASCONDE (§12.1 delle linee guida): lo STATO
//    disabilita spiegando, il PERMESSO nasconde. Il permesso lo applica
//    `action`; lo stato arriva dal database e passa da qui come `motivo`.
// ⭐ E LA FIRMA RENDE LA REGOLA STRUTTURALE: non c'è modo di spegnere questa
//    voce senza dire perché, perché `disabled` NON è un parametro — si deduce
//    dalla presenza del motivo. Un `disabled` indipendente sarebbe la terza via
//    vietata dal §12, disponibile per distrazione.
// ⚠️ Il campo si chiama `tooltip`, non `motivo`: `RowActionsMenu` legge quello,
//    e da lì ricava da sé sia il tooltip inline sia la riga sotto la voce nel
//    kebab — che su touch è l'unico posto in cui il motivo si vede. Un
//    `motivo:` non lo legge nessuno.
function azioneEscludi(motivo, payload) {
  return {
    key: 'escludi',
    label: t('vendite.lotti.gruppo_escludi'),
    icon: ESCLUDI_ICON,
    severity: ESCLUDI_SEVERITY,
    disabled: Boolean(motivo),
    tooltip: motivo,
    // Stesso potere della cancellazione di una bozza dal lotto, che questo
    // verbo COMPONE: non è un'altra facoltà, e un codename proprio direbbe
    // che lo è.
    action: 'reset_lotto_fattura_draft',
    command: () => apriEsclusione(payload),
  }
}

// Scopo: le azioni di riga della scheda CRITICHE. ⭐ È la seconda superficie
//        dello stesso verbo — «togli dal giro» — e non ne è una copia: chiama
//        la stessa funzione con lo stesso stato. *Stessa azione, seconda
//        superficie, un verbo solo.*
//
// ⭐ E QUI IL POSTO È GIUSTO: quando un documento rompe il giro, l'operatore è
//    su questa scheda. Era l'ipotesi di partenza di Tid — «nell'area Critiche si
//    annulla il messaggio» — con l'oggetto corretto: il gesto si appende al
//    DOCUMENTO, non al messaggio. Un documento può avere più critiche, e
//    toglierlo dal messaggio richiederebbe N gesti.
//
// ⛔ SULLE CRITICHE DEL GIRO L'AZIONE È SPENTA COL MOTIVO, MAI NASCOSTA (§12.1):
//    togliere la voce farebbe sparire l'azione senza spiegazione, e chi la
//    cercava non saprebbe se è un permesso, un bug o una versione vecchia.
// ⚠️ E quel motivo NON viene dal database, ed è l'unica eccezione dichiarata:
//    la `fn_check_*` risponde sullo STATO di un documento, mentre qui il verbo
//    non ha OGGETTO — la riga non ne nomina nessuno. È una proprietà della
//    forma della riga, visibile in `gruppo_key`, non una regola di dominio
//    riscritta.
function buildSegnalazioneRowActions(row) {
  if (isReadonly.value) return []
  return [azioneEscludi(
    // Il ramo senza documento è l'eccezione spiegata qui sopra.
    row.gruppo_key
      ? uscitaDalGiro.motivo(row)
      : t('vendite.lotti.segn_escludi_del_giro'),
    {
      gruppo_key: row.gruppo_key,
      // ⭐ La conferma nomina il documento come lo legge una persona
      //    (`ORD0036004`), non la chiave. ⚠️ Il ripiego sulla chiave resta e
      //    non è teorico: `riferimento` è l'ULTIMO gradino di una scala che il
      //    database percorre — numero, codice commessa, chiave — e su un lavoro
      //    che non si risolve più torna proprio lei.
      riferimento: row.riferimento || row.gruppo_key,
      // ⚠️ Il conteggio dei trascinati vive sulla scheda Documenti, non qui:
      //    `null` significa «non lo so», e la conferma non promette un numero
      //    che non ha. ⛔ Non `0`, che direbbe «non trascina nessuno».
      n_trascinati: null,
    },
  )]
}

// ⭐ FE — L'USCITA DI UN DOCUMENTO DAL GIRO (brief-db-uscita-documento-dal-giro).
//
// ⛔ Il motivo è OBBLIGATORIO (D-5) e il pulsante resta spento finché non c'è:
//    un documento che esce senza motivo è una riga che fra un mese nessuno sa
//    spiegare. ⚠️ La regola vera la tiene il database — il `CHECK` rifiuta anche
//    i soli spazi — e questo è il non-proporre, non il cancello.
//
// ⚠️ E LA CONSEGUENZA SI DICHIARA PRIMA. Una bozza può coprire più documenti:
//    togliere A può portare via anche B, che torna «da emettere» e si fattura al
//    giro dopo. Non è un motivo che rifiuta — rifiutare lascerebbe bloccati
//    anche i documenti di un'ALTRA bozza, cioè il sequestro di partenza in forma
//    più stretta — è una conseguenza, e le conseguenze stanno nella conferma.
// ⚠️ La forma chiusa in una FUNZIONE e non in due letterali gemelli: la stessa
//    tupla serve all'inizializzazione e alla chiusura dopo l'atto, e due copie
//    divergono al primo campo aggiunto — con la seconda che lascia in giro il
//    valore vecchio invece di azzerarlo.
const esclusioneChiusa = () => ({
  visible: false, chiavi: [], riferimento: '', trascinati: null,
})
const esclusione = ref(esclusioneChiusa())
const esclusioneMotivo = ref('')

// Scopo: apre la conferma dell'uscita — per UNA riga o per la selezione.
// ⚠️ Una firma sola per i due percorsi: `{chiavi}` dal gesto di massa,
//    `{gruppo_key, …}` da una riga. Due funzioni divergerebbero sul testo della
//    conferma, che è la cosa che l'operatore legge prima di un atto
//    irreversibile.
function apriEsclusione(row) {
  esclusioneMotivo.value = ''
  esclusione.value = {
    visible: true,
    chiavi: row.chiavi ?? [row.gruppo_key],
    // Vuoto sul gesto di massa: lì il soggetto è il numero, non un nome.
    riferimento: row.chiavi ? '' : gruppoRiferimento(row),
    // ⚠️ `?? null` e MAI `?? 0`, e vale per i due percorsi che qui non hanno il
    //    numero — la scheda Critiche, che il conteggio non lo riceve, e il gesto
    //    di MASSA, dove sommare i trascinati riga per riga conterebbe due volte
    //    i documenti che si trascinano a vicenda ed ESSENDO entrambi selezionati
    //    non tornano indietro affatto. `0` direbbe «non trascina nessuno», che
    //    è un'affermazione; `null` dice «non lo so», e la conferma tace invece
    //    di promettere un numero che non ha.
    trascinati: row.n_trascinati ?? null,
  }
}

// Scopo: esegue l'uscita e RACCONTA il consuntivo — quante bozze sono state
//        cancellate e quanti documenti sono tornati in coda. ⛔ Non è
//        decorazione: sono le due conseguenze che l'operatore non si aspetta, e
//        chi non le mostra le nasconde.
async function confermaEsclusione() {
  const chiavi = esclusione.value.chiavi
  const res = await execute(
    () => escludiDocumentiDaGiro(props.lottoId, {
      gruppoKeys: chiavi, motivo: esclusioneMotivo.value,
    }),
  )
  // `!== null` e non `if (res)`: un esito vuoto è comunque un successo.
  if (res === null) return
  esclusione.value = esclusioneChiusa()

  // ⛔ UN 200 NON È UN SUCCESSO: la risposta è un REPORT a tre stati e il
  //    fallimento è un campo del payload — il verbo non produce un atto
  //    fiscale, quindi un esito parziale lascia documenti in coda, non mezzo
  //    documento. Chi legge solo lo status annuncia riuscita un'operazione in
  //    cui quattro righe su cinque sono state rifiutate.
  const falliti = res?.falliti ?? []
  if (falliti.length) {
    // ⭐ SI TENGONO SPUNTATE SOLO LE FALLITE, che sono esattamente ciò su cui
    //    l'operatore deve tornare. ⚠️ E non è cosmetica: le riuscite escono
    //    dall'elenco lavorabile, quindi il prune — che guarda solo ciò che la
    //    pagina dichiara — non le vedrebbe mai: resterebbero spuntate e
    //    invisibili, contate dal pulsante.
    selezioneDocumenti.tieniSolo(falliti.map((f) => f.gruppo_key))
    // ⚠️ Il MOTIVO del primo rifiuto, non un «alcuni non sono passati»: il
    //    codice per riga esiste apposta, e su una selezione omogenea è il
    //    motivo di tutte.
    notify.warn(t('vendite.lotti.gruppo_escludi_parziale', {
      ok: res?.ok ?? 0,
      totale: res?.totale ?? 0,
      motivo: falliti[0]?.messaggio || falliti[0]?.codice || '',
    }))
  } else {
    selezioneDocumenti.azzera()
    notify.success(t('vendite.lotti.gruppo_escludi_esito', {
      n: res?.ok ?? 0,
      // ⚠️ Le bozze si SOMMANO e i documenti NO, e la differenza è di merito:
      //    una bozza la cancella una sola uscita — la seconda che la tocca ne
      //    trova zero — mentre lo STESSO documento può essere nominato
      //    «riaperto» da due uscite diverse della stessa corsa.
      fatture: (res?.usciti ?? []).reduce((tot, u) => tot + (u.fatture_cancellate ?? 0), 0),
      riaperti: contaRiaperti(res?.usciti ?? []).length,
    }))
  }
  // ⚠️ Si ricarica TUTTO e non la sola scheda: l'uscita cambia il riepilogo
  //    delle segnalazioni (il lotto può essere ripartito) e può aver cancellato
  //    una bozza, che è nella scheda accanto.
  await reloadAll()
  emit('changed')
}

// Scopo: ⭐ LA COMMESSA DA CORREGGERE, come bersaglio. Sta in una funzione e non
//        in due espressioni perché le superfici sono DUE — il kebab qui sopra e
//        l'icona d'errore nella cella dell'esito — e scriverla due volte
//        significa dimenticare in un posto il guard su `commessa_id`.
// ⚠️ Elenco vuoto e non `null`: chi la usa la concatena o la passa a
//        `ErroreRigaInfo`, e in entrambi i casi «niente» è la lista vuota.
// ⛔ Il tipo viene dalla mappa dei bersagli, non da una stringa a mano: un tipo
//        che quella mappa non conosce non risolve, e il pulsante semplicemente
//        non compare — senza nessun errore.
function bersaglioCommessa(row) {
  return row.commessa_id
    ? [{ type: BERSAGLIO_TIPI.COMMESSA, id: row.commessa_id }]
    : []
}

// Scopo: ⭐ I DOCUMENTI CHE TORNANO DAVVERO «DA EMETTERE» dopo una corsa di
//        uscite — l'insieme, non la somma dei conteggi per riga.
//
// 🔴 Sommare `n_gruppi_riaperti` mente in due modi, ed è il difetto che questa
//    funzione chiude. Due documenti che condividono una bozza si nominano A
//    VICENDA come trascinati: togliendoli ENTRAMBI nella stessa corsa la somma
//    dice «2 documenti tornati da emettere» mentre in coda non ne torna
//    NESSUNO — sono usciti tutti e due. E lo stesso terzo documento trascinato
//    da due uscite diverse verrebbe contato due volte.
// ⚠️ Nessun errore, solo un numero più grande del vero in un messaggio che
//    l'operatore usa per decidere se il mese è a posto.
//
// ⭐ È ANCHE LA RAGIONE PER CUI IL BACKEND MANDA LE CHIAVI e non solo il
//    conteggio: un numero da solo non si può né deduplicare né sottrarre. Le
//    chiavi arrivano perché la conferma possa NOMINARE i trascinati; questo è
//    il secondo consumatore della stessa scelta.
function contaRiaperti(usciti) {
  const usciteDelGiro = new Set(usciti.map((u) => u.gruppo_escluso))
  const riaperti = new Set()
  usciti.forEach((u) => (u.gruppi_riaperti ?? []).forEach((chiave) => {
    // Chi è uscito lui stesso non «torna da emettere»: è fuori dal giro.
    if (!usciteDelGiro.has(chiave)) riaperti.add(chiave)
  }))
  return [...riaperti]
}

// Scopo: chi ha tolto il documento dal giro, quando e perché — in una riga.
// ⚠️ Il motivo c'è SEMPRE su una riga `ESCLUSO` (lo impone un `CHECK`), quindi
//    non serve un ripiego per «uscito senza motivo»: non esiste. Il ripiego
//    serve sul TIMBRO, che lo scrive un trigger e non il chiamante.
function uscitaTooltip(row) {
  return t('vendite.lotti.gruppo_uscita_tooltip', {
    motivo: row.uscita_motivo || '—',
    chi: row.uscita_da || '—',
    quando: row.uscita_quando ? displayTimestamp(row.uscita_quando) : '—',
  })
}

// Scopo: il nome del documento preso in carico. ⚠️ Il ripiego è la CHIAVE del
//        gruppo e non un trattino: quando l'identità non si risolve più — il
//        lavoro è finito in un altro giro, o è uscito dal mese — la riga resta
//        in elenco col suo esito, ed è proprio quella per cui questa scheda
//        esiste. Una riga senza nome è comunque meglio di una riga assente.
function gruppoRiferimento(row) {
  return row.riferimento || row.gruppo_key
}

// ⛔ Niente composizione locale: il numero documento viene dalla sede unica
// (`vendite.fn_numero_documento_fattura`, 20260829-15). Qui si scriveva
// `serie numero`, nel drawer fattura `serie numero/anno`: due schermate, due
// documenti scritti in due modi. Il ripiego del non-numerato resta di chi rende.
function fatturaNumero(row) {
  return row.numero_documento || '—'
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotoEsclusione = useFotografiaDialog(() => ({ motivo: esclusioneMotivo.value }), { visibile: () => esclusione.value.visible })
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('vendite.lotti.drawer_titolo')"
    :icon="MANAGE_ICONS.LOTTO"
    :width="DRAWER_WIDTH.WIDE"
    :proteggi-corpo="false"
    :readonly="isReadonly"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <template v-if="lotto">
      <DrawerEntityHeader>
        <Tag :value="lotto.codice" severity="secondary" />
        <span class="app-text-muted">{{ lotto.tipo_lotto }}</span>
        <span v-if="lotto.competenza_mese" class="app-text-muted">
          {{ displayDate(lotto.competenza_mese) }}
        </span>
        <template #status>
          <Tag :value="lotto.stato_lotto" :severity="statoLottoSeverity(lotto.stato_lotto)" />
        </template>
      </DrawerEntityHeader>

      <!-- Step corrente (stato doc fiscale del lotto). -->
      <div class="app-lotto-step">
        <span class="app-text-muted">{{ t('vendite.lotti.step_corrente') }}:</span>
        <Tag :value="lotto.stato_doc_fiscale_descrizione ?? '—'" severity="info" />
        <span v-if="lotto.stato_operativo" class="app-text-muted">· {{ lotto.stato_operativo }}</span>
      </div>

      <!-- Banner del lotto FERMO (blocca l'avanzamento). Compare sul VERDETTO
           del backend, non su un conteggio: dal 2026-09-12 un lotto puo' essere
           fermo con zero critiche vive (esiti in errore, D2). -->
      <!-- ⚠️ Il ROSSO solo dove c'e' qualcosa da fare: su un lotto congelato
           le critiche sono storia, e un allarme rosso su un giro chiuso
           insegna a ignorare gli allarmi rossi. -->
      <Message
        v-if="lottoFermo"
        :severity="giroRimediabile ? 'error' : 'secondary'"
        :closable="false"
        class="app-mt-1"
      >
        {{ fraseBanner }}
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
        :info-key="capabilities.stato_info_key || ''"
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
          <Tab :value="LOTTO_SCHEDE.DOCUMENTI">{{ t('vendite.lotti.tab_documenti') }} ({{ listaDocumenti.totale.value }})</Tab>
          <!-- ⭐ I documenti PRESI IN CARICO — quelli che una fattura non sono
               mai diventati compresi. Il conteggio è quello del server, come
               sulle altre schede: dal 2026-09-07 vale su entrambi i tipi di
               giro, quindi non ha più bisogno di essere condizionato. -->
          <Tab :value="LOTTO_SCHEDE.PRESI_IN_CARICO">{{ t('vendite.lotti.tab_gruppi') }} ({{ listaGruppi.totale.value }})</Tab>
          <Tab :value="LOTTO_SCHEDE.TASK">{{ t('vendite.lotti.tab_task') }} ({{ listaTask.totale.value }})</Tab>
          <Tab :value="LOTTO_SCHEDE.SEGNALAZIONI">{{ t('vendite.lotti.tab_segnalazioni') }}</Tab>
          <!-- ⭐ La quarta scheda risponde a una domanda che le altre tre non
               fanno: le prime dicono COSA C'E' ORA, questa COSA E' SUCCESSO.
               Il conteggio nell'etichetta dice se vale la pena entrare. -->
          <Tab :value="LOTTO_SCHEDE.STORIA">
            {{ t('vendite.lotti.tab_storia') }}
            <template v-if="giornaleStore.totalRecords"> ({{ giornaleStore.totalRecords }})</template>
          </Tab>
        </TabList>
        <TabPanels>
          <!-- ⭐ I TRE TAB SONO TRE LISTE CONFIGURABILI (seed 45/46/47, FE-2
               del brief liste drawer lotto). Le colonne arrivano dal
               catalogo: qui restano solo gli slot delle celle che hanno una
               resa propria (Tag, icona errore, kebab). Aggiungere una
               colonna e' ora un seed, non una riga di `.vue`. -->
          <TabPanel :value="LOTTO_SCHEDE.DOCUMENTI">
            <!-- ⭐ Contenitore STANDARD delle liste: filtri a sinistra, azioni a
                 destra. Non un allineamento scritto a mano — `app-page-toolbar` e' lo
                 stesso di ogni pagina lista.
                 ⚠️ Sul piccolo schermo le icone collassano nel kebab da se':
                 `PageActionsBar` lo fa al breakpoint, non serve nulla qui. -->
            <div class="app-page-toolbar">
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
              <!-- ⚠️ Il seed dichiara la colonna `numero`, ma a video ci va il
                   NUMERO DOCUMENTO (`numero - serie`) che arriva gia' composto
                   dal backend: qui il FE non compone piu' niente. I due nomi
                   restano diversi di proposito — `numero` e' il campo su cui
                   si ORDINA, il numero documento e' quello che si LEGGE. -->
              <template #cell-numero="{ data }">{{ fatturaNumero(data) }}</template>
              <!-- ⚠️ La natura NON ha slot: il seed dichiara `formato = natura_doc`
                   e `CellaConfigurabile` la rende con `NaturaDocTag` (dal 18/09,
                   come `yesno`). La nota di credito non e' un'anomalia: severity
                   neutra, mai `danger` — e il totale negativo si mostra com'e',
                   perche' e' il documento a essere di segno opposto. -->
              <template #cell-stato_doc_fiscale_descrizione="{ data }">
                <Tag :value="data.stato_doc_fiscale_descrizione ?? '—'" severity="info" />
              </template>
              <template #cell-stato_esecuzione="{ data }">
                <span class="app-lotto-esecuzione-cella">
                  <Tag :value="data.stato_esecuzione" :severity="statoEsecuzioneLottoSeverity(data.stato_esecuzione)" />
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
                   Il kebab sotto spazio stretto arriva da se'
                   (`CellaAzioniRiga`): lo scope `compact` non va girato. -->
              <template #actions="{ data }">
                <RowActionsMenu :row="data" :actions="buildFatturaActions(data)" />
              </template>
              <!-- Empty-state TRADOTTO: senza lo slot il BB lascia il default
                   PrimeVue, che e' in inglese. -->
              <template #empty>
                <div class="app-empty-state"><i :class="STATUS_ICONS.VUOTO" /><p>{{ t('vendite.lotti.nessuna_fattura') }}</p></div>
              </template>
            </ListaConfigurabile>
          </TabPanel>

          <TabPanel :value="LOTTO_SCHEDE.PRESI_IN_CARICO">
            <div class="app-page-toolbar">
              <PageActionsBar :actions="barraGruppi">
                <template #suffix>
                  <ListaConfigStatusTag :dirty="azioniGruppi.dirty.value" />
                </template>
              </PageActionsBar>
            </div>
            <ListaConfigurabile
              ref="listaGruppiRef"
              codice="vendite.lotto_gruppi"
              data-key="gruppo_key"
              :selezione="selezioneDocumenti.perLista.value"
              :rows="listaGruppi.righe.value"
              :total="listaGruppi.totale.value"
              :loading="tabLoading || listaGruppi.loading.value"
              :paginator-options="listaGruppi.paginatorOptions.value"
              :page="listaGruppi.page.value"
              :sort-field="listaGruppi.sortField.value"
              :sort-order="listaGruppi.sortOrder.value"
              @page="listaGruppi.onPage"
              @sort="listaGruppi.onSort"
              @config-loaded="listaGruppi.onConfigLoaded"
            >
              <!-- ⚠️ Il ripiego è la CHIAVE del gruppo, non un trattino: una
                   riga che ha perso l'identità ha comunque un esito da
                   raccontare, ed è quella per cui la scheda esiste. -->
              <template #cell-riferimento="{ data }">
                <strong>{{ gruppoRiferimento(data) }}</strong>
              </template>
              <template #cell-tipo_gruppo="{ data }">
                <Tag v-if="data.tipo_gruppo" :value="data.tipo_gruppo" severity="secondary" />
                <span v-else>—</span>
              </template>
              <!-- ⚠️ Vuota quando il documento alimenta PIÙ commesse
                   (`commesse_n > 1`): non è «non lo so», è «sono più di una»,
                   e le due cose si scrivono diverse — stessa forma con cui
                   questa applicazione tratta già il sezionale multiplo. -->
              <template #cell-commessa_codice="{ data }">
                <span v-if="data.commessa_codice">{{ data.commessa_codice }}</span>
                <span
                  v-else-if="data.commesse_n > 1"
                  v-tooltip.bottom="t('vendite.lotti.gruppo_commesse_multi_tooltip')"
                >
                  <i :class="STATUS_ICONS.MULTIPLI" />
                  {{ t('vendite.lotti.gruppo_commesse_multi', { n: data.commesse_n }) }}
                </span>
                <span v-else>—</span>
              </template>
              <!-- ⭐ Il CHE COSA e il PERCHÉ nella stessa cella, come sulla
                   scheda «Documenti»: il tag dice com'è andata, l'icona apre
                   il motivo per intero e porta alla commessa da correggere.
                   ⚠️ Vuoto = MAI TENTATO in questo lotto, e non è «andata
                   bene»: si scrive «—», che è l'assenza, non un `PENDING`
                   inventato qui. -->
              <template #cell-stato_esecuzione="{ data }">
                <span class="app-lotto-esecuzione-cella">
                  <Tag
                    v-if="data.stato_esecuzione"
                    :value="data.stato_esecuzione"
                    :severity="statoEsecuzioneLottoSeverity(data.stato_esecuzione)"
                  />
                  <span v-else>—</span>
                  <ErroreRigaInfo
                    v-if="data.stato_esecuzione === STATO_ESECUZIONE_LOTTO.ERRORE"
                    :messaggio="data.errore_messaggio"
                    :codice="data.errore_codice"
                    :quando="data.errore_quando"
                    :bersagli="bersaglioCommessa(data)"
                    :titolo="t('vendite.lotti.gruppo_errore_titolo')"
                  />
                  <!-- ⭐ CHI L'HA TOLTO E PERCHÉ. Il motivo è obbligatorio
                       (D-5) proprio perché fra un mese qualcuno chiederà come
                       mai quel documento non è in quella fattura: senza il
                       nome e la data, «ESCLUSO» è un tag che non risponde.
                       ⚠️ Il timbro lo scrive un trigger dalla GUC, non il
                       chiamante — e non riusa `data_update`/`user_update`,
                       che qualunque aggiornamento successivo riscriverebbe. -->
                  <i
                    v-if="data.stato_esecuzione === STATO_ESECUZIONE_LOTTO.ESCLUSO"
                    v-tooltip.bottom="uscitaTooltip(data)"
                    :class="STATUS_ICONS.INFO"
                  />
                </span>
              </template>
              <!-- ⛔ `actions`, non `cell-azioni`: col nome sbagliato la
                   colonna non viene resa affatto e non fallisce niente. -->
              <template #actions="{ data }">
                <RowActionsMenu :row="data" :actions="buildGruppoRowActions(data)" />
              </template>
              <!-- ⚠️ Empty-state ONESTO, e la frase è cambiata col modello:
                   zero righe non vuol più dire «giro di massa, qui non si può
                   sapere» — vuol dire che di questo lotto non risulta nessun
                   documento. Vero sia per un lotto che non ha ancora
                   lavorato, sia per uno anteriore al tracciamento: non si
                   afferma che non abbia fatto niente, e si dice dove
                   guardare. -->
              <template #empty>
                <div class="app-empty-state">
                  <i :class="STATUS_ICONS.VUOTO" />
                  <p>{{ t('vendite.lotti.nessun_gruppo') }}</p>
                </div>
              </template>
            </ListaConfigurabile>
          </TabPanel>

          <TabPanel :value="LOTTO_SCHEDE.TASK">
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
              <!-- ⚠️ `:segno` e non `:store`: queste sotto-liste del lotto non
                   hanno uno store-lista — i loro filtri sono ref di questo
                   drawer. E' il ripiego dichiarato dal brief. -->
              <FiltriLista :segno="segnoAmpiezzaTask" @pulisci="azzeraAmpiezzaTask">
                <!-- Filtro di AMPIEZZA, a sinistra come i filtri di ogni
                     lista. Non è il gemello del filtro gravità delle
                     segnalazioni: là si sceglie un livello, qui quanto si
                     guarda. -->
                <SelectButton
                  class="app-filtro-largo"
                  v-model="ampiezzaTask"
                  :options="opzioniAmpiezzaTask"
                  option-label="label"
                  option-value="value"
                  :allow-empty="false"
                  size="small"
                />
              </FiltriLista>
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
                <div class="app-empty-state"><i :class="STATUS_ICONS.VUOTO" /><p>{{ t('vendite.lotti.nessun_task') }}</p></div>
              </template>
            </ListaConfigurabile>
          </TabPanel>

          <TabPanel :value="LOTTO_SCHEDE.SEGNALAZIONI">
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
                <FiltriLista :segno="segnoLivelloSegnalazioni" @pulisci="azzeraLivelloSegnalazioni">
                  <!-- Filtro per livello, a sinistra come i filtri di ogni
                       lista. Il CONTEGGIO sta nell'etichetta: dice se vale la
                       pena guardare quel livello. -->
                  <SelectButtonGravita
                    class="app-filtro-largo"
                    v-model="livelloSegnalazioni"
                    :options="opzioniLivello"
                  />
                </FiltriLista>
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
                  <span v-else class="app-text-muted">{{ data.fase || t('vendite.lotti.segn_origine_lotto') }}</span>
                </template>
                <!-- ⭐ DI CHI E' LA CRITICA — la colonna che divide la scheda
                     in DUE FAMIGLIE con vie d'uscita diverse: quella di un
                     documento si toglie dal giro, quella del GIRO si corregge
                     e basta. Prima erano indistinguibili, ed è la ragione per
                     cui l'unica proposta a video era «annulla tutto».
                     ⚠️ Il vuoto si SCRIVE, non si lascia in bianco: «è del
                     giro» è un'informazione, non un dato mancante.
                     ⭐ Si legge il RIFERIMENTO e non la chiave (2026-09-08):
                     `ORD0036004` invece di `ORDINE_VENDITA:<uuid>`. I due non
                     sono in concorrenza — servono a destinatari diversi: la
                     chiave la vuole il PULSANTE e continua a viaggiare in
                     riga, il riferimento è per la persona ed è l'unico dei
                     due che si vede (la colonna della chiave è spenta a
                     catalogo, D-7).
                     ⚠️ Nessun ripiego sulla chiave qui: la scala di ripiego
                     la fa già il database — numero del documento, codice
                     commessa, chiave grezza — e rifarla qui sarebbe la terza
                     sede della stessa regola. -->
                <template #cell-riferimento="{ data }">
                  <span v-if="data.riferimento">{{ data.riferimento }}</span>
                  <span v-else class="app-text-muted">
                    {{ t('vendite.lotti.segn_del_giro') }}
                  </span>
                </template>
                <!-- ⛔ `actions`, non `cell-azioni`: col nome sbagliato la
                     colonna non viene resa affatto e non fallisce niente. -->
                <template #actions="{ data }">
                  <RowActionsMenu
                    :row="data"
                    :actions="buildSegnalazioneRowActions(data)"
                  />
                </template>
                <template #empty>
                  <div class="app-empty-state">
                    <i :class="STATUS_ICONS.TUTTO_OK" />
                    <p>{{ t('vendite.lotti.nessuna_segnalazione_livello') }}</p>
                  </div>
                </template>
              </ListaConfigurabile>
            </div>
            <div v-else class="app-empty-state"><i :class="STATUS_ICONS.TUTTO_OK" /><p>{{ t('vendite.lotti.nessuna_segnalazione') }}</p></div>
          </TabPanel>
          <TabPanel :value="LOTTO_SCHEDE.STORIA">
            <!-- ⭐ LA STORIA DEL LOTTO — «cosa è successo, in che ordine».
                 La lista a catalogo `vendite.giornale` sul lotto PIÙ le sue
                 fatture (sorgente `script.vw_giornale_entita`: sul lotto
                 rispondono `EVENT_LOG`, `LOTTO_LOG`, `TASK_RUN`, più
                 `FATTURA_LOG` per i documenti che contiene).
                 ⭐ Le righe della FATTURA ci sono di proposito: il lotto
                 ripete «Esito fatture lotto · WARN» e il motivo sta sul
                 documento, perché la sua entità è la fattura — ed è per
                 questo che le colonne Entità/Riferimento servono.
                 ⛔ Non è la scheda «Segnalazioni»: quella elenca i problemi
                 APERTI da risolvere, qui c'è anche ciò che è andato bene. -->
            <GiornaleEntitaTab
              :store="giornaleStore"
              :entita-id="lottoId"
              :emittente-soggetto-ruolo-id="lotto.emittente_soggetto_ruolo_id"
            />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </template>

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

  <!-- Archivio documenti generati della fattura selezionata (sorgente FATTURA).
       L'emittente e' quello del LOTTO: una fattura del lotto e' dell'emittente
       del lotto. La PK (`emittente_fiscale_id`), non il soggetto-ruolo: e' il
       lasciapassare del cancello di perimetro, senza il quale il super admin
       su «Tutti» vedrebbe il pannello di scelta dentro il dialog. -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialogVisible"
      :sorgente-code="SORGENTE_CODES.FATTURA"
      :sorgente-id="pdfFatturaId"
      :emittente-fiscale-id="lotto?.emittente_fiscale_id ?? null"
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
      :azione="confermaNumera"
    />

    <!-- ⭐ USCITA DI UN DOCUMENTO DAL GIRO. Non è un «sei sicuro?»: chiede il
         MOTIVO, che è obbligatorio, e DICHIARA la conseguenza quando la bozza
         è condivisa. ⚠️ `save-severity="danger"`: l'uscita è a senso unico —
         per rimettere tutto in un lotto solo si annulla il lotto e si rigenera.
         ⚠️ `readonly: false` esplicito: il drawer del lotto è locked-by-stato,
         e senza questo `FormFooter` erediterebbe readonly e nasconderebbe la
         conferma di un'azione che su quello stato è legittima. -->
    <AppDialog
      :conferma-uscita="fotoEsclusione.chiudiConConferma"
      v-model:visible="esclusione.visible"
      :header="t('vendite.lotti.gruppo_escludi_header')"
      width="md"
      :loading="loading"
      :readonly="false"
      :save-disabled="!esclusioneMotivo.trim() || !esclusione.chiavi.length || loading"
      :save-label="t('vendite.lotti.gruppo_escludi_conferma')"
      save-severity="danger"
      @save="confermaEsclusione"
    >
      <!-- Il soggetto è il documento quando è uno, il NUMERO quando sono tanti:
           «I 3 documenti selezionati escono…» dice cosa sta per succedere
           meglio di un elenco di chiavi lungo tre righe. -->
      <p v-if="esclusione.riferimento">
        {{ t('vendite.lotti.gruppo_escludi_testo', { documento: esclusione.riferimento }) }}
      </p>
      <p v-else>
        {{ t('vendite.lotti.gruppo_escludi_testo_n', { n: esclusione.chiavi.length }) }}
      </p>
      <!-- ⚠️ L'AVVISO C'È SOLO QUANDO TRASCINA, e nomina il numero: dirlo
           sempre lo renderebbe rumore, e chi legge un avviso perpetuo smette
           di leggerlo. I documenti trascinati NON escono — tornano «da
           emettere» e si fatturano al giro dopo: rimandati, non distrutti. -->
      <Message
        v-if="esclusione.trascinati > 0"
        severity="warn"
        :closable="false"
        size="small"
      >
        {{ t('vendite.lotti.gruppo_escludi_trascina', { n: esclusione.trascinati }) }}
      </Message>
      <div class="form-field">
        <label for="esclusione-motivo">{{ t('vendite.lotti.gruppo_escludi_motivo') }}</label>
        <Textarea
          id="esclusione-motivo"
          v-model="esclusioneMotivo"
          rows="3"
          auto-resize
          :placeholder="t('vendite.lotti.gruppo_escludi_motivo_placeholder')"
        />
      </div>
    </AppDialog>
  </AppDrawer>
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
/* Stacco fra il banner «questo lotto non dichiara un perimetro» e ciò che
   segue. ⚠️ Locale come `.app-mt-1` qui sopra: le spaziature globali di
   `main.css` sono `mt-025`/`mt-05`/`mt-1`, senza gemelle in basso. */
.app-mb-1 {
  margin-bottom: 1rem;
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
