// Store Pinia Lente 1 Competenza (brief-design-fatturazione-due-lenti §4):
// anno, mese selezionato, aggregata 12 mesi × 4 stadi, drill-down per commessa
// (DEC-4: una riga per commessa, dettaglio nel drawer) e pannello errori vivi.
// Le action fanno la chiamata axios internamente e lasciano propagare gli
// errori: i componenti le invocano dentro try/catch con extractApiError
// (niente useApiHandler.execute su promise non-axios —
// memoria feedback_useapihandler_solo_axios).
// Le sezioni paginate (commesse, errori) usano il BB usePagedDashFetch
// (guard di versione + rientro pagina-oltre-l'ultima); l'aggregata ha il suo
// guard di versione dedicato.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useDashRiepilogo } from '../../core/composables/useDashRiepilogo'
import { usePagedDashFetch } from '../../core/composables/usePagedDashFetch'
import { USO_MISURA } from '../../core/misurePagina'
import { oggiAziendale } from '../../core/utils/date'
import {
  getDashboardCompetenza,
  listDashboardCompetenzaCommesse,
  listDashboardCompetenzaErrori,
  listDashboardCompetenzaGruppi,
  listDashboardCompetenzaResidui,
} from '../api/dashboardCompetenza'

// Stadio del funnel il cui drill-down NON è la lista commesse ma la lista dei
// GRUPPI FATTURABILI: è l'unico stadio in cui il verbo è «Fattura», e si
// fattura un documento (o gli oneri di una commessa), non una commessa —
// che è multi-sorgente e quindi non isola nulla. Costante unica: la usano il
// gate della fetch e il template.
export const STADIO_GRUPPI = 'DA_EMETTERE'

// Stadio il cui drill-down NON è la lista commesse ma la lista dei RESIDUI.
// ⭐ Stessa forma di STADIO_GRUPPI, e per la stessa ragione: qui il verbo è
// «Riporta da emettere», e agisce su un'ATTIVITÀ — la commessa aggregata non
// direbbe su cosa si sta per agire.
// ⚠️ La card conta più di quello che la lista mostra, ed è voluto: lo stadio
// contiene quattro situazioni e solo `RESIDUO` chiede un'azione. Il numero
// grande è «quanto lavoro è fermo qui», la lista è «su cosa si può agire».
export const STADIO_RESIDUI = 'EMESSA_NON_FATTURATA'

// Voce «cliente non determinabile» del filtro cliente: sono i gruppi il cui BA
// di fatturazione non e' risolvibile (tipicamente il padre e' fuori dallo scope
// dell'operatore). Si MOSTRA e non si nasconde — una riga che non si riesce ad
// attribuire e' precisamente la riga che sfugge, ed e' il caso da cui nasce
// tutto il filtro.
// ⚠️ E' un sentinella di sola INTERFACCIA (una `<Select>` ha un valore solo):
// lo store lo traduce nel parametro `ba_non_determinabile`, cosi' l'API non
// riceve mai un id finto in un campo che trasporta chiavi vere. Stringa e non
// numero apposta: non puo' collidere con nessun id.
export const GRUPPI_CLIENTE_NON_DETERMINABILE = '__NON_DETERMINABILE__'

// Voce «sezionale non determinabile» del filtro sezionale: i gruppi il cui
// registro di fatturazione non è risolvibile — tipicamente perché il tipo
// documento non è ancora stato scelto sulle righe (il vincolo a DB lo pretende
// solo da riga approvata e non emessa, quindi su `DA_APPROVARE` il vuoto è
// legittimo).
// ⚠️ Stesso sentinella di sola INTERFACCIA della voce cliente qui sopra, e per
// lo stesso motivo: una `<Select>` ha un valore solo, ma all'API non deve
// arrivare un id finto in un campo che trasporta chiavi vere. Lo store lo
// traduce nel parametro `registro_non_risolvibile`.
export const GRUPPI_REGISTRO_NON_RISOLVIBILE = '__NON_RISOLVIBILE__'

// Riepilogo di perimetro vuoto: forma stabile per il render prima della prima
// risposta (mai `undefined` nel template).
const RIEPILOGO_VUOTO = { n_gruppi: 0, n_attivita: 0, valore: null, n_gruppi_oneri: 0 }

// Scopo: stato di ordinamento server-side di una lista lazy del cruscotto —
//        i due ref (colonna + direzione) e l'handler che applica l'evento
//        @sort del DataTable. Estratto alla 2ª occorrenza (commesse + gruppi,
//        regola del 2, ok Tid 2026-07-27): erano due copie identiche salvo la
//        colonna di default.
//        Convenzione PrimeVue: `sortOrder === 1` = asc; sort RIMOSSO
//        (`sortField` null) = ritorno al default della lista, non "nessun
//        ordinamento" — su una lista paginata server-side un ordine assente
//        renderebbe la paginazione non deterministica.
//        Solo stato: la ricarica (che riparte da pagina 1) resta al caller,
//        che ha la sua gestione errori.
function useSortState(defaultBy, defaultDir = 'desc') {
  const orderBy = ref(defaultBy)
  const orderDir = ref(defaultDir)
  function apply(event) {
    orderBy.value = event.sortField || defaultBy
    orderDir.value = event.sortField && event.sortOrder === 1 ? 'asc' : defaultDir
  }
  function reset() {
    orderBy.value = defaultBy
    orderDir.value = defaultDir
  }
  return { orderBy, orderDir, apply, reset }
}

export const useDashboardCompetenzaStore = defineStore('vendite-dashboard-competenza', () => {
  const anno = ref(oggiAziendale().getFullYear())
  // Indice 0-11 del mese selezionato (default: mese corrente dell'azienda).
  const meseIdx = ref(oggiAziendale().getMonth())
  // Stadio selezionato per il drill-down (null = nessuna card attiva).
  const stadioSelezionato = ref(null)
  // Filtro recuperi tardivi del drill-down (solo attivita' emesse in ritardo).
  const soloRitardo = ref(false)

  // Ordinamento del drill-down per commessa (convenzione order_by/order_dir come
  // le liste standard): default "valore totale" DESC (le commesse piu' pesanti
  // prima). Lista lazy (paginata server-side) -> ordinamento server-side,
  // corretto su TUTTE le pagine. Si ordina per gli AGGREGATI, non per la riga.
  const commesseSort = useSortState('valore_tot')

  // Aggregata: array 12 mesi { competenza_mese, stadi, totali, n_errori }
  // dal BE. Fetch guardata anti-race via BB useDashRiepilogo: scarta la
  // risposta se nel frattempo l'anno e' cambiato di nuovo (vince l'ultima
  // richiesta, non l'ultima risposta arrivata).
  const mesi = ref([])
  const aggregata = useDashRiepilogo(
    () => getDashboardCompetenza(anno.value),
    (data) => {
      mesi.value = data.mesi ?? []
    }
  )

  // Drill-down per commessa + pannello errori: sezioni paginate standard.
  const commesseFetch = usePagedDashFetch((paging, competenzaMese) =>
    listDashboardCompetenzaCommesse({
      competenza_mese: competenzaMese,
      stadio: stadioSelezionato.value,
      solo_ritardo: soloRitardo.value,
      order_by: commesseSort.orderBy.value,
      order_dir: commesseSort.orderDir.value,
      ...paging,
    })
  )

  // Drill-down GRUPPI FATTURABILI (card «Da emettere»): stessa meccanica delle
  // altre sezioni paginate, piu' il `riepilogo` di perimetro che il BE mette
  // nell'envelope. Il riepilogo NON si somma dalle righe della pagina: sarebbe
  // un parziale che sembra un totale, e nessuno somma a mano piu' pagine per
  // accorgersene.
  const gruppiSort = useSortState('valore')
  const gruppiRiepilogo = ref({ ...RIEPILOGO_VUOTO })
  // Filtro «tipo documento/sorgente». `null` = tutti (parametro omesso), stessa
  // convenzione dello stadio: il default non e' un valore speciale da gestire,
  // e' l'assenza del filtro.
  const gruppiTipo = ref(null)
  // Voci del filtro, calcolate dal BE SUI DATI del perimetro: solo cio' che
  // esiste davvero, con il conteggio. Non seguono il filtro (se lo seguissero,
  // scegliendo un tipo le altre voci sparirebbero dalla tendina).
  const gruppiTipi = ref([])
  // Filtro CLIENTE. Il valore e' l'`id` del billing account di FATTURAZIONE —
  // lo stesso elemento che il DB mette nella chiave della fattura — e MAI la
  // ragione sociale: lo stesso soggetto puo' avere piu' alberi di BA, anche
  // sotto emittenti diversi, con nome e codice fiscale identici, e quegli
  // alberi finiscono su fatture DIVERSE.
  // `null` = tutti; il sentinella `GRUPPI_CLIENTE_NON_DETERMINABILE` e' la voce
  // dei gruppi il cui cliente di fatturazione non e' risolvibile (padre fuori
  // scope): vive SOLO nel frontend e viene tradotto in un parametro dedicato,
  // cosi' l'API non porta id finti in un campo che trasporta chiavi vere.
  const gruppiCliente = ref(null)
  const gruppiClienti = ref([])
  // Filtro SEZIONALE (D-5). ⚠️ L'asse è l'INSIEME dei sezionali del gruppo, non
  // il codice unico: un gruppo che ne tocca due ha il codice vuoto e deve
  // comparire sotto entrambe le voci. Filtrare per codice lo farebbe sparire da
  // tutte e due — cioè proprio il gruppo che c'è da guardare.
  const gruppiRegistro = ref(null)
  const gruppiRegistri = ref([])
  // Quanti gruppi ha il perimetro BASE, per la sola voce «Tutti i sezionali».
  // ⚠️ Non si ricava dalla facet (sommarla sovrastima: un gruppo su due
  // sezionali è contato sotto entrambi) né dal riepilogo (che segue i filtri,
  // quindi «Tutti» scenderebbe al conteggio del sezionale scelto).
  const gruppiPerimetroN = ref(0)
  // Ricerca libera. Separata dal filtro cliente perche' risponde a un'altra
  // domanda — «dov'e' finito ORD0005174» invece di «dammi tutto di Rossi» —
  // e sotto i 3 caratteri il BE la ignora (non svuota la lista).
  const gruppiSearch = ref('')
  // Scopo: i filtri di dominio della lista gruppi, nella forma che l'API vuole.
  //
  // ⛔ ESISTE PERCHÉ LE COPIE ERANO DUE, e la seconda ha davvero sbagliato: la
  //    fetch li componeva qui, l'export se li ricomponeva nella view — e
  //    aggiungendo il filtro sezionale è finito solo nella fetch. Il file
  //    esportato avrebbe portato TUTTE le righe mentre a video ne restavano 32,
  //    e chi lo apre non ha modo di accorgersene: crede di avere il perimetro
  //    che aveva a schermo. È lo stesso difetto che il commento dell'export
  //    dichiarava di voler evitare.
  //    Una sede sola: il prossimo filtro nasce in tutti e due i posti o in
  //    nessuno.
  //
  // ⚠️ Fuori NON escono i sentinella: `gruppiClienteParams`/`gruppiRegistroParams`
  //    li traducono nei due flag dedicati, così all'API non arriva mai un id
  //    finto in un campo che trasporta chiavi vere.
  // ⛔ Niente paginazione né `formato`: sono di trasporto, e i due chiamanti li
  //    trattano diversamente (l'export salta la paginazione).
  function gruppiFiltriApi() {
    return {
      stadio: STADIO_GRUPPI,
      tipo_gruppo: gruppiTipo.value,
      ...gruppiClienteParams(),
      ...gruppiRegistroParams(),
      search: gruppiSearch.value || null,
      order_by: gruppiSort.orderBy.value,
      order_dir: gruppiSort.orderDir.value,
    }
  }

  const gruppiFetch = usePagedDashFetch(
    (paging, competenzaMese) =>
      listDashboardCompetenzaGruppi({
        competenza_mese: competenzaMese,
        ...gruppiFiltriApi(),
        ...paging,
      }),
    {
      onPayload: (payload) => {
        gruppiRiepilogo.value = payload.riepilogo ?? { ...RIEPILOGO_VUOTO }
        gruppiTipi.value = payload.tipi ?? []
        gruppiClienti.value = payload.clienti ?? []
        gruppiRegistri.value = payload.registri ?? []
        gruppiPerimetroN.value = Number(payload.n_gruppi_perimetro ?? 0)
      },
    }
  )

  // Scopo: traduce la scelta della tendina nei parametri dell'API. Il
  //        sentinella non esce mai da qui: fuori viaggiano o un id vero, o il
  //        flag `ba_non_determinabile`.
  function gruppiClienteParams() {
    if (gruppiCliente.value === GRUPPI_CLIENTE_NON_DETERMINABILE) {
      return { ba_non_determinabile: true }
    }
    return { ba_fatturazione_id: gruppiCliente.value }
  }

  // Scopo: gemello del precedente per il sezionale. Il sentinella non esce mai
  //        da qui: fuori viaggiano o un id vero, o il flag dedicato.
  function gruppiRegistroParams() {
    if (gruppiRegistro.value === GRUPPI_REGISTRO_NON_RISOLVIBILE) {
      return { registro_non_risolvibile: true }
    }
    return { registro_id: gruppiRegistro.value }
  }

  // Scopo: carica una pagina di gruppi fatturabili del mese. Parte solo sullo
  //        stadio che ha «Fattura» come verbo: sugli altri la lista di
  //        riferimento resta quella per commessa.
  async function fetchGruppi(competenzaMese) {
    if (stadioSelezionato.value !== STADIO_GRUPPI) return
    await gruppiFetch.fetch(competenzaMese)
  }

  // Scopo: azzera la lista gruppi (cambio mese/stadio) incluso il riepilogo —
  //        lasciarlo indietro mostrerebbe i totali del contesto precedente
  //        sopra una lista vuota.
  function resetGruppi() {
    gruppiFetch.reset()
    gruppiRiepilogo.value = { ...RIEPILOGO_VUOTO }
    gruppiTipo.value = null
    gruppiTipi.value = []
    gruppiCliente.value = null
    gruppiClienti.value = []
    gruppiRegistro.value = null
    gruppiRegistri.value = []
    gruppiPerimetroN.value = 0
    gruppiSearch.value = ''
  }

  // Ordinamento del pannello errori: default `data_evento desc` (eventi
  // recenti prima), che replica il default del BE e il preset del seed — la
  // lista non si riordina sotto gli occhi al primo caricamento.
  const erroriSort = useSortState('data_evento')
  const erroriFetch = usePagedDashFetch(
    (paging, competenzaMese) =>
      listDashboardCompetenzaErrori({
        competenza_mese: competenzaMese,
        order_by: erroriSort.orderBy.value,
        order_dir: erroriSort.orderDir.value,
        ...paging,
      }),
    { misura: USO_MISURA.COMPATTA }
  )

  // Drill-down RESIDUI (card «Emesse non fatturate»): l'elenco su cui agisce
  // «Riporta da emettere».
  // ⭐ Ordinamento `competenza_mese` ASC, e NON `valore` DESC come le sorelle:
  // e' allineato all'`ordinamento_default` del preset `dash_competenza_residui_default`
  // (`ui.lista_preset`, 2026-08-27), che quel campo non lo consuma ancora il
  // frontend — la convenzione e' allinearlo a mano, come fanno `auditLog` ed
  // `emittentiFiscali`.
  // ⛔ E la ragione e' di dominio, non di simmetria: questa non e' una lista di
  // GRANDEZZE, e' una CODA DI RECUPERO. Un residuo che invecchia si avvicina al
  // limite di emissione, quindi il piu' vecchio e' il piu' a rischio — stessa
  // logica del backlog (`anzianita_giorni desc`), non dei gruppi fatturabili.
  // ⚠️ La prima versione ordinava per `valore` DESC per copia dalle sorelle:
  // avrebbe messo in cima i residui piu' grossi invece dei piu' urgenti, e la
  // lista avrebbe raccontato una priorita' diversa da quella che il catalogo
  // dichiara — senza che niente andasse storto.
  const residuiSort = useSortState('competenza_mese', 'asc')
  const residuiFetch = usePagedDashFetch(
    (paging, competenzaMese) =>
      listDashboardCompetenzaResidui({
        competenza_mese: competenzaMese,
        order_by: residuiSort.orderBy.value,
        order_dir: residuiSort.orderDir.value,
        ...paging,
      }),
    { misura: USO_MISURA.COMPATTA }
  )

  // Scopo: carica una pagina di residui del mese. Parte solo con la card
  //        «Emesse non fatturate» selezionata, come le altre sezioni.
  async function fetchResidui(competenzaMese) {
    if (stadioSelezionato.value !== STADIO_RESIDUI) return
    await residuiFetch.fetch(competenzaMese)
  }

  // Scopo: azzera la lista residui (cambio mese/anno o deselezione card).
  function resetResidui() {
    residuiSort.reset()
    residuiFetch.reset()
  }

  // Scopo: carica una pagina di commesse per (mese, stadio selezionato,
  //        filtro ritardo). Senza stadio attivo non parte nessuna fetch.
  async function fetchCommesse(competenzaMese) {
    if (!stadioSelezionato.value) return
    await commesseFetch.fetch(competenzaMese)
  }

  // Scopo: carica una pagina di errori vivi del mese (blocco 4).
  async function fetchErrori(competenzaMese) {
    await erroriFetch.fetch(competenzaMese)
  }

  // Scopo: azzera il drill-down (cambio mese/anno, o passaggio a un'ALTRA card)
  //        e invalida le fetch in volo.
  // ⚠️ Non piu' la «deselezione» della card: dal 2026-09-03 la selezione e'
  //    esclusiva e un secondo click sulla stessa card non chiude piu' la lista
  //    (vedi `DashboardCompetenzaView.selezionaStadio`).
  function resetCommesse() {
    stadioSelezionato.value = null
    soloRitardo.value = false
    commesseFetch.reset()
    // Il drill-down e' UNO solo: deselezionare la card deve azzerare anche la
    // lista gruppi, altrimenti resterebbe a video appesa a uno stadio che non
    // e' piu' selezionato.
    resetGruppi()
    // ⚠️ E la lista residui, per la stessa ragione. Dimenticarla qui e' il
    //    difetto che non si vede provando una card sola: si apre «Emesse non
    //    fatturate», si clicca un'altra card, e la selezione di righe resta
    //    viva sotto uno stadio che non c'e' piu'.
    resetResidui()
  }

  // Scopo: azzera il pannello errori (cambio mese/anno) e invalida le fetch.
  function resetErrori() {
    erroriSort.reset()
    erroriFetch.reset()
  }

  // Scopo: reset per logout (plugin autoResetPlugin via userScoped) —
  //        resetAll riporta anche le pageSize al default (stato utente).
  function clearUserState() {
    aggregata.invalidate()
    anno.value = oggiAziendale().getFullYear()
    meseIdx.value = oggiAziendale().getMonth()
    mesi.value = []
    stadioSelezionato.value = null
    soloRitardo.value = false
    commesseSort.reset()
    commesseFetch.resetAll()
    // ⚠️ `resetAll` e non `reset`: al logout si riporta al default anche la
    //    dimensione di pagina, che e' una preferenza dell'operatore che se ne
    //    va — la stessa regola delle sezioni sorelle (feedback_pinia_userscoped).
    residuiSort.reset()
    residuiFetch.resetAll()
    gruppiSort.reset()
    gruppiRiepilogo.value = { ...RIEPILOGO_VUOTO }
    gruppiTipo.value = null
    gruppiTipi.value = []
    // ⚠️ Anche il filtro cliente e la ricerca: sono STATO UTENTE (chi stavo
    // guardando, cosa stavo cercando) e sopravvivere al logout li porterebbe
    // nella sessione di un altro operatore, che magari quel cliente non lo vede
    // nemmeno (memoria feedback_pinia_userscoped).
    gruppiCliente.value = null
    gruppiClienti.value = []
    gruppiRegistro.value = null
    gruppiRegistri.value = []
    gruppiPerimetroN.value = 0
    gruppiSearch.value = ''
    gruppiFetch.resetAll()
    erroriSort.reset()
    erroriFetch.resetAll()
  }

  return {
    anno,
    meseIdx,
    stadioSelezionato,
    soloRitardo,
    commesseOrderBy: commesseSort.orderBy,
    commesseOrderDir: commesseSort.orderDir,
    mesi,
    commesse: commesseFetch.items,
    commesseCount: commesseFetch.count,
    commessePage: commesseFetch.page,
    commessePageSize: commesseFetch.pageSize,
    commesseLoading: commesseFetch.loading,
    applyCommessePage: commesseFetch.applyPageEvent,
    applyCommesseSort: commesseSort.apply,
    gruppi: gruppiFetch.items,
    gruppiCount: gruppiFetch.count,
    gruppiPage: gruppiFetch.page,
    gruppiPageSize: gruppiFetch.pageSize,
    gruppiLoading: gruppiFetch.loading,
    gruppiLoaded: gruppiFetch.loaded,
    gruppiOrderBy: gruppiSort.orderBy,
    gruppiOrderDir: gruppiSort.orderDir,
    gruppiRiepilogo,
    gruppiTipo,
    gruppiTipi,
    gruppiCliente,
    gruppiClienti,
    gruppiRegistro,
    gruppiRegistri,
    gruppiPerimetroN,
    gruppiFiltriApi,
    gruppiSearch,
    applyGruppiPage: gruppiFetch.applyPageEvent,
    applyGruppiSort: gruppiSort.apply,
    fetchGruppi,
    resetGruppi,
    residui: residuiFetch.items,
    residuiCount: residuiFetch.count,
    residuiPage: residuiFetch.page,
    residuiPageSize: residuiFetch.pageSize,
    residuiLoading: residuiFetch.loading,
    residuiLoaded: residuiFetch.loaded,
    residuiOrderBy: residuiSort.orderBy,
    residuiOrderDir: residuiSort.orderDir,
    applyResiduiPage: residuiFetch.applyPageEvent,
    applyResiduiSort: residuiSort.apply,
    fetchResidui,
    resetResidui,
    errori: erroriFetch.items,
    erroriCount: erroriFetch.count,
    erroriPage: erroriFetch.page,
    erroriPageSize: erroriFetch.pageSize,
    erroriLoading: erroriFetch.loading,
    applyErroriPage: erroriFetch.applyPageEvent,
    erroriOrderBy: erroriSort.orderBy,
    erroriOrderDir: erroriSort.orderDir,
    applyErroriSort: erroriSort.apply,
    fetchMensile: aggregata.fetchRiepilogo,
    fetchCommesse,
    fetchErrori,
    resetCommesse,
    resetErrori,
    clearUserState,
  }
}, {
  // Dati filtrati per operatore (scope GUC fail-closed): reset al logout.
  userScoped: true,
})
