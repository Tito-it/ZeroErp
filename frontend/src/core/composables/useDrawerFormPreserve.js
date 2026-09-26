// Scopo: preservare le modifiche NON SALVATE del form quando il drawer
//        ricarica il dettaglio dal server. Estratto 2026-08-17 (regola del 2
//        alla 3a occorrenza, ok Tid) dal DdtDrawer, dove il difetto è stato
//        trovato in-app: valeva identico su OrdiniDrawer e PreventiviDrawer.
//
// IL PROBLEMA CHE RISOLVE
// I drawer documento ricaricano il dettaglio da molti punti — apertura,
// auto-save bozza, salvataggio di una RIGA (`@changed`), cambio stato, azioni —
// e `loadDetail` fa `form.value = {...dati dal server}`: una SOSTITUZIONE.
// Chi aveva compilato la testata senza ancora salvarla se la vedeva tornare
// indietro, in silenzio. Sul DDT: si sceglieva la causale di trasporto, si
// salvava una riga, e la causale tornava vuota — sembrava «in creazione la
// testata non si salva», mentre era il salvataggio della RIGA a cancellarla.
//
// ⚠️ Il rimedio NON è rincorrere i chiamanti di `loadDetail`: erano sette nel
// solo DDT, e l'ottavo nascerebbe scoperto. Si mette in UN punto — dentro la
// ricarica — e vale per tutti.
//
// COME SI USA
//   const { preserva, reset } = useDrawerFormPreserve(form)
//
//   async function loadDetail(id) {
//     const applica = preserva()            // ① cattura il non-salvato
//     const data = await fetch(...)
//     form.value = { ...dal server ... }    // ② sostituzione, come prima
//     applica()                             // ③ fissa la baseline e ripristina
//   }
//
//   function resetForm() { form.value = defaultForm(); reset() }
//
// ⚠️ `applica()` va chiamata SEMPRE dopo la sostituzione, anche quando non
// c'è nulla da ripristinare: è lei a fissare la baseline per il confronto
// successivo. Saltarla lascerebbe la baseline vecchia e il giro dopo
// scambierebbe i dati del server per modifiche dell'operatore.
//
// PERCHÉ UNA BASELINE E NON UN FLAG "SPORCO"
// Il confronto è contro l'ultima forma RICEVUTA DAL SERVER: così un campo
// modificato e poi rimesso com'era non viene scambiato per una modifica da
// preservare. Un dirty-flag per campo direbbe «toccato», non «diverso».
//
// ⭐ «CI SONO MODIFICHE NON SALVATE?» (2026-09-26, ok Tid) — e' la stessa
// domanda, e ha la stessa risposta: il form e' diverso dalla fotografia.
// Il BB la espone come `modificato`, e con l'opzione `visibile` la dice alla
// content tab che ospita il drawer (`stores/tabs.js`, `segnalaModifiche`):
// pallino sulla tab, conferma alla chiusura, avviso sul cambio emittente.
//   const { preserva, reset, fissa, modificato, chiudiConConferma } =
//     useDrawerFormPreserve(form, { visibile: () => props.visible })
// ⭐ Chiudere il drawer con modifiche non salvate CHIEDE CONFERMA
//    (`chiudiConConferma(chiudi)`, 2026-09-26, Tid): e' li' che il lavoro si
//    perde. Con il drawer aperto il velo copre tab e topbar, quindi la
//    conferma della tab da sola non arrivava mai: il primo clic chiudeva il
//    drawer, in silenzio. Il drawer la mette su OGNI via d'uscita — X della
//    testata, Annulla, ESC, clic fuori (tutte passano da `update:visible`).
//    E `modificato` si passa a `<DrawerTitle>`: la scritta dell'azione
//    («Modifica») diventa arancio finche' c'e' qualcosa da salvare.
// ⚠️ `form` puo' essere un oggetto piatto o un ELENCO di righe (widget di una
//    dashboard, colonne di una lista): la fotografia e' una copia in
//    profondita', quindi anche una riga cambiata sul posto e' una modifica.
// ⚠️ `form` puo' essere anche un `computed` in sola lettura, quando il form
//    vive in un composable (reactive) o e' spezzato su piu' ref: `modificato`,
//    `fissa` e `chiudiConConferma` funzionano, `preserva` no (riscrive nel
//    form). Es. SoggettoDrawer, ClienteDrawer, IndirizzoDrawer.
// ⚠️ Senza fotografia (`reset()`, drawer in creazione non ancora salvato) non
//    c'e' niente da confrontare, e `modificato` e' false. Un drawer che vuole
//    contare anche la creazione chiama `fissa()` dopo aver preparato il form.
// ⚠️ A salvataggio riuscito si chiama `fissa()`: la fotografia deve dire
//    com'e' il documento adesso, o dopo il Salva la tab resterebbe «sporca».
//    Vale anche per chi POI ricarica con `preserva`: `fissa()` va chiamato
//    PRIMA della ricarica, o `preserva` prenderebbe i valori appena salvati
//    per modifiche pendenti e li rimetterebbe sopra quelli del server.
// ⭐ Due helper dello stesso modulo, per non riscrivere il cablaggio in ogni
//    drawer: `gestoreVisibile(emit, chiudi)` per `@update:visible`, e
//    `unisciFotografie(...)` quando le fotografie sono piu' d'una.

import { computed, getCurrentScope, onScopeDispose, ref, toRaw, unref, watch, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useTabsStore } from '../../stores/tabs'
import { useConfirmAction } from './useConfirmAction'

let sorgenti = 0

// Scopo: un campo vuoto e' vuoto comunque lo scriva il controllo (null,
//        undefined, stringa vuota o di soli spazi): svuotare un campo gia'
//        vuoto non e' una modifica.
function vuoto(v) {
  return v === null || v === undefined || (typeof v === 'string' && v.trim() === '')
}

// Scopo: copia IN PROFONDITA' del form per la fotografia. Una copia in
//        superficie condivideva gli oggetti annidati col form: una riga di un
//        elenco cambiata sul posto (`riga.visibile = false`) cambiava anche la
//        fotografia, e la modifica non si vedeva. Date copiate come date;
//        cio' che non e' dato semplice (funzioni, istanze) resta per
//        riferimento.
function copiaProfonda(v) {
  if (v instanceof Date) return new Date(v.getTime())
  if (Array.isArray(v)) return v.map(copiaProfonda)
  if (v && typeof v === 'object' && Object.getPrototypeOf(toRaw(v)) === Object.prototype) {
    const copia = {}
    for (const [k, x] of Object.entries(v)) copia[k] = copiaProfonda(x)
    return copia
  }
  return v
}

// Scopo: due valori di un campo dicono la stessa cosa? Un testo con uno
//        spazio in piu' in coda e' lo stesso testo (il backend lo salva
//        ripulito); una data riscelta uguale e' un oggetto nuovo con lo stesso
//        istante; un elenco o un oggetto si confrontano per contenuto.
// ⭐ Regola UNICA del «e' cambiato?»: la usano la fotografia di questo BB e
//    `useDrawerAutosaveBozza`. Due confronti diversi darebbero due risposte
//    diverse sullo stesso campo.
export function valoriUguali(a, b) {
  if (a === b) return true
  if (vuoto(a) && vuoto(b)) return true
  if (typeof a === 'string' && typeof b === 'string') return a.trim() === b.trim()
  if (a instanceof Date && b instanceof Date) return a.getTime() === b.getTime()
  if (a && b && typeof a === 'object' && typeof b === 'object') {
    return JSON.stringify(a) === JSON.stringify(b)
  }
  return false
}

// `form`    ref del form del drawer (oggetto piatto di valori)
// `ignora`  suffissi/chiavi da NON preservare. Default `_obj`: sono le
//           decorazioni di visualizzazione dei lookup (ragione sociale, codice)
//           che la ricarica ricostruisce dal server — preservarle terrebbe in
//           vita un'etichetta non più coerente con l'id accanto.
// `visibile` getter della visibilita' del drawer: se dato, la fotografia si
//           azzera alla chiusura, e `modificato` (a drawer aperto) si segnala
//           alla content tab che lo ospita.
export function useDrawerFormPreserve(form, { ignora = ['_obj'], visibile = null } = {}) {
  const serverForm = ref(null)

  // Scopo: azzera la baseline. Da chiamare nel resetForm del drawer: senza,
  //        riaprendo in CREATE si confronterebbe col documento precedente.
  function reset() {
    serverForm.value = null
  }

  function _daIgnorare(chiave) {
    return ignora.some((suffisso) => chiave.endsWith(suffisso))
  }

  // Scopo: fotografa ciò che diverge dalla baseline e restituisce la funzione
  //        da invocare DOPO la sostituzione del form.
  function preserva() {
    let pendenti = null
    if (serverForm.value && form.value) {
      const diff = {}
      for (const [k, v] of Object.entries(form.value)) {
        if (_daIgnorare(k)) continue
        if (!valoriUguali(v, serverForm.value[k])) diff[k] = v
      }
      if (Object.keys(diff).length) pendenti = diff
    }
    return function applica() {
      // Nuova baseline: com'è il documento SECONDO IL SERVER, prima che le
      // modifiche pendenti gli tornino sopra.
      serverForm.value = copiaProfonda(form.value)
      if (pendenti) Object.assign(form.value, pendenti)
    }
  }

  // Scopo: la fotografia diventa il form com'e' adesso. Dopo un caricamento
  //        che non passa da `preserva`, o un salvataggio senza ricarica.
  // ⛔ A drawer CHIUSO non fissa niente: la fotografia si azzera alla
  //    chiusura, e un `fissa()` arrivato dopo un `await` (fetch lenta, drawer
  //    chiuso nel frattempo) la rimetterebbe in vita col documento vecchio —
  //    all'apertura successiva il form nuovo risulterebbe «modificato».
  function fissa() {
    if (visibile && !visibile()) return
    serverForm.value = form.value ? copiaProfonda(form.value) : null
  }

  // Il form e' diverso dalla fotografia? Si guardano le chiavi di tutti e due:
  // un campo sparito dal form e' una differenza quanto uno cambiato.
  const modificato = computed(() => {
    const base = serverForm.value
    const attuale = form.value
    if (!base || !attuale) return false
    const chiavi = new Set([...Object.keys(base), ...Object.keys(attuale)])
    for (const k of chiavi) {
      if (_daIgnorare(k)) continue
      if (!valoriUguali(attuale[k], base[k])) return true
    }
    return false
  })

  // Scopo: chiude il drawer, chiedendo prima conferma se ci sono modifiche
  //        non salvate. `chiudi` e' cio' che il drawer faceva prima.
  let confirmAction = null
  let t = null
  function chiudiConConferma(chiudi) {
    // ⚠️ Prima si toglie il fuoco al campo: InputNumber scrive il v-model solo
    //    al blur, e ESC chiude il drawer col fuoco ancora dentro — il valore
    //    appena digitato non sarebbe ancora nel form, e si uscirebbe senza
    //    domanda. Il blur e' sincrono: `modificato` qui sotto lo vede gia'.
    togliFuoco()
    if (!modificato.value || !confirmAction) {
      chiudi()
      return
    }
    confirmAction({
      header: t('common.modifiche_non_salvate.titolo'),
      message: t('common.modifiche_non_salvate.messaggio'),
      acceptLabel: t('common.modifiche_non_salvate.chiudi'),
      onAccept: chiudi,
    })
  }

  if (visibile) {
    // La conferma serve solo a un drawer (chi passa `visibile`): il BB si usa
    // anche fuori da un setup, dove `useConfirm` non avrebbe il suo inject.
    confirmAction = useConfirmAction().confirmAction
    t = useI18n().t
    // ⛔ Alla CHIUSURA la fotografia si azzera. Il drawer e' un'istanza sola,
    //    riusata a ogni apertura, e il form conserva cio' che c'era: senza
    //    azzerare, la ricarica del documento successivo trovava la modifica
    //    ABBANDONATA sul precedente, la prendeva per «non salvato da
    //    preservare» e la rimetteva sopra il nuovo documento (difetto trovato
    //    il 2026-09-26 su ordini, DDT e preventivi, il cui ramo di modifica
    //    ricarica senza `resetForm`). Chiudere senza salvare vuol dire lasciare.
    watch(() => Boolean(visibile()), (aperto) => {
      if (!aperto) reset()
    })
    segnalaAllaTab(() => Boolean(visibile()) && modificato.value)
  }

  // La fotografia in sola lettura: per chi manda al server solo il DELTA
  // (GenericConfigDrawer), che prima ne teneva una copia propria.
  const fotografia = computed(() => serverForm.value)

  return { preserva, reset, fissa, modificato, chiudiConConferma, fotografia }
}

// Scopo: toglie il fuoco al campo attivo, perche' il suo valore arrivi nel
//        form prima di chiedersi «e' modificato?» (InputNumber scrive il
//        v-model solo al blur). Sincrono.
function togliFuoco() {
  if (typeof document !== 'undefined') document.activeElement?.blur?.()
}

// Scopo: il gestore di `@update:visible` del `<Drawer>` PrimeVue. ⭐ OGNI
//        uscita — X della testata, ESC, clic fuori — passa da `chiudi`, lo
//        STESSO dell'Annulla del footer: e' un gesto solo («esco»), e con due
//        gestori scritti a mano la X e l'Annulla finivano per emettere eventi
//        diversi (estratto 2026-09-26, regola del 2, ok Tid: era ricopiato in
//        ~50 drawer).
//   const suVisibile = gestoreVisibile(emit, chiudi)
//   <Drawer :visible="visible" @update:visible="suVisibile">
export function gestoreVisibile(emit, chiudi) {
  return (v) => (v ? emit('update:visible', true) : chiudi())
}

// Scopo: PIU' fotografie, UNA domanda. Un drawer con piu' form che si salvano
//        ciascuno per conto suo (testata + form inline, o un tab figlio con i
//        suoi Salva) chiude chiedendo conferma se ALMENO UNO e' modificato,
//        con un dialog solo — due conferme in fila sullo stesso ConfirmDialog
//        si pesterebbero. Estratto 2026-09-26 (regola del 2, ok Tid: era
//        scritto a mano in cinque drawer, in cinque forme diverse).
// `fonti`: istanze del BB, oppure getter di un figlio che le espone con
//          `defineExpose` (template ref: puo' essere ancora null).
//   const tutto = unisciFotografie(testata, inline, () => tabRef.value)
//   tutto.modificato            → per <DrawerTitle>
//   tutto.chiudiConConferma(fn) → per ogni uscita
export function unisciFotografie(...fonti) {
  const attive = () => fonti.map((f) => (typeof f === 'function' ? f() : f)).filter(Boolean)
  const modificato = computed(() => attive().some((f) => Boolean(unref(f.modificato))))
  function chiudiConConferma(chiudi) {
    togliFuoco()
    const sporca = attive().find((f) => unref(f.modificato))
    if (sporca) sporca.chiudiConConferma(chiudi)
    else chiudi()
  }
  return { modificato, chiudiConConferma }
}

// Scopo: tiene la content tab che ospita il drawer allineata a «ci sono
//        modifiche non salvate». La tab e' quella della rotta al montaggio: il
//        drawer vive nella view di quella tab (KeepAlive), anche quando
//        l'operatore passa a un'altra.
function segnalaAllaTab(sporco) {
  const tabs = useTabsStore()
  const path = useRoute()?.path
  if (!path) return
  const sorgente = `form-${++sorgenti}`
  const stop = watchEffect(() => tabs.segnalaModifiche(path, sorgente, sporco()))
  if (getCurrentScope()) {
    onScopeDispose(() => {
      stop()
      tabs.segnalaModifiche(path, sorgente, false)
    })
  }
}
