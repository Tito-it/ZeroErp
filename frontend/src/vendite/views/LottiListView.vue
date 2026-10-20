<script setup>
// Scopo: Registro dei giri di fatturazione (cockpit Fase B, B-2). Lista dei
//        lotti con filtri competenza/stato, scope emittente applicato dal BE
//        (RLS + get_scope_user_id). Non è il percorso quotidiano: serve per le
//        eccezioni (errori, reset, recuperi) e per il gate fiscale. Il click
//        apre il LottoDrawer diagnostico (step corrente, fatture, task-run,
//        segnalazioni) con le azioni di governo. Nessuna logica di dominio:
//        stato/step/gate vivono nel motore, la lista rende e naviga.
import { ref, computed, nextTick, onActivated, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { registraDrawerChiudibile } from '../../core/composables/useDrawerChiusuraGlobale'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import DashMesiSidebar from '../../core/components/dash/DashMesiSidebar.vue'
import DashMeseStepper from '../../core/components/dash/DashMeseStepper.vue'
import LottiLista from '../components/LottiLista.vue'
import LottoDrawer from '../components/LottoDrawer.vue'
import NumerazioneDataDialog from '../components/NumerazioneDataDialog.vue'
import FatturazioneEsitiPanel from '../components/FatturazioneEsitiPanel.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useNotify } from '../../core/composables/useNotify'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useListaDrawerPaginata } from '../../core/composables/useListaDrawerPaginata'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Message from 'primevue/message'
import { useLottoAzioni } from '../composables/useLottoAzioni'
import { useSelezioneLotti } from '../composables/useSelezioneLotti'
import { useJobPolling } from '../../core/composables/useJobPolling'
import { useRigheInGiro } from '../../core/composables/useRigheInGiro'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { runNumerazione, getFatturazioneRun } from '../api/lotti'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import { useDashMesiNav } from '../../core/composables/useDashMesiNav'
import { extractApiError } from '../../core/utils/apiError'
import { MANAGE_ICONS, READONLY_DOMAINS, STATUS_ICONS } from '../../core/constants'
import { menuItemClass } from '../../core/utils/rowActions'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { exportLotti, listLotti, listLottiMensile } from '../api/lotti'
import { paramsPerimetro, useLottiStore } from '../stores/lotti'
import { paramsOrdinamento } from '../../core/utils/listParams'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { oggiAziendale, parseIsoDate } from '../../core/utils/date'

const { t, te } = useI18n()
const notify = useNotify()
// Servono al deep-link `?open=<id>` (vedi `applicaDeepLink` piu' sotto).
const route = useRoute()
const router = useRouter()
// Il valore serve anche qui, non solo ai figli: in sola lettura il kebab di
// riga non propone azioni di governo (il BE resta il guard vero).
const { isReadonly } = useReadonlyMode(READONLY_DOMAINS.VENDITE)
const store = useLottiStore()

// Filtro stato lotto (select statico sui valori di dominio; una nuova voce si
// mostra comunque via fail-visible).
const statoFilter = ref(null)
// ⛔ IL VERSO STORE → WIDGET, che fino al 2026-09-23 mancava. Questo `ref` e'
//    la sede condivisa dei DUE comandi (i pulsanti di stato e la tendina) e la
//    spinta verso lo store la fa `syncFiltri()`; ma quando il filtro lo cambia
//    QUALCUN ALTRO — il «Pulisci filtri» del drawer compatto — nessuno
//    riportava indietro il valore: la lista tornava a tutti gli stati e la
//    tendina continuava a mostrare quello di prima. Nessun errore.
// ⚠️ Qui non si usa `bindSelect` e non e' una dimenticanza: il suo `onChange`
//    scriverebbe subito nello store, e `syncFiltri()` decide il reset a pagina 1
//    proprio CONFRONTANDO ref e store — con un binder i due sarebbero sempre
//    uguali e l'offset non si azzererebbe mai.
watch(() => store.filters.stato_lotto, (v) => { statoFilter.value = v ?? null })

// Navigazione anno/mese — stesso telaio della Lente Competenza (BB condiviso
// useDashMesiNav + DashMesiSidebar): anno in alto, 12 mesi sotto. C'è SEMPRE un
// mese selezionato (niente "tutti i mesi": lo storico si naviga con le frecce
// anno). Default = mese corrente, la competenza che si sta fatturando.
// Il mese corrente e' quello dell'AZIENDA, non del PC.
const oggi = oggiAziendale()
const anno = ref(oggi.getFullYear())
const meseIdx = ref(oggi.getMonth())

// `onMeseChange`/`onAnnoChange` sono dichiarazioni di funzione (hoisted): il
// telaio le riceve qui ma le invoca solo su interazione.
const { nomiMesi, competenzaCorrente, selezionaMese, cambiaAnno, stepMese } = useDashMesiNav({
  anno,
  meseIdx,
  onMeseChange: onFilterChange,
  onAnnoChange: loadMensile,
})

// Competenza in formato API (YYYY-MM-01): è già la forma di competenzaCorrente,
// condivisa da lista ed esiti (unica derivazione, non possono divergere).
const competenzaParam = computed(() => competenzaCorrente.value)

// Conteggi lotti/mese dell'anno per il badge della sidebar: mappa
// competenza→n. I 12 mesi sono SEMPRE presenti (0-riempiti) e reattivi
// all'anno, così la sidebar non "lampeggia" vuota prima della fetch.
const conteggiMese = ref({})
const mesi = computed(() =>
  Array.from({ length: 12 }, (_, m) => {
    const cm = `${anno.value}-${String(m + 1).padStart(2, '0')}-01`
    return { competenza_mese: cm, n_lotti: conteggiMese.value[cm] ?? 0 }
  })
)

const statoOptions = computed(() => [
  { value: 'DRAFT', label: t('vendite.lotti.stato_draft') },
  { value: 'IN_ESECUZIONE', label: t('vendite.lotti.stato_in_esecuzione') },
  { value: 'COMPLETATO', label: t('vendite.lotti.stato_completato') },
  { value: 'ERRORE', label: t('vendite.lotti.stato_errore') },
])

// Scaffolding della lista configurabile (useSearchTable + export + pageActions).
// L'export riceve gli STESSI filtri della lista: il file rispecchia ciò che si
// sta guardando, ordinamento incluso.
const {
  onPage, onSort, paginatorProps, tablePage, reload,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions,
  perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportLotti,
  getExportParams: (fmt) => ({
    // Il file E' la lista: stesso perimetro (mese, stato, annullati — e
    // l'intestazione del file lo dichiara), stesso ordine.
    // ⚠️ Ripiego `asc` come la FETCH dello store (`lotti.js`, `paramsPagina`
    //    con `orderDirDefault: 'asc'`): fino al 2026-09-18 qui era `desc`,
    //    cioe' lista ed export avrebbero letto due versi diversi il giorno in
    //    cui quel ramo si fosse acceso — l'unica delle dodici copie divergente
    //    dalla propria lista, trovata estraendo `paramsOrdinamento`.
    formato: fmt,
    ...paramsPerimetro(store.filters),
    ...paramsOrdinamento(store.filters, { orderDirDefault: 'asc' }),
  }),
})

// ⭐ LA SCHEDA «RECUPERI DEL MESE»: i lotti di competenza PRECEDENTE che hanno
//    emesso documenti nel mese filtrato. Non passa dallo store — è una seconda
//    domanda sulla stessa lista, non un secondo stato della pagina.
// ⚠️ `useListaDrawerPaginata` e non `useListaConfigurabilePage`: quest'ultimo
//    pretende uno store con la forma «ricerca + sort + limit», e qui lo store
//    non c'è. È lo stesso caso per cui quel BB è nato (una lista pilotata da un
//    contesto esterno) — il nome dice «drawer» solo perché lì è stato estratto.
const schedaAttiva = ref('lotti')

// ⭐ Cambiando PERIODO si torna sempre ai «Lotti del mese» (rilievo di Tid,
//    2026-08-27). I «Recuperi» sono la vista di eccezione — i lotti di
//    competenza precedente che hanno emesso documenti nel mese filtrato — e
//    restarci dentro cambiando mese è la strada per credere che il mese nuovo
//    abbia quelle poche righe lì, e non i suoi lotti.
// ⚠️ NON basta il reset in `onActivated`: quello copre l'apertura della pagina
//    e il rientro nel tab, ma un cambio mese non smonta né riattiva niente —
//    cambia un filtro e basta. Erano due strade diverse per lo stesso stato, e
//    la prima correzione ne aveva coperta una sola.
// ⚠️ Si osserva `competenzaParam` e non l'handler del mese: così vale per ogni
//    modo di cambiare periodo — il click sul mese, le frecce, il cambio anno —
//    senza doverli rincorrere uno per uno.
watch(competenzaParam, () => { schedaAttiva.value = 'lotti' })

// Scopo: inoltra a `listaRef` l'istanza di `<ListaConfigurabile>` che
//        `<LottiLista>` espone, invece del wrapper.
// 🔴 Difetto pagato il 2026-08-24: con `ref="listaRef"` sul componente estratto
//    il ref puntava al WRAPPER, e `useListaConfigurabilePage` calcola
//    `configReady` come `lista.value?.config != null` — che sul wrapper è
//    sempre `null`. Effetto: «Personalizza colonne» **disabilitato**, senza
//    nessun errore da nessuna parte. È lo stesso tipo di difetto del nome di
//    slot sbagliato: tutto corretto tranne dove punta un riferimento.
// ⚠️ Si ascolta l'ANNUNCIO del figlio (`@lista-pronta`) e non si LEGGE un ref:
//    leggere significa leggere UNA volta sola, e un `null` in quell'istante
//    resterebbe tale per sempre — con l'unico sintomo di un pulsante
//    disabilitato. L'annuncio arriva dall'`onMounted` del figlio, quando la
//    lista e' certamente montata: nessuna ipotesi sull'ordine.
function registraLista(istanza) {
  listaRef.value = istanza ?? null
}
// Stesso meccanismo della scheda sopra, e per la stessa ragione: un solo modo
// di consegnare l'istanza, nessun caso che si affidi a un accesso tracciato
// attraverso il proxy di `defineExpose`.
const listaRecuperiRef = ref(null)
function registraListaRecuperi(istanza) {
  listaRecuperiRef.value = istanza ?? null
}
// Ripartizione per stato della SECONDA scheda. I recuperi sono un perimetro
// diverso (competenza precedente + documenti emessi nel mese), quindi hanno il
// loro breakdown: i pulsanti devono contare la lista che sta sotto, non l'altra.
const statiRecuperi = ref([])
// Quanti annullati la scheda «Recuperi» sta nascondendo (stesso campo della
// lista principale, dalla propria risposta).
const annullatiRecuperi = ref(0)

// ⚠️ Qui la cattura sta NELLA promise, al contrario dello store — e non e' una
//    disattenzione: `useListaDrawerPaginata` non ha il guard di versione, e
//    scrive `righe`/`totale` subito dopo questo `await`. Conteggi e righe
//    atterrano quindi nella stessa finestra e nello stesso ordine, anche con
//    due chiamate in volo: non c'e' nessuna risposta «scartata» da cui
//    disallinearsi. E' il motivo per cui la lista principale, che quel guard ce
//    l'ha, deve invece passare da `onPayload`.
const listaRecuperi = useListaDrawerPaginata(async ({ page, pageSize, sortBy, sortDir }) => {
  const res = await listLotti({
    // ⚠️ TUTTO il perimetro della pagina, non solo il mese: la scheda si
    // ricarica al cambio filtro, e senza `stato_lotto` si ricaricherebbe
    // IDENTICA — un filtro che si muove sopra una lista che non cambia si
    // legge come un filtro rotto (rilievo di Tid, 2026-08-24). I filtri di
    // pagina valgono per entrambe le schede, e stanno in una sede sola.
    ...paramsPerimetro(store.filters),
    recuperi_mese: true,
    page,
    page_size: pageSize,
    ...(sortBy ? { order_by: sortBy, order_dir: sortDir } : {}),
  })
  statiRecuperi.value = res.data?.data?.stati ?? []
  annullatiRecuperi.value = res.data?.data?.annullati_count ?? 0
  return res
})

// ── I PULSANTI-FILTRO PER STATO ──────────────────────────────────────────
//
// ⭐ Stesso gesto dei chip per area della Lente Backlog: etichetta + conteggio,
//    click = filtro, e SOLO gli stati sopra zero (decisione di Tid, 2026-08-17:
//    un elenco in cui meta' delle voci dicono zero e' rumore, non informazione).
//    L'operatore vede la ripartizione del mese PRIMA di filtrare, che e' la
//    domanda che si fa aprendo la pagina — con la sola tendina la doveva
//    scoprire provando uno stato per volta.
//
// ⭐ I chip cambiano con la SCHEDA, perche' le due schede sono due perimetri
//    diversi: «Lotti del mese» e «Recuperi del mese» non contengono gli stessi
//    lotti, e un pulsante che dicesse «5 Bozza» sopra una lista che ne ha 2
//    sarebbe peggio di nessun pulsante. Il conteggio lo produce il BE dallo
//    stesso costruttore di `WHERE` della lista, quindi la seconda scheda l'ha
//    senza lavoro in piu'.
//
// ⚠️ Il vocabolario e' del DATABASE ed e' aperto: `labelOrCode` e non `t()`
//    secco, cosi' uno stato nuovo compare col suo codice grezzo invece di
//    sparire. La tendina qui sotto elenca i quattro stati noti — e resta il
//    modo per filtrare uno stato oggi a zero, che per costruzione non ha chip.
const chipStati = computed(() => {
  const sorgente = schedaAttiva.value === 'recuperi' ? statiRecuperi.value : store.stati
  return (sorgente ?? [])
    .filter((s) => (s.n_lotti ?? 0) > 0)
    .map((s) => ({
      stato: s.stato_lotto,
      label: labelOrCode(
        t, te, `vendite.lotti.stato_${String(s.stato_lotto).toLowerCase()}`, s.stato_lotto,
      ),
      n: s.n_lotti,
    }))
})

// Scopo: click su un pulsante di stato = filtro, sullo STESSO ref della tendina
//        (`statoFilter`): due comandi, una sola verita'.
// ⭐ Ri-cliccare lo stato gia' attivo lo azzera, come sui chip del Backlog: qui
//    il toggle-off e' legittimo perche' i pulsanti non hanno un «Tutti» e senza
//    di esso per tornare a tutti gli stati si dovrebbe passare per la tendina.
//    E' la stessa regola per cui il toggle e' stato invece TOLTO dalle card
//    della Lente Competenza, che un ritorno esplicito ce l'hanno: un toggle-off
//    si tiene solo dove non c'e' altra via indietro.
function selezionaStato(stato) {
  statoFilter.value = statoFilter.value === stato ? null : stato
  onFilterChange()
}

// Personalizza colonne + esporta anche sulla seconda scheda: è una lista come
// le altre. ⚠️ `?.lista`: `useListaAzioni` vuole l'istanza di
// `<ListaConfigurabile>`, che `<LottiLista>` espone.
const azioniRecuperi = useListaAzioni(() => listaRecuperiRef.value, {
  exportFn: exportLotti,
  getExportParams: (fmt) => ({
    formato: fmt,
    // Il file È la lista, quindi porta TUTTO il perimetro della pagina piu'
    // la scheda: senza `recuperi_mese` esporterebbe i lotti del mese, senza
    // `stato_lotto` tutti gli stati mentre a video se ne vede uno.
    ...paramsPerimetro(store.filters),
    recuperi_mese: true,
    ...(listaRecuperi.sortField.value
      ? {
          order_by: listaRecuperi.sortField.value,
          order_dir: listaRecuperi.sortOrder.value === -1 ? 'desc' : 'asc',
        }
      : {}),
  }),
})

// Scopo: carica la lista con toast d'errore (fail-visible: lo store propaga).
//
// ⚠️ Anche la seconda scheda, e insieme alla prima: il CONTEGGIO sta
// nell'etichetta, e un'etichetta che dice «(0)» finché non la si apre è peggio
// di nessun conteggio. ⛔ Best-effort: se i recuperi non arrivano, la lista
// principale si vede lo stesso.
//
// ⛔ E parte PRIMA dell'`await`, non dopo: stava dentro il `try`, quindi un
//    errore della lista principale la saltava del tutto. I filtri sono già
//    stati riversati nello store da `syncFiltri`, quindi la seconda scheda
//    restava sui dati del filtro precedente mentre il pulsante-stato del nuovo
//    filtro risultava già acceso: un chip che afferma un perimetro che sotto
//    non è applicato. Le due liste hanno perimetri indipendenti — il fallimento
//    di una non è una ragione per non aggiornare l'altra.
async function load() {
  listaRecuperi.page.value = 1
  listaRecuperi.carica().catch(() => {})
  try {
    await store.fetchList()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Scopo: conteggi lotti/mese dell'anno per il badge della sidebar. Fotografia
//        completa (nessun filtro stato): indipendente dai filtri di lista —
//        ⭐ tranne l'interruttore degli annullati, che vale per tutta la pagina:
//        un calendario che contasse i gusci sopra una lista che non li mostra
//        direbbe «35» su un mese con due lotti (misurato il 2026-09-12).
// ⚠️ Guard di versione (`useFetchVersion`, BB), come la lista e i chip: i
//    grilletti sono DUE — l'anno e l'interruttore degli annullati — e senza
//    guard acceso→spento in fretta lascia vincere la risposta lenta, cioe' un
//    calendario che conta i gusci sopra una lista che non li mostra. Nessun
//    errore: solo un numero che non torna con la lista sotto.
const versioneMensile = useFetchVersion()
async function loadMensile() {
  const tag = versioneMensile.tag()
  try {
    const res = await listLottiMensile(anno.value, { annullati: store.filters.annullati })
    if (!versioneMensile.isCurrent(tag)) return
    const map = {}
    for (const m of res.data?.data?.mesi ?? []) map[m.competenza_mese] = m.n_lotti
    conteggiMese.value = map
  } catch (err) {
    // Il fallimento di una richiesta gia' superata non e' una notizia.
    if (!versioneMensile.isCurrent(tag)) return
    notify.error(extractApiError(err, t('common.error')))
  }
}

// Scopo: riversa i filtri della view (mese dalla sidebar, stato dal select)
//        nello store, che è la sola fonte che il BB legge. Il reset a pagina 1
//        avviene SOLO se un filtro è davvero cambiato: su una riattivazione
//        senza cambi (rientro nel tab) l'operatore deve ritrovare la SUA
//        pagina, non la prima — stessa filosofia del refresh idempotente di
//        useSearchTable («offset invariato, cambia solo il contenuto righe»).
function syncFiltri() {
  const competenza = competenzaParam.value
  const stato = statoFilter.value
  if (store.filters.competenza_mese !== competenza || store.filters.stato_lotto !== stato) {
    store.filters.competenza_mese = competenza
    store.filters.stato_lotto = stato
    store.filters.offset = 0
  }
}

// Scopo: cambio mese/filtro stato → lista da pagina 1 (il badge non cambia:
//        è la fotografia dell'anno, ricaricata solo al cambio anno).
function onFilterChange() {
  syncFiltri()
  load()
}

// Scopo: l'interruttore «mostra annullati» cambia il PERIMETRO, non un filtro
//        dentro il perimetro: si ricaricano lista, chip (viaggiano con la
//        lista), scheda recuperi E calendario. Da pagina 1: la pagina 3 di un
//        insieme piu' piccolo puo' non esistere in quello piu' grande e viceversa.
function onAnnullatiChange() {
  store.filters.offset = 0
  load()
  loadMensile()
}

// Il conteggio dei nascosti da mostrare accanto all'interruttore: quello della
// scheda attiva, come i chip — le due schede sono due perimetri.
const annullatiNascosti = computed(() => (
  schedaAttiva.value === 'recuperi' ? annullatiRecuperi.value : store.annullatiCount
))

// KeepAlive (ContentTabs): onActivated scatta anche al primo mount e a ogni
// rientro nel tab (feedback_keepalive_onactivated).
// ⚠️ useSearchTable registra il PROPRIO onActivated (refresh idempotente
// sulle riattivazioni) PRIMA di questo, quindi sulle riattivazioni il suo
// fetch è già in volo quando arriviamo qui: il guard su `store.loading`
// evita il doppio fetch concorrente. Al primo mount invece il suo hook si
// auto-salta (firstActivation) ed è QUESTO a fare il fetch iniziale.
onActivated(() => {
  // ⭐ La pagina si apre SEMPRE sui «Lotti del mese». Il `ref('lotti')` da solo
  //    non basta: la view vive sotto KeepAlive, quindi il valore iniziale vale
  //    al PRIMO mount e mai piu' — chi usciva dalla scheda «Recuperi» la
  //    ritrovava aperta al rientro.
  // ⚠️ Questa e' UNA delle due strade: l'altra e' il cambio di periodo, che non
  //    passa di qui (non smonta e non riattiva) ed e' coperta dal watch su
  //    `competenzaParam`, accanto alla dichiarazione di `schedaAttiva`.
  // ⚠️ Scatta anche al primo mount, dove e' un no-op.
  schedaAttiva.value = 'lotti'
  syncFiltri()
  if (!store.loading) load()
  loadMensile()
  applicaDeepLink()
})

// Drawer diagnostico.
const drawerVisible = ref(false)
// Le sole due liste che tengono a mano lo stato del drawer invece di passare da
// `useDrawerState`: si registrano da se' nella chiusura globale, o resterebbero
// gli unici due pannelli a sopravvivere a un cambio di pagina.
registraDrawerChiudibile(() => { drawerVisible.value = false })

const drawerLottoId = ref(null)

// Scopo: accesso alla riga con il click, come le liste standard. Il kebab
//        (tolto il 2026-07-31, quando l'unica azione era «apri», cioè lo stesso
//        gesto) torna il 2026-08-04 con le azioni di governo: la colonna
//        `azioni` del catalogo è stata riattivata dal team DB.
function apriLotto(row) {
  drawerLottoId.value = row.id
  drawerVisible.value = true
}

// ⭐ DEEP-LINK `?open=<id>`: la lista apre direttamente il lotto indicato.
// Nasce per il BERSAGLIO di un errore (2026-08-24) — il pulsante «Apri Lotto
// 6034» di un toast o di un'icona di riga arriva qui — ma e' il meccanismo
// generico gia' in servizio su `vendite-contratti`, non un canale suo.
//
// ⚠️ In `onActivated` e non in un `watch immediate`, ed e' la differenza che
// conta su questa view: sta sotto KeepAlive, quindi tornarci NON rimonta il
// setup. Un `watch` sulla query funzionerebbe al primo ingresso e poi
// silenziosamente piu' (feedback_keepalive_onactivated).
// ⚠️ Il param si ripulisce subito: senza, un refresh della pagina riaprirebbe
// il pannello che l'operatore aveva appena chiuso.
function applicaDeepLink() {
  const query = { ...route.query }
  let cambiato = false

  // ⭐ `?competenza=YYYY-MM-DD`: arrivare sul MESE giusto. Lo usa la Lente 1,
  //    da cui «Rendi definitive» se n'è andato: senza, il rimando lascerebbe
  //    l'operatore sul mese che la lista aveva l'ultima volta, e la card da cui
  //    è partito parlava di un altro periodo.
  // ⚠️ Porta il MESE e NON «solo i lotti emessi», ed è una limitazione da
  //    sapere: il filtro di questa lista è sullo stato del LAVORO
  //    (bozza/completato/errore), che è un altro asse dallo stato del
  //    DOCUMENTO (emessa/definitiva). Quali righe si possano numerare lo dice
  //    la casella di selezione, riga per riga, col suo motivo.
  const competenza = query.competenza
  if (competenza) {
    delete query.competenza
    cambiato = true
    const d = parseIsoDate(competenza)
    if (d) {
      // ⛔ `cambiaAnno` prende un DELTA, non l'anno: passargli `2026` avrebbe
      //    calcolato `anno + 2026`, sforato il range e fatto un `return`
      //    silenzioso — si sarebbe atterrati sul mese giusto dell'anno
      //    sbagliato, senza un solo errore. (Sbagliato in prima stesura.)
      const delta = d.getFullYear() - anno.value
      if (delta !== 0) cambiaAnno(delta)
      selezionaMese(d.getMonth())
    }
  }

  const grezzo = query.open
  if (grezzo) {
    delete query.open
    cambiato = true
  }
  if (cambiato) router.replace({ query })
  if (!grezzo) return
  const id = Number(grezzo)
  if (!Number.isFinite(id) || id <= 0) return
  nextTick(() => apriLotto({ id }))
}

// Azioni di riga: stesso composable del drawer — conferme, chiamate e testi
// stanno in una sede sola. La lista non ha il blob capability (scelta del team
// DB: nessuna lista del progetto lo consuma per riga), quindi il kebab propone
// i verbi PLAUSIBILI per lo stato della riga e la verifica vera avviene al
// click, leggendo la capability di quel lotto: se il DB dice no, l'operatore
// legge il motivo invece di veder fallire l'azione.
const {
  azioniRiga,
  loading: azioniLoading,
  // FE-2: stato del dialog della data, dal composable condiviso col drawer.
  numeraDialog,
  confermaNumera,
} = useLottoAzioni({
  onDone: async () => {
    await load()
    await loadMensile()
  },
})

// ═══════════════════════════════════════════════════════════════════════════
// RENDI DEFINITIVE — l'atto fiscale, dove sta l'elenco del suo oggetto
// ═══════════════════════════════════════════════════════════════════════════
//
// ⭐ Il verbo è ARRIVATO QUI dalla Lente 1 (2026-08-26). Là agiva sui LOTTI e
//    viveva accanto a un elenco di COMMESSE: per sapere cosa si stava per
//    rendere definitivo bisognava andarsene altrove. La regola è una sola —
//    **un verbo sta dove sta l'elenco del suo oggetto** — ed è la stessa che
//    tiene «Riporta da emettere» sulla card dei residui, dove quell'elenco
//    esiste e non c'è altrove.
//
// ⭐ DUE VERBI NELLO STESSO POSTO, e non è la contraddizione che sembra: quello
//    che Tid non voleva era la stessa azione in DUE POSTI. Qui convivono come
//    su «Da emettere» convivono «Fattura adesso» (il mese) e «Fattura questo»
//    (la selezione).
//
// ⛔ E il verbo di massa RESTA, perché la lista è paginata: il seleziona-tutto
//    opera sulla pagina corrente, quindi un mese da 120 lotti diventerebbe un
//    giro di pagine. Chi vuole chiudere il mese non deve pagare quel prezzo.
// ⚠️ `useActionPermission(codename)` prende l'azione come ARGOMENTO e torna un
//    computed `isAllowed` — non un predicato da chiamare. La prima stesura
//    inventava una firma (`const { can } = useActionPermission()`, poi
//    `can('vendite', '…')`): `can` usciva `undefined` e il computed SOLLEVAVA
//    al primo render, lasciando la pagina **bianca**. Né eslint né la build lo
//    vedono, e di test sul frontend non ce ne sono: l'unico modo di
//    accorgersene è leggere l'API invece di ricordarsela.
// ⭐ Gate UNICO permesso + readonly: le caselle di selezione e i due verbi
//    usano lo stesso predicato, mai due copie che possono divergere.
const { isAllowed: canNumerareFatture } = useActionPermission('numera_fatture_lotti')
const canNumerare = computed(() => canNumerareFatture.value && !isReadonly.value)

// Le righe che l'operatore sta guardando: cambiano con la SCHEDA, e la
// selezione le attraversa entrambe — un lotto di competenza precedente,
// spuntato nei «recuperi», si numera insieme a quelli del mese. È il caso che
// il verbo di massa non sa fare, perché lavora su una competenza sola.
const righeVisibili = computed(() => (schedaAttiva.value === 'recuperi'
  ? listaRecuperi.righe.value
  : store.items))

// I lotti dentro un giro di numerazione ancora vivo (BB condiviso col cruscotto
// competenza). Fa DUE cose, e la seconda è la più importante:
//   1. la rotellina sulla riga — si sa su quali righe si sta lavorando, che il
//      pulsante non può dire;
//   2. ⭐ quelle righe ESCONO dalla selezione e non si ri-spuntano finché il
//      giro è vivo. È così che due invii non possono sovrapporsi, ed è la
//      ragione per cui i giri concorrenti si possono ammettere (sotto).
// ⚠️ Dichiarato QUI, sopra `useSelezioneLotti` che lo consuma: in `<script
//    setup>` una const usata più in alto è una TDZ silenziosa
//    (feedback_vue_watch_immediate_tdz).
// ⚠️ Il perimetro di MESE non marca niente — non ha un elenco di chiavi — ed è
//    esattamente per questo che il suo verbo resta spento finché c'è un giro
//    vivo: il suo perimetro è TUTTO, e si sovrapporrebbe alle righe in volo.
const lottiInGiro = useRigheInGiro()

const selezioneLotti = useSelezioneLotti({
  righeVisibili,
  abilitata: canNumerare,
  chiaviInGiro: lottiInGiro.chiaviInGiro,
})

const { execute: eseguiNumera } = useApiHandler()

// Polling del job: `useJobPolling` è il BB condiviso con la Lente 1.
// ⛔ Qui NON si riusa `useVerboFatturazione` della dashboard: quella funzione
//    porta con sé concetti che questa lista non ha — i «gruppi non serviti», le
//    marcature per `gruppo_key` — e riusarla significherebbe trascinarli dentro
//    per poi ignorarli. Ciò che era davvero condiviso è già estratto, ed è il
//    polling.
// ⭐ GIRI CONCORRENTI AMMESSI (decisione di Tid, 2026-08-27), ricalcando
//    l'emissione mirata del cruscotto competenza (`maxConcurrent: Infinity`,
//    decisione del 2026-08-17). Prima il tetto era 1 e i due verbi restavano
//    spenti per tutta la durata: una seconda selezione si poteva comporre ma
//    non inviare, e intanto la prima restava spuntata — il contatore diceva
//    «(2)» contando lavoro già in volo.
// ⚠️ Si può ammettere SOLO perché le righe spedite escono dalla selezione
//    (`lottiInGiro`): senza quella, due invii avrebbero perimetri sovrapposti e
//    il secondo rimanderebbe lotti già numerati.
const { start: seguiJob, isFollowing, nJobsInCorso: nGiriNumera } = useJobPolling({
  fetchStatus: (jobId) => getFatturazioneRun(jobId),
  maxConcurrent: Infinity,
  onDone: (stato, context) => {
    // ⚠️ Si smarca SEMPRE, anche su esito negativo: una riga marcata da un giro
    //    concluso male resterebbe con la rotellina per sempre — e fuori dalla
    //    selezione, cioè non più lavorabile proprio quando serve riprovare.
    lottiInGiro.smarca(context?.jobId)
    if (stato.stato === 'FATTO') {
      const r = stato.result ?? {}
      const numerati = Number(r.numerati ?? 0)
      const saltati = Number(r.saltati ?? 0)
      const falliti = Number(r.falliti ?? 0)
      // ⚠️ «saltato» = lotto percorso ma NON transitato a definitiva: è un
      //    esito parziale quanto un errore, e tacerlo lascerebbe credere che
      //    tutto il perimetro sia stato numerato.
      if (falliti > 0 || saltati > 0) {
        notify.warn(t('vendite.lotti.numera_esito_parziale', {
          numerati, saltati, falliti, lotti: Number(r.lotti ?? 0),
        }))
      } else {
        notify.success(t('vendite.lotti.numera_esito', { numerati }))
      }
      // ⛔ QUI NON SI AZZERA PIÙ LA SELEZIONE, ed è un cambiamento voluto.
      //    Con i giri concorrenti la selezione che c'è adesso è quella NUOVA,
      //    composta mentre questo giro viaggiava: azzerarla butterebbe via il
      //    lavoro di preparazione dell'operatore per un giro che non lo
      //    riguarda. Le righe di QUESTO giro erano già uscite all'invio, per
      //    mano del prune su `chiaviInGiro`.
      // ⚠️ Il vecchio azzeramento era corretto quando i giri erano uno per
      //    volta: allora «la selezione» e «il perimetro appena spedito» erano
      //    la stessa cosa. Non lo sono più.
    } else {
      notify.error(stato.ultimo_errore?.message || t('vendite.lotti.numera_errore'))
    }
    reload()
    loadMensile()
  },
  onTimeout: (context) => {
    lottiInGiro.smarca(context?.jobId)
    notify.warn(t('vendite.lotti.numera_in_coda'))
    reload()
  },
})

// Il dialog della data: un solo componente per i due perimetri. `lotti` vuoto =
// atto sul mese.
const dialogNumeraPerimetro = ref({ visible: false, lotti: null })

function chiediNumeraSelezione() {
  dialogNumeraPerimetro.value = { visible: true, lotti: [...selezioneLotti.ids.value] }
}

function chiediNumeraMese() {
  dialogNumeraPerimetro.value = { visible: true, lotti: null }
}

// ⚠️ La competenza si congela QUI: il giro può concludersi dopo che l'operatore
//    ha cambiato mese, e i suoi lotti appartengono al mese in cui è partito.
async function confermaNumeraPerimetro(dataDocumento) {
  const lotti = dialogNumeraPerimetro.value.lotti
  dialogNumeraPerimetro.value = { visible: false, lotti: null }
  const competenza = competenzaParam.value
  const res = await eseguiNumera(() => runNumerazione(competenza, {
    dataDocumento: dataDocumento || null,
    lotti,
  }))
  if (res === null) return
  // Stesso perimetro ancora vivo → il backend non crea un secondo job: torna
  // l'id di quello in corso (chiave competenza + scope + digest del perimetro).
  // Seguirlo di nuovo lo conterebbe due volte, e all'operatore va detto che non
  // ha avviato niente di nuovo.
  if (isFollowing(res.job_id)) {
    notify.info(t('vendite.lotti.numera_gia_in_corso'))
    return
  }
  notify.info(t('vendite.lotti.numera_accodato'))
  // ⚠️ Si marca SOLO se il polling ha davvero preso in carico il giro. `start`
  //    può rifiutare (job già seguito, o tetto raggiunto) e ritorna `false`:
  //    marcare comunque lascerebbe righe con la rotellina e fuori dalla
  //    selezione PER SEMPRE, perché lo `smarca` vive in `onDone`/`onTimeout` —
  //    callback di un giro che nessuno sta seguendo e che quindi non arriveranno
  //    mai. Sono righe che diventano non lavorabili senza che niente lo dica.
  const seguito = seguiJob(res.job_id, { jobId: res.job_id, competenza })
  // Le chiavi del giro sono gli id del perimetro: solo per l'atto su SELEZIONE.
  if (seguito && lotti?.length) lottiInGiro.marca(res.job_id, lotti)
}

// ⭐ I DUE VERBI SU SCHERMO PICCOLO. Sotto i 1024px (o su un dispositivo senza
//    hover) i pulsanti a etichetta lunga non ci stanno: finiscono in un kebab,
//    che e' lo standard di tutte le liste — le stesse classi
//    `app-page-actions-desktop` / `app-page-actions-compact` di
//    `PageActionsBar`, cosi' il punto di rottura e' UNO e non due che possono
//    divergere.
// ⚠️ I verbi restano QUI, accanto alla lista, e non salgono nella barra azioni
//    di pagina: quella e' la toolbar di utility (ricarica / personalizza /
//    esporta), e il principio di questo cantiere e' che «un verbo sta dove sta
//    l'elenco del suo oggetto». Cambiare posto per guadagnare il kebab avrebbe
//    disfatto la ragione per cui i verbi sono arrivati su questa pagina.
// ⚠️ Nel menu il motivo per cui una voce e' spenta si vede lo stesso: una voce
//    di Menu disabilitata mostra comunque il suo testo, mentre un Button
//    disabilitato non riceve nemmeno gli eventi del mouse (vedi il wrapper del
//    tooltip nel template).
// Icona dei due verbi dell'atto fiscale: una sola, `MANAGE_ICONS.NUMERA`, usata
// dai pulsanti e dalle voci del kebab.

const verbiMenuRef = ref(null)
function toggleVerbiMenu(event) {
  verbiMenuRef.value?.toggle(event)
}

// ⭐ SORGENTE UNICA dei due verbi: etichetta, icona, quando sono spenti, il
//    motivo e il comando. Da qui li rendono ENTRAMBE le forme — i pulsanti per
//    esteso sopra i 1024px e le voci del kebab sotto.
// ⚠️ Prima erano scritti due volte, e il difetto non sarebbe stato un errore
//    ma una DERIVA: si cambia il testo o la condizione di spegnimento da una
//    parte sola, e le due forme dicono cose diverse a seconda della larghezza
//    della finestra — cioè il difetto piu' difficile da riprodurre che esista.
const verbiNumerazione = computed(() => {
  const nSelezionati = selezioneLotti.selezione.value.length
  const giroVivo = nGiriNumera.value > 0
  return [
    {
      key: 'numera-selezionati',
      label: t('vendite.lotti.numera_selezionati', { n: nSelezionati }),
      disabled: nSelezionati === 0,
      tooltip: t('vendite.lotti.numera_selezionati_tooltip'),
      command: chiediNumeraSelezione,
    },
    {
      key: 'numera-mese',
      label: t('vendite.lotti.numera_mese'),
      // Il verbo di MESE aspetta ogni giro vivo: il suo perimetro è TUTTO e si
      // sovrapporrebbe alle righe già in volo. Vedi il commento su `lottiInGiro`.
      disabled: giroVivo,
      loading: giroVivo,
      tooltip: giroVivo
        ? t('vendite.lotti.numera_mese_atteso')
        : t('vendite.lotti.numera_mese_tooltip'),
      command: chiediNumeraMese,
    },
  ]
})

const verbiMenuItems = computed(() => verbiNumerazione.value.map((v) => ({
  label: v.label,
  icon: MANAGE_ICONS.NUMERA,
  // Classe via helper centralizzato: la palette delle voci kebab vive in
  // `rowActions.js`, non in una stringa scritta qui.
  class: menuItemClass(undefined, 'app-menu-item-action'),
  disabled: v.disabled,
  command: v.command,
})))

// Istanza del pannello esiti, per poterlo ricaricare dal «Ricarica» di pagina.
// ⛔ Dal 2026-09-03 il pannello non ha piu' un pulsante suo: due «Ricarica»
//    identici a mezzo schermo di distanza non erano una comodita' ma un dubbio
//    su cosa aggiornassero. ⚠️ Toglierlo senza questo aggancio lo avrebbe
//    lasciato SENZA alcun modo di aggiornarsi a comando: `defineExpose({refresh})`
//    era dichiarato dal primo giorno e non lo chiamava nessuno.
const esitiRef = ref(null)

// Azioni di pagina: quelle standard del BB (reload / personalizza / export).
// Niente «Nuovo» — un lotto non si crea da qui, lo genera la pipeline: lo
// scaffolding lo omette da sé, non ricevendo `onNew`.
// Unico adattamento: «Ricarica» aggiorna ANCHE i badge per-mese della sidebar
// e il pannello esiti, che il BB non conosce — la fotografia dell'anno e il
// riassunto dei giri devono restare coerenti con la lista.
const azioniPagina = computed(() =>
  pageActions.value.map((a) => (a.key === 'reload'
    ? { ...a, command: () => { reload(); loadMensile(); esitiRef.value?.refresh() } }
    : a)),
)
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-toolbar-start">
        <h2 style="margin: 0;">{{ t('vendite.lotti.page_title') }}</h2>
        <small class="app-text-muted">{{ t('vendite.lotti.page_description') }}</small>
      </div>
      <PageActionsBar :actions="azioniPagina">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <div class="app-dash-layout">
      <!-- Pannello laterale anno + 12 mesi (BB condiviso con la Lente
           Competenza): badge = numero lotti generati nel mese. -->
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
            v-if="mesi[idx].n_lotti > 0"
            class="app-dash-mese-lotti"
            v-tooltip.right="t('vendite.lotti.mese_lotti', { n: mesi[idx].n_lotti })"
          >
            {{ mesi[idx].n_lotti }} <i :class="MANAGE_ICONS.LOTTO" />
          </span>
        </template>
      </DashMesiSidebar>

      <div class="app-dash-main">
        <!-- Stepper compatto anno/mese (BB condiviso): solo piccoli schermi. -->
        <DashMeseStepper
          :anno="anno"
          :mese-idx="meseIdx"
          :nomi-mesi="nomiMesi"
          @step="stepMese"
        >
          <template #badge>
            <span v-if="mesi[meseIdx].n_lotti > 0" class="app-dash-mese-lotti">
              {{ mesi[meseIdx].n_lotti }} <i :class="MANAGE_ICONS.LOTTO" />
            </span>
          </template>
        </DashMeseStepper>

        <!-- Esiti fatturazione (C-5): stato coda stampa + giri del mese
             selezionato. La competenza è la STESSA della lista: pannello e
             lista raccontano lo stesso periodo. -->
        <FatturazioneEsitiPanel ref="esitiRef" :competenza-mese="competenzaParam" />

        <div class="app-page-toolbar">
          <FiltriLista :store="store" :inert="perimetroBloccato">
            <!-- Etichetta A SINISTRA della tendina, non sopra: due righe per un
                 filtro sono altezza tolta ai lotti, che sono il lavoro.
                 ⭐ `app-dash-filter-toggle` e' la classe che i tre cruscotti
                 usano gia' per «etichetta + controllo in linea» (muted, 0.78rem):
                 questa e' la quarta occorrenza dello stesso filtro di
                 cruscotto, quindi si riusa invece di scriverne uno locale. -->
            <label class="app-dash-filter-toggle">
              <span>{{ t('vendite.lotti.filtro_stato') }}</span>
              <Select
                v-model="statoFilter"
                :options="statoOptions"
                option-label="label"
                option-value="value"
                show-clear
                size="small"
                :placeholder="t('common.all')"
                @update:model-value="onFilterChange"
              />
            </label>

            <!-- Pulsanti-filtro per stato: la ripartizione della scheda attiva,
                 solo sopra zero. Stesso ref della tendina qui a fianco, quindi
                 i due comandi non possono mostrare filtri diversi. -->
            <div v-if="chipStati.length" class="app-dash-chips">
              <span
                v-for="c in chipStati"
                :key="c.stato"
                class="app-dash-chip"
                :class="{ 'is-selected': statoFilter === c.stato }"
                role="button"
                tabindex="0"
                @click="selezionaStato(c.stato)"
                @keydown.enter="selezionaStato(c.stato)"
              >
                {{ c.label }}
                <strong>{{ c.n }}</strong>
              </span>
            </div>

            <!-- ⭐ «Mostra annullati (N)» (2026-09-12). I lotti annullati sono
                 gusci: fuori dal perimetro di default, ma non spariscono in
                 silenzio — il numero dice che ci sono, e l'interruttore li
                 rimette dentro OVUNQUE (lista, chip, calendario, export).
                 BB `FiltroToggle` col conteggio, lo stesso del «Mostra
                 archiviate» delle code; `app-dash-filter-toggle` gli da' il look dei filtri di
                 cruscotto che ha accanto. -->
            <FiltroToggle
              v-model="store.filters.annullati"
              class="app-dash-filter-toggle"
              :label="t('vendite.lotti.filtro_annullati')"
              :hint="t('vendite.lotti.filtro_annullati_hint')"
              :count="annullatiNascosti"
              @change="onAnnullatiChange"
            />
          </FiltriLista>

          <!-- I DUE VERBI DELL'ATTO FISCALE. ⚠️ `severity="warn"` su entrambi:
               è la convenzione che distingue la numerazione — irreversibile —
               dai verbi pre-fiscali. -->
          <!-- ⭐ Gate UNICO: `canNumerare` porta già permesso E readonly, e lo
               stesso predicato governa le caselle di selezione. Ripeterlo sui
               `:disabled` sarebbe una seconda copia che può divergere. -->
          <div v-if="canNumerare" class="app-lotti-verbi">
            <!-- Sopra i 1024px: i due verbi per esteso. Sotto: il kebab qui in
                 fondo, con le stesse due voci. -->
            <span class="app-page-actions-desktop">
              <!-- ⚠️ Il tooltip sta sul WRAPPER e non sul Button: un bottone
                   disabilitato non riceve eventi del mouse, quindi il tooltip
                   appeso a lui non comparirebbe mai — ed è proprio quando è
                   spento che il motivo serve. Stessa ragione per cui dal
                   2026-08-27 le due barre azioni condivise hanno l'involucro. -->
              <span
                v-for="v in verbiNumerazione"
                :key="v.key"
                class="app-action-tooltip-wrap"
                v-tooltip.bottom="v.tooltip"
              >
                <Button
                  :label="v.label"
                  :icon="MANAGE_ICONS.NUMERA"
                  size="small"
                  severity="warn"
                  :outlined="v.key === 'numera-mese'"
                  :loading="v.loading"
                  :disabled="v.disabled"
                  @click="v.command"
                />
              </span>
            </span>

            <span class="app-page-actions-compact">
              <Button
                :icon="MANAGE_ICONS.KEBAB"
                text
                rounded
                class="app-manage-btn"
                v-tooltip.bottom="t('common.altre_azioni')"
                aria-haspopup="true"
                @click="toggleVerbiMenu"
              />
              <Menu ref="verbiMenuRef" :model="verbiMenuItems" popup />
            </span>
          </div>
        </div>

        <!-- Colonne, ordine e visibilità arrivano dal catalogo `vendite.lotti`:
             qui restano solo le celle che hanno un rendering proprio. Le altre
             (documento, utility, area geografica, creato, creato da) le rende il
             BB dal `formato` del catalogo. -->
        <!-- ⭐ DUE SCHEDE (decisione di Tid, 2026-08-24). La seconda esiste
             perché una commessa di competenza GIUGNO fatturata ad AGOSTO
             produce un documento con data agosto dentro un lotto di giugno:
             chi lavora sul mese di agosto non lo trova, perché lo cerca —
             giustamente — per la data del documento e non per la competenza
             della commessa.
             ⚠️ Stesso componente in entrambe: stesse colonne, stesse azioni per
             costruzione. -->
        <Tabs v-model:value="schedaAttiva">
          <TabList>
            <Tab value="lotti">{{ t('vendite.lotti.tab_lotti_mese') }}</Tab>
            <Tab value="recuperi">
              {{ t('vendite.lotti.tab_recuperi') }}
              <template v-if="listaRecuperi.totale.value"> ({{ listaRecuperi.totale.value }})</template>
            </Tab>
          </TabList>
          <TabPanels>
            <TabPanel value="lotti">
              <LottiLista
                @lista-pronta="registraLista"
                :rows="store.items"
                :total="store.totalRecords"
                :loading="store.loading"
                :paginator-options="paginatorProps"
                :page="tablePage"
                :sort-field="paginatorProps.sortField"
                :sort-order="paginatorProps.sortOrder"
                :build-row-actions="(data) => azioniRiga(data, { readonly: isReadonly })"
                :azioni-disabled="azioniLoading"
                :selezione="selezioneLotti.perLista.value"
                :in-giro="lottiInGiro.inGiro"
                @page="onPage"
                @sort="onSort"
                @row-click="apriLotto"
                @config-loaded="onConfigLoaded"
              />
            </TabPanel>

            <TabPanel value="recuperi">
              <!-- ⚠️ La riga che spiega la scheda: senza, un elenco di lotti di
                   giugno dentro la pagina filtrata su agosto si legge come un
                   filtro che non ha funzionato. -->
              <Message severity="secondary" :closable="false" class="app-mb-1">
                {{ t('vendite.lotti.recuperi_lista_nota') }}
              </Message>
              <!-- Personalizza colonne + esporta anche qui: è una lista come le
                   altre, e l'export porta con sé il filtro della scheda. -->
              <div class="app-page-toolbar">
                <PageActionsBar :actions="azioniRecuperi.azioniLista.value">
                  <template #suffix>
                    <ListaConfigStatusTag :dirty="azioniRecuperi.dirty.value" />
                  </template>
                </PageActionsBar>
              </div>
              <LottiLista
                @lista-pronta="registraListaRecuperi"
                :rows="listaRecuperi.righe.value"
                :total="listaRecuperi.totale.value"
                :loading="listaRecuperi.loading.value"
                :paginator-options="listaRecuperi.paginatorOptions.value"
                :page="listaRecuperi.page.value"
                :sort-field="listaRecuperi.sortField.value"
                :sort-order="listaRecuperi.sortOrder.value"
                :build-row-actions="(data) => azioniRiga(data, { readonly: isReadonly })"
                :azioni-disabled="azioniLoading"
                :selezione="selezioneLotti.perLista.value"
                :in-giro="lottiInGiro.inGiro"
                empty-key="vendite.lotti.nessun_recupero_lista"
                :empty-icon="STATUS_ICONS.VUOTO"
                @page="listaRecuperi.onPage"
                @sort="listaRecuperi.onSort"
                @row-click="apriLotto"
                @config-loaded="listaRecuperi.onConfigLoaded"
              />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </div>
    </div>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />

    <!-- Dialog di export della seconda scheda: separato perché i filtri sono
         diversi, e un dialog solo esporterebbe la lista sbagliata. -->
    <ExportDialog
      v-model:visible="azioniRecuperi.exportDialogVisible.value"
      :loading="azioniRecuperi.exportLoading.value"
      @export="azioniRecuperi.onExportConfirm"
    />

    <LottoDrawer
      v-model:visible="drawerVisible"
      :lotto-id="drawerLottoId"
      @changed="load"
    />

    <!-- FE-2: stesso dialog del drawer, stesso stato: il kebab della lista e la
         barra del drawer non possono chiedere la data in due modi diversi. -->
    <NumerazioneDataDialog
      v-model:visible="numeraDialog.visible"
      :lotto-id="numeraDialog.lottoId"
      @conferma="confermaNumera"
    />
    <!-- La data dell'atto di PERIMETRO (selezione oppure mese intero). ⚠️ È lo
         stesso componente del verbo per-riga, in modo `numera`: il limite lo
         porta lui, ricalcolandolo sul perimetro che riceve. -->
    <NumerazioneDataDialog
      v-model:visible="dialogNumeraPerimetro.visible"
      :competenza-mese="dialogNumeraPerimetro.lotti ? null : competenzaParam"
      :lotti="dialogNumeraPerimetro.lotti"
      @conferma="confermaNumeraPerimetro"
    />
  </div>
</template>

<style scoped>
/* I due verbi dell'atto fiscale, in barra accanto ai filtri. */
.app-lotti-verbi {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.app-lotto-stato-cella {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
/* Rosso dal token PrimeVue, mai un esadecimale a mano: e' la convenzione gia'
   in uso per le spie di stato (`CodaStampaTab`). */
.app-lotto-spia-errore {
  color: var(--app-severity-danger);
}
/* Badge "numero lotti generati" nel mese (sidebar/stepper anno-mese). Neutro:
 * è un conteggio informativo, non un allarme (diverso dai badge errori/fermi
 * della Lente Competenza). */
.app-dash-mese-lotti {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.8rem;
  color: var(--app-text-muted);
}
</style>
