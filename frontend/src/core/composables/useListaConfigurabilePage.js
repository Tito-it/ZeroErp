// Scopo: scaffolding condiviso delle pagine lista basate su
// <ListaConfigurabile>. Estratto 2026-06-02 (regola del 2): le SearchTable
// di clienti/soggetti/fornitori/contratti ripetevano identici useSearchTable +
// ref alla lista (dirty/colonneNuove/configReady) + wiring export
// (useFileDownload/ExportDialog) + le 4 pageActions standard
// (reload/personalizza/export/new) + onConfigLoaded. Qui vivono una volta
// sola; il componente mantiene solo i propri filtri, slot e azioni di riga.
//
// Uso tipico:
//   const {
//     searchText, onPage, onSort, applyFilters, reload, paginatorProps,
//     tablePage, listaRef, dirty, configReady,
//     exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded,
//     pageActions, mostraLista, mostraSearchHint,
//   } = useListaConfigurabilePage(store, {
//     exportFn: exportFornitori,
//     getExportParams: (fmt) => buildExportParams(fmt),
//     newTooltipKey: 'anagrafiche.fornitori.nuovo_fornitore',
//     onNew: () => emit('new'),
//     searchTableOptions: { defaultSortField: 'ragione_sociale_completa' },
//   })
//
// Liste a ricerca obbligatoria (<SearchHint> + lista dietro `v-show`): usare
// `mostraSearchHint` / `mostraLista` invece di `!store.hasSearched &&
// !store.loading`. Non e' zucchero: dentro ci sta il cancello di perimetro
// emittente, che altrimenti resta nascosto proprio quando deve parlare (vedi
// il commento su `perimetroBloccato`).
//
// `getExportParams` e' invocata SOLO al click di export (lazy): puo' quindi
// riferire `searchText`/ref dei filtri definiti nel componente DOPO il
// destructuring (closure lazy). `extraActions` (opzionale) inserisce azioni
// utility custom prima di "Nuovo". `onReload` (opzionale) sostituisce il
// comando del pulsante "Ricarica" per le pagine che devono ricaricare anche
// altro insieme alla lista (il caller richiama `reload` dentro il proprio
// handler).

import { computed, ref, unref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSearchTable } from './useSearchTable'
import { useListaAzioni } from './useListaAzioni'
import { MANAGE_ICONS } from '../constants'
import { paramsRicerca } from '../utils/listParams'
import { allineaMisuraConfig } from '../allineaMisuraConfig'

// Scopo: la soglia della ricerca libera dalla configurazione risolta
//        (`ricerca_min_caratteri`): un intero >= 1, altrimenti `null` («non
//        nota»: `listParams` usa la soglia di progetto).
function sogliaDellaConfig(config) {
  const v = config?.ricerca_min_caratteri
  return Number.isInteger(v) && v >= 1 ? v : null
}

export function useListaConfigurabilePage(
  store,
  {
    exportFn,
    getExportParams = () => ({}),
    newTooltipKey,
    newLabelKey = null,
    onNew,
    searchTableOptions = {},
    extraActions = null,
    onReload = null,
  } = {},
) {
  const { t } = useI18n()
  const search = useSearchTable(store, searchTableOptions)

  // Cancello di perimetro emittente (P-2b): la conclusione la fa il BACKEND e
  // arriva nella config (`richiede_scelta_emittente`); <ListaConfigurabile>
  // mostra gia' il pannello AL POSTO della tabella. Qui non si ricalcola
  // niente — si legge, e si decide COSA della pagina resta a video.
  //
  // ⚠️ Perche' vive nello scaffolding e non nei template: sulle liste a
  // ricerca obbligatoria (clienti, soggetti, fornitori, indirizzi, articoli)
  // il pannello non si vedeva MAI. Il caller tiene l'intera lista dietro
  // `v-show="hasSearched || loading"` e al suo posto mostra <SearchHint>:
  // finche' non si cerca, il cancello e' renderizzato ma nascosto — cioe'
  // proprio nello stato in cui doveva parlare. A video il difetto si vedeva
  // come «il pannello lampeggia mentre cerco e sparisce»: durante la fetch
  // `loading` lo scopre, poi il BE rifiuta con 422 (toast soppresso),
  // `hasSearched` resta false e il `v-show` lo richiude.
  // ⚠️ Dichiarato in testa perche' lo leggono sia le azioni di testata (qui
  // sotto) sia i caller, che ci legano l'`inert` sui propri filtri.
  const perimetroBloccato = ref(false)

  // Stato della lista configurabile + le due azioni di utility
  // (personalizza/export): vivono in `useListaAzioni`, sede unica condivisa
  // coi cruscotti, che non possono usare questo scaffolding (store diverso).
  const listaRef = ref(null)
  const {
    dirty, colonneNuove, configReady,
    exportDialogVisible, exportLoading, onExportConfirm,
    azioniLista,
  } = useListaAzioni(() => listaRef.value, { exportFn, getExportParams })

  // I due stati della pagina a ricerca obbligatoria, ed e' UNA regola sola:
  // il secondo e' la negazione del primo, scritto come tale. Scriverli come
  // due espressioni gemelle («bloccato || cercato || carico» e «!bloccato &&
  // !cercato && !carico») li avrebbe fatti divergere alla prima modifica —
  // ed e' la classe di difetto che questo cantiere ha gia' pagato una volta.
  // ⚠️ <SearchHint> va TOLTO col cancello su, non affiancato: inviterebbe a
  // cercare in una lista che il backend rifiutera' comunque finche'
  // l'emittente non e' scelto, e due pannelli che dicono cose diverse sono
  // peggio di nessuno.
  const mostraLista = computed(
    () => perimetroBloccato.value || store.hasSearched || store.loading,
  )
  const mostraSearchHint = computed(() => !mostraLista.value)

  // Allinea store.filters.limit alla pagina_dimensione risolta dal BE quando
  // la misura della configurazione cambia (BB `allineaMisuraConfig`).
  const misuraConfig = allineaMisuraConfig()
  function onConfigLoaded(config) {
    // ⚠️ PRIMA dell'allineamento della misura: quello tocca il `limit` solo
    // quando la misura della configurazione cambia. Il cancello no — e' uno stato che
    // cambia quando cambia l'emittente attivo, e leggerlo dopo un `return`
    // significherebbe lasciarlo fermo al primo valore.
    perimetroBloccato.value = config?.richiede_scelta_emittente === true
    // Sospende la lista finche' il cancello e' su: ogni richiesta sarebbe
    // rifiutata con 422 dal guard di backend, che resta l'unica protezione
    // vera. Si scrive nei DUE versi — rientrare in un emittente riapre la
    // lista senza che nessuno debba ricordarsi di abbassare la bandiera.
    // ⚠️ Il guard `in` non e' difensivismo: tutti i caller di oggi passano uno
    // store di `createCrudStore`, che la chiave ce l'ha. Serve perche' lo
    // scaffolding non ha modo di PRETENDERLO — chi domani passera' uno store
    // fatto a mano non deve schiantare su una pagina che, senza sospensione,
    // funziona lo stesso: il cancello si vede, e il backend rifiuta comunque.
    const eraSospesa = store.fetchSospesa === true
    if ('fetchSospesa' in store) store.fetchSospesa = perimetroBloccato.value
    // ⛔ E ABBASSARE LA BANDIERA NON BASTA: la fetch chiesta mentre era su e'
    //    uscita senza chiamare (`useListaEmptyStateFetch`), e nessuno la rifa'.
    //    Il caso e' il tab-lista in un drawer: si monta prima del dettaglio, la
    //    prima config arriva senza emittente (cancello su), la fetch del padre
    //    completo cade nel vuoto, e la config riletta con l'emittente sblocca
    //    una lista che resta vuota — con la frase «nessuna riga» sotto.
    const sbloccata = eraSospesa && !perimetroBloccato.value
    // ⭐ La casella di ricerca si mostra solo se la lista cerca davvero
    //    (`ricerca_full`, brief-be-ricerca-full-liste-residue §7-bis): la
    //    legge `FiltriLista` dallo store. Prima dell'allineamento della misura,
    //    come il cancello: l'amministratore puo' spegnere le colonne, e la
    //    configurazione si ricarica (salvataggio della personalizzazione).
    // ⚠️ Assegnata senza guard `in`: gli store scritti a mano senza il core
    //    la ricevono lo stesso (lo store Pinia e' reattivo anche sulle chiavi
    //    nuove). Una chiave assente sarebbe una casella sempre accesa.
    store.ricercaFull = typeof config?.ricerca_full === 'boolean' ? config.ricerca_full : null
    // Un termine arrivato da fuori (`?search=` di un deep-link, un tab
    // riattivato) su una lista che non cerca: la casella non c'e' piu' per
    // cancellarlo, e il backend risponderebbe una lista vuota. Si svuota dalla
    // casella stessa, cosi' il `watch` di `useSearchTable` riallinea lo store
    // e rifa' la fetch.
    if (store.ricercaFull === false && search.searchText.value) search.searchText.value = ''
    // ⭐ Da quanti caratteri la lista cerca (`ricerca_min_caratteri`, brief-db-
    //    be-fe-ricerca-soglia-per-lista): un fatto della lista, letto dalla
    //    stessa colonna con cui il BB del backend decide se filtrare. Lo tiene
    //    lo store (dichiarato dal BB di stato), lo usano `termineCorto` e
    //    `paramsRicerca`. Prima dell'allineamento della misura, come
    //    `ricercaFull`: e' un fatto della lista, e si rilegge a ogni config.
    // ⚠️ Un valore che non e' un intero >= 1 non si prende per buono: `null`
    //    = soglia di progetto. Un `0` o una stringa manderebbero ogni lettera.
    const soglia = sogliaDellaConfig(config)
    // ⚠️ La prima fetch puo' essere partita PRIMA della config (liste che
    //    partono piene, deep-link `?search=KG`), con la soglia di ripiego: se
    //    la soglia vera cambia cio' che si manda, la lista si ricarica — senza,
    //    «KG» su unita' di misura mostrerebbe la lista intera fino al tasto
    //    successivo. Si confronta il PARAMETRO, non il numero: da 3 a 1 senza
    //    termine in casella non c'e' niente da rifare.
    const cambiaLaRicerca = store.ricercaMinCaratteri !== soglia
      && paramsRicerca(store.filters, { minCaratteri: store.ricercaMinCaratteri }).search
        !== paramsRicerca(store.filters, { minCaratteri: soglia }).search
    store.ricercaMinCaratteri = soglia
    // Su una lista che non cerca il termine e' appena stato tolto dalla
    // casella, e la fetch la rifa' il `watch` di `useSearchTable`.
    let ricarica = (cambiaLaRicerca && store.ricercaFull !== false) || (sbloccata && !store.loading)
    const newLimit = misuraConfig.daApplicare(config)
    if (newLimit && newLimit !== store.filters.limit) {
      store.filters.limit = newLimit
      // ⚠️ Con un passo nuovo l'offset di prima non e' piu' una pagina.
      store.filters.offset = 0
      if (store.hasSearched) ricarica = true
    }
    // Una fetch sola anche quando cambiano insieme pagina e soglia.
    if (ricarica) store.fetchList()
  }

  const pageActions = computed(() => {
    const rawExtras =
      typeof extraActions === 'function'
        ? extraActions()
        : (extraActions?.value ?? extraActions ?? [])
    const extras = Array.isArray(rawExtras) ? rawExtras : []
    // `export` e `new` sono CONDIZIONATE al proprio handler: senza `exportFn`
    // il dialog si aprirebbe e `onExportConfirm` uscirebbe subito (pulsante
    // che non fa nulla), e senza `onNew` il comando sarebbe `undefined`.
    // Prima erano incondizionate e i caller senza "Nuovo" filtravano a mano —
    // stesso `filter(a => a.key !== 'new')` ripetuto in 3 file: la condizione
    // vive qui una volta sola (2026-07-31). La condizione su `exportFn` e' ora
    // dentro `useListaAzioni`, che produce le due azioni di lista.
    const conNew = typeof onNew === 'function'
    // Cancello di perimetro su: TUTTE le azioni di testata si spengono, in un
    // punto solo (§C-3-bis). Non e' un elenco di eccezioni — «ricarica» non ha
    // niente da ricaricare (la lista e' sospesa), «esporta» scaricherebbe lo
    // stesso 422 della lista (l'endpoint dichiara lo stesso `lista_codice` e
    // cade sotto lo stesso guard), «nuovo» aprirebbe un drawer che al
    // salvataggio si sente dire dal database che l'emittente non e' risolto, e
    // le azioni custom del caller non hanno modo di essere piu' fortunate.
    // ⚠️ `disabled` e non «tolte»: la barra resta la stessa e spenta, che e'
    // un'informazione; farla sparire e ricomparire sarebbe un'interfaccia che
    // si riscrive sotto le mani mentre il pannello spiega cosa fare.
    // ⚠️ Col cancello giu' l'azione passa INTATTA (stesso oggetto): niente
    // `disabled: false` scritto sopra, che spegnerebbe il `disabled` proprio
    // dell'azione — «personalizza» finche' la config non c'e', «esporta»
    // mentre un download e' in corso. Col cancello su vince `true`, che e'
    // l'OR di quei due stati.
    const spegni = (a) => (perimetroBloccato.value ? { ...a, disabled: true } : a)
    return [
      spegni({
        key: 'reload',
        kind: 'utility',
        label: t('common.reload_list'),
        icon: MANAGE_ICONS.RELOAD,
        // `onReload` (opzionale) SOSTITUISCE il reload di lista quando la
        // pagina deve ricaricare anche altro insieme alla lista — es. il tab
        // BA emittente, dove il summary e' indipendente dalla pagina corrente
        // e senza di lui il pulsante "default" resta disallineato. Il caller
        // richiama `reload` (esposto qui sotto) dentro il proprio handler.
        command: onReload ?? search.reload,
      }),
      ...azioniLista.value.map(spegni),
      ...extras.map(spegni),
      ...(conNew ? [spegni({
        key: 'new',
        kind: 'primary',
        // ⚠️ `newLabelKey` esiste perche' il verbo di creazione non si chiama
        //    sempre «Nuovo»: sul registro del plafond si «FORZA una rettifica»,
        //    ed e' il nome a dire che da li' non si scrivono fatture. Senza,
        //    l'unico modo di avere l'etichetta giusta era riscriversi a mano
        //    l'intera `pageActions` — che e' quello che
        //    `CanaliIncassoSearchTable` ha fatto, perdendo le utility del BB.
        label: newLabelKey ? t(newLabelKey) : t('common.new'),
        tooltip: newTooltipKey ? t(newTooltipKey) : t('common.new'),
        icon: MANAGE_ICONS.ADD,
        hideWhenReadonly: true,
        command: onNew,
      })] : []),
    ]
  })

  // Pagina 1-based per <ListaConfigurabile :page>, con guard su rows>0
  // (evita Infinity/NaN se il limit fosse mai nullish). `paginatorProps` di
  // useSearchTable e' un ComputedRef: va unwrappato con `unref` (dentro JS non
  // c'e' l'auto-unwrap del template), altrimenti `.rows`/`.first` sono
  // undefined e la pagina resta bloccata a 1 (paginazione rotta).
  const tablePage = computed(() => {
    const pp = unref(search.paginatorProps)
    return pp?.rows ? pp.first / pp.rows + 1 : 1
  })

  return {
    ...search,
    tablePage,
    listaRef,
    dirty,
    colonneNuove,
    configReady,
    exportDialogVisible,
    exportLoading,
    onExportConfirm,
    onConfigLoaded,
    pageActions,
    // Consumato dai caller per rendere `inert` il proprio blocco filtri: la
    // toolbar e' markup loro, e lo scaffolding non ha modo di raggiungerla.
    perimetroBloccato,
    mostraLista,
    mostraSearchHint,
  }
}
