// Scopo: binding toolbar filtri ↔ store.filters per le liste (B14 2026-06-05,
//        regola del 2). Le SearchTable vendite (ordini/offerte/contratti/
//        preventivi) ripetevano per ogni filtro la coppia
//        `const xFilter = ref(store.filters.key ?? null)` +
//        `function onXChange() { store.filters.key = xFilter.value; applyFilters() }`,
//        e per le date un parse ISO→Date inline **non uniforme** (contratti
//        usava `new Date(iso)` → timezone-shift; gli altri `T00:00:00`
//        local-safe). Qui le primitive centralizzano ref + handler usando
//        sempre `parseIsoDate`/`toDateString` local-safe.
//
// I binder ritornano `{ value, onChange }` con `value` = il **ref** (non
// unwrappato): il consumer lo destruttura coi propri nomi storici, cosi' il
// template resta invariato.
//
//   const { bindSelect, bindDate, bindToggle, bindLookup } = useStoreFilterBindings(store, applyFilters)
//   const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato')
//   const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da')
//   const { value: soloNegativa, onChange: onSoloNegativaChange } = bindToggle('solo_negativa')
//   const { value: articoloFilter, onChange: onArticoloChange } = bindLookup('articolo_id')
//   // template: v-model="statoFilter" @change="onStatoChange"
//   //           v-model="dataDaFilter" @date-select="onDataDaChange" ...
//   //           <FiltroToggle v-model="soloNegativa" @change="onSoloNegativaChange" />
//   //           <ArticoloLookup v-model="articoloFilter" @update:model-value="onArticoloChange" />
//
// ⭐ LA DISCIPLINA COMUNE AI QUATTRO: `onChange` scatta SOLO da un evento
//    utente nel template, mai da un `watch` sul widget. Il `watch` c'e', ma
//    nel verso opposto (store → widget), per i cambi fatti FUORI dal widget —
//    `useSearchTable` che azzera i default data su una ricerca esterna, un
//    reset, un deep-link: l'operatore deve sempre vedere il valore che limita
//    la lista. Cosi' non c'e' nessun loop da guardare.
//
// `buildExportParams` resta caller-side: la mappatura filtri→query export
// diverge per ogni lista (rename `data_a`→`data_al`/`validita_dal_max`,
// `solo_ultima_revisione` string-cast, `scadenza_mese` YYYY-MM) e ingabbiarla qui
// sarebbe un config piu' lungo del codice che sostituisce.

import { computed, ref, watch } from 'vue'
import { parseIsoDate, toDateString } from '../utils/date'

export function useStoreFilterBindings(store, applyFilters) {
  // Filtro select/valore semplice: ref inizializzato dallo store, onChange
  // riscrive lo store e rilancia la fetch. Il watch store→ref tiene la
  // toolbar allineata anche quando il filtro viene cambiato FUORI dal
  // widget (es. useSearchTable che azzera i default data su ricerca
  // esterna): l'operatore deve sempre vedere il valore che limita la lista.
  // Nessun loop: onChange scatta solo da evento utente, mai dal watch.
  function bindSelect(storeKey, { defaultValue = null } = {}) {
    const value = ref(store.filters[storeKey] ?? defaultValue)
    watch(() => store.filters[storeKey], (nuovo) => {
      value.value = nuovo ?? defaultValue
    })
    function onChange() {
      store.filters[storeKey] = value.value
      applyFilters()
    }
    return { value, onChange }
  }

  // Filtro data: ref Date local-safe dallo store (ISO 'YYYY-MM-DD'), onChange
  // serializza con `toDateString`. `clearTo` (opzionale) ripristina un floor
  // quando l'utente cancella (es. contratti: il floor standard, la lista ne vuole uno).
  // Stesso sync store→ref di bindSelect (vale solo per i cambi esterni:
  // il floor clearTo resta legato al gesto utente di svuotamento).
  function bindDate(storeKey, { clearTo = null } = {}) {
    const value = ref(parseIsoDate(store.filters[storeKey]))
    watch(() => store.filters[storeKey], (nuovo) => {
      value.value = parseIsoDate(nuovo)
    })
    // Scopo: RISOLVERE il valore (compreso il floor di `clearTo`) e scriverlo
    //        nello store, SENZA rilanciare la fetch.
    // ⭐ E' separata da `onChange` perche' il valore che finisce nel filtro non
    //    e' sempre quello che il widget ha emesso: svuotando una data con un
    //    `clearTo` il filtro diventa il FLOOR, non `null`. Chi deve decidere
    //    qualcosa SU quel valore — `bindPeriodo`, che controlla l'invariante
    //    `da <= a` — puo' saperlo solo dopo, e prima della fetch: con la sola
    //    `onChange` l'unico punto in cui guardare sarebbe dopo la partenza
    //    della richiesta, cioe' troppo tardi per evitarne una seconda.
    function applica() {
      if (!value.value && clearTo) {
        const fallback = clearTo()
        value.value = fallback
        store.filters[storeKey] = toDateString(fallback)
      } else {
        store.filters[storeKey] = value.value ? toDateString(value.value) : null
      }
    }
    function onChange() {
      applica()
      applyFilters()
    }
    return { value, onChange, applica }
  }

  // Filtro INTERRUTTORE (`FiltroToggle`): il widget e' un booleano, lo store
  // porta il valore che il backend legge — e non e' sempre `true`/`false`.
  // Estratto il 2026-09-18 (regola del 2, ok Tid) da CINQUE siti con TRE forme:
  // un ref + onChange (pratiche), un computed get/set INVERTITO (offerte e
  // preventivi: «mostra storico» acceso ⇔ `solo_ultima_revisione = false`),
  // un computed get/set che scrive `true | null` (disponibilita').
  //
  // `on` / `off` sono i DUE valori dello store: acceso ⇒ `store = on`, spento
  // ⇒ `store = off`, e il widget e' acceso quando `store === on`. Coprono
  // entrambe le divergenze senza un flag `inverti`: offerte passa
  // `{ on: false, off: true }`, disponibilita' i default.
  // ⚠️ `off` e' `null` di default, non `false`: il core manda ogni filtro
  //    `!= null`, e un `false` sul filo sarebbe un parametro che il backend
  //    legge senza che filtri niente. Chi ha `false` come default dello store
  //    (pratiche) lo dichiara.
  // Il `value` e' un computed sullo store, non un ref copiato: un cambio da
  // fuori (reset, logout) si vede da se', senza il watch di sync.
  function bindToggle(storeKey, { on = true, off = null } = {}) {
    const value = computed({
      get: () => store.filters[storeKey] === on,
      set: (acceso) => { store.filters[storeKey] = acceso ? on : off },
    })
    function onChange() {
      applyFilters()
    }
    return { value, onChange }
  }

  // ⭐ IL PERIODO — `data_da`/`data_a` NON sono due filtri: sono UN filtro con
  // due estremi (ok Tid, 2026-09-22, voce A5 del brief dei filtri compatti).
  // Ne discende la coppia di binding in una chiamata sola, e il building block
  // `<FiltroPeriodo :periodo="periodo" />` che la rende come una cosa unica.
  //
  // ⛔ NON e' zucchero su due `bindDate`. Prima di questo, la coppia era
  //    riscritta in DICIOTTO liste, e il cablaggio degli eventi era
  //    DIVERGENTE: `@date-select` + `@clear-click` in quasi tutte,
  //    `@update:modelValue` nei contratti. I due non sono equivalenti — col
  //    primo una data DIGITATA a mano nella casella non applica il filtro:
  //    l'operatore vede la data che ha scritto e una lista che non l'ha
  //    ricevuta, senza nessun errore. Il BB tiene il verso giusto in un posto
  //    solo (`feedback_bb_legge_non_trasporta`: un BB unifica la lettura, e i
  //    punti che traducevano diversamente si cercano uno per uno).
  //
  // ⚠️ Internamente sono due `bindDate`, non una copia della loro logica: il
  //    parse locale-safe, la serializzazione ISO, il sync store→ref e il
  //    `clearTo` restano dove erano. `clearToDa`/`clearToA` esistono perche'
  //    una lista puo' volere il FLOOR su un solo estremo (i contratti: il
  //    default temporale si ripristina svuotando `data_da`, e `data_a` resta
  //    libera).
  //
  // ⭐ E RITORNA DUE SETTER, non i ref nudi coi loro handler, ed e' una
  //    correzione dell'API fatta dal lint (`vue/no-mutating-props`): il
  //    componente che rende il periodo riceve la coppia come PROP, e scrivere
  //    dentro un ref che sta in una prop e' scrivere in casa d'altri —
  //    funziona, e nasconde chi possiede lo stato. Con `setDa`/`setA` la
  //    proprieta' resta qui: il componente LEGGE `da.value` e CHIEDE il
  //    cambio, che e' la stessa cosa che fa un `v-model` ma detta a voce.
  function bindPeriodo(keyDa = 'data_da', keyA = 'data_a', { clearToDa = null, clearToA = null } = {}) {
    const estremoDa = bindDate(keyDa, { clearTo: clearToDa })
    const estremoA = bindDate(keyA, { clearTo: clearToA })

    // ⛔ UN INTERVALLO INVERTITO NON E' UN PERIODO (decisione di Tid,
    //    2026-09-22: «non puo' essere da > a»). E' una regola sul modello, non
    //    una validazione di comodo: `da > a` descrive un insieme vuoto, e una
    //    lista che torna vuota per questo non lo dice a nessuno — l'operatore
    //    legge «non ci sono documenti» invece di «hai chiesto un intervallo che
    //    non esiste».
    //
    // ⭐ IL MECCANISMO: **l'estremo che si tocca vince, l'altro si apre.** Chi
    //    sposta `da` oltre `a` sta dicendo dove comincia la finestra; il vecchio
    //    `a` non descrive piu' niente, quindi si SVUOTA — e un estremo vuoto e'
    //    «aperto da quella parte», che e' un periodo legittimo.
    // ⛔ NON si blocca con `min-date`/`max-date` incrociati: e' la trappola
    //    provata e buttata lo stesso giorno — legando un estremo all'altro,
    //    spostare la finestra in AVANTI diventa impossibile finche' non si tocca
    //    prima l'altra data.
    // ⛔ E NON si SCAMBIANO i due: lo scambio inventa un periodo che nessuno ha
    //    chiesto, e lo fa in silenzio. Svuotare invece si VEDE — il campo
    //    accanto si spegne davanti all'operatore, ed e' il suo avviso.
    // ⚠️ La correzione porta l'altro estremo a `null`, MAI al suo `clearTo`: il
    //    floor e' la risposta al gesto «svuoto io», e qui il gesto e' un altro.
    //    Per giunta un floor puo' essere a sua volta invertito rispetto alla
    //    data appena scelta, e si tornerebbe al punto di partenza.
    // ⚠️ Il confronto e' sulle stringhe ISO (`YYYY-MM-DD`, ordinabili come
    //    testo), non sui `Date`: i due estremi viaggiano cosi' verso il backend,
    //    e confrontare gli oggetti significherebbe portarsi dentro l'ora e il
    //    fuso per una domanda che parla di giorni.
    // ⭐ Simmetrico nei due versi per costruzione (`feedback_normalize_guard_simmetrico`):
    //    la stessa funzione serve i due estremi, scambiando i ruoli.
    function invertito(nuovo, altro, nuovoEPrimo) {
      if (!nuovo || !altro) return false
      const a = toDateString(nuovo)
      const b = toDateString(altro)
      return nuovoEPrimo ? a > b : a < b
    }

    // Scopo: scrive l'estremo toccato e, se l'altro e' diventato impossibile, lo
    //        svuota — nello stesso giro, quindi UNA sola fetch.
    //
    // ⛔ L'INVARIANTE SI CONTROLLA SUL VALORE RISOLTO, NON SU QUELLO EMESSO dal
    //    widget, ed e' la correzione del 2026-09-22: guardando `v` il guard
    //    saltava tutto il ramo del `clearTo`. Chi SVUOTA un estremo che ha un
    //    floor (i contratti: `clearToDa`) emette `null` — e `null` non puo'
    //    invertire niente, quindi il guard concludeva «a posto» — ma il filtro
    //    che finisce nello store e' il FLOOR, che puo' benissimo cadere DOPO
    //    l'altro estremo. Risultato: `da > a` sopravviveva proprio dove il
    //    `clearTo` esiste, cioe' nell'unica lista per cui l'opzione e' nata, e
    //    senza nessun errore. ⭐ E' il difetto che `feedback_contratto_dichiarato_provalo_intero`
    //    descrive: un ramo che il contratto dichiara ammesso va provato per
    //    intero, non solo nel verso che si aveva in mente scrivendolo.
    //
    // ⚠️ L'altro estremo si azzera scrivendo ref E store QUI, senza passare dal
    //    suo `onChange`: quello rifarebbe la fetch, e la prima partirebbe con
    //    l'intervallo ancora invertito — una lista vuota che lampeggia e poi si
    //    riempie e' il modo in cui un'interfaccia sembra rotta mentre funziona.
    //    Per la stessa ragione la fetch parte UNA VOLTA SOLA, in fondo: qui si
    //    usa `applica()` (scrive e basta) e non `onChange()` (scrive e rilancia).
    function scrivi(estremo, altro, chiaveAltro, v, estremoEPrimo) {
      estremo.value.value = v
      estremo.applica()
      if (invertito(estremo.value.value, altro.value.value, estremoEPrimo)) {
        altro.value.value = null
        store.filters[chiaveAltro] = null
      }
      applyFilters()
    }

    const setDa = (v) => scrivi(estremoDa, estremoA, keyA, v, true)
    const setA = (v) => scrivi(estremoA, estremoDa, keyDa, v, false)
    return { da: estremoDa.value, a: estremoA.value, setDa, setA }
  }

  // Filtro LOOKUP RICCO (`ArticoloLookup`, `BillingAccountLookup`…): il
  // widget tiene l'OGGETTO scelto (gli serve per mostrarlo), lo store l'id.
  // Estratto il 2026-09-18 (regola del 2, ok Tid) dalle due copie identiche
  // del registro e della disponibilita' di magazzino.
  //
  // Verso widget → store: `onChange` alla scelta o al clear (i lookup ricchi
  // emettono `update:modelValue` in entrambi i casi), `store = obj[idField]`.
  // ⚠️ Nel template `v-model` PRECEDE `@update:model-value`: Vue accoda i
  //    listener nell'ordine in cui sono scritti, e `onChange` legge il ref
  //    che il `v-model` ha appena aggiornato — come per `bindSelect` con
  //    `@update:model-value`.
  // Verso store → widget: l'azzeramento, e l'OGGETTO scelto quando lo store lo
  // ricorda. ⭐ L'oggetto si salva accanto all'id (`<storeKey>_obj`, stampo
  //    `feedback_autocomplete_restore`: il `_obj` nel form per il restore
  //    dell'AutoComplete): un widget che RIMONTA — la scheda di un `<Tabs lazy>`
  //    al cambio scheda, la disponibilita' di magazzino (2026-09-18) — rinasce
  //    con il ref vuoto mentre lo store tiene il filtro attivo, e l'operatore
  //    vedrebbe una lista filtrata da un articolo che il picker non mostra.
  //    ⚠️ `<storeKey>_obj` NON e' fra i `filterDefaults`: `paramsFiltro` manda
  //    solo quelle chiavi, quindi l'oggetto non viaggia mai sul filo, e il
  //    `reset()` dello store lo fa sparire con tutto il resto.
  // ⛔ Un id messo da fuori SENZA l'oggetto (un deep-link con il solo id) non si
  //    rende: da un id non si ricostruisce l'oggetto senza una lettura by-id,
  //    e per gli articoli quella lettura oggi non esiste. Il giorno che servira'
  //    e' un'opzione `risolvi(id) -> Promise<obj>` qui, non un watch nel
  //    chiamante.
  function bindLookup(storeKey, { idField = 'id' } = {}) {
    const chiaveObj = `${storeKey}_obj`
    const ricordato = () => {
      const obj = store.filters[chiaveObj]
      return obj && obj[idField] === store.filters[storeKey] ? obj : null
    }
    const value = ref(ricordato())
    watch(() => store.filters[storeKey], (id) => {
      if (id == null) {
        value.value = null
        if (chiaveObj in store.filters) store.filters[chiaveObj] = null
      } else if (value.value?.[idField] !== id) {
        value.value = ricordato()
      }
    })
    function onChange() {
      const obj = value.value ?? null
      store.filters[storeKey] = obj?.[idField] ?? null
      store.filters[chiaveObj] = obj
      applyFilters()
    }
    return { value, onChange }
  }

  return { bindSelect, bindDate, bindPeriodo, bindToggle, bindLookup }
}
