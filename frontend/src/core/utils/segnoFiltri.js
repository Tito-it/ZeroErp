// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL SEGNO DEI FILTRI ATTIVI di una lista, in una funzione PURA: dai
//        filtri correnti + le chiavi dichiarate dallo store + i loro default,
//        ai tre stati che `FiltriLista` disegna (decisione D4 di Tid,
//        2026-09-22).
// Note: ⛔ Nessun import, di proposito: e' il modulo che ha la spec, e un
//        import dal componente trascinerebbe store, i18n e PrimeVue nel test.
//        Stesso pattern di `pallinoPresidi.js` e `ramoBannerLotto.js`.
//
//       ⭐ PERCHE' ESISTE. Quando i filtri non sono piu' sempre a video (sotto
//       i 1024px stanno in un drawer), una lista RISTRETTA e una lista VUOTA
//       si assomigliano: l'operatore attribuisce il buco al sistema («il
//       documento non c'e'») invece che al filtro. Il segno e' cio' che
//       distingue le due cose, e per questo i DEFAULT contano: `data_da` a
//       «oggi-60gg al primo del mese» restringe esattamente come un filtro
//       scelto a mano — che nessuno l'abbia digitato non lo rende meno vero.
//
//       ⚠️ I DUE STATI «CON VALORE» NON SONO UN VEZZO: con i default dentro
//       il conteggio quasi ogni lista mostrerebbe un segno SEMPRE, e un segno
//       sempre acceso smette di essere un segno. Cio' che separa «ristretta
//       come nasce» da «ristretta da te» e' il COLORE del numero — grigio e
//       blu. ⛔ Dal 2026-09-23, e prima era la FORMA: lo stato «tutto al
//       default» era un pallino senza numero, e lo stesso filtro valeva zero
//       un istante e uno quello dopo («0 → 2» toccando una cosa sola,
//       rilievo in-app di Tid). Il conteggio non e' mai cambiato: la forma lo
//       nascondeva.
//
//       ⛔ MA IL GRIGIO NON COPRE I DEFAULT RISOLTI A RUNTIME, E NON E' UN
//       DIFETTO DA CORREGGERE (decisione D9 di Tid, 2026-09-22). `defaults` e'
//       il letterale `filterDefaults` dello store, cioe' la fotografia scattata
//       alla NASCITA della lista: un default che arriva dopo il mount —
//       `UtilityPerRuoloSelect apply-default`, che risolve la catena
//       utente→gruppo→emittente e scrive `utility_id` a lista gia' montata —
//       li' dentro non c'e', quindi esce `modificato` e il numero si vede BLU.
//       ⭐ La regola e' UNA: *si contano sempre i filtri, default compresi*.
//       L'eccezione non starebbe in piedi da sola — se un default risolto tardi
//       dovesse tornare nel grigio, il caso gemello (l'operatore che SVUOTA un
//       filtro di default) vorrebbe la regola opposta, e il conteggio
//       risponderebbe a due domande diverse a seconda di come il valore ci e'
//       arrivato. Il numero resta VERO comunque: dice quante cose stanno
//       restringendo l'elenco.
//       ⇒ Chi arriva qui per «sistemare» il caso `apply-default` si fermi: e'
//       gia' stato deciso. Brief §2.3.
//
//       Brief: docs/it/dev/work-done/brief-fe-filtri-lista-su-schermo-compatto.md
// ------------------------------------------------------------

export const SEGNO_VUOTO = 'vuoto'
export const SEGNO_DEFAULT = 'default'
export const SEGNO_MODIFICATO = 'modificato'

// Scopo: il valore «assente» in UNA definizione. `null`, `undefined` e stringa
//        vuota sono la stessa cosa per un filtro (una Select svuotata scrive
//        `null`, una casella di testo `''`), mentre `false` e `0` sono valori
//        LEGITTIMI — «solo i disattivati», «quantita' zero».
// ⚠️ E' la stessa regola di `paramsFiltro` in `useListaStoreCore` (`!= null`),
//    allargata alla stringa vuota: mandare `''` sul filo non filtra niente, e
//    contarlo come filtro attivo accenderebbe il segno su una lista intera.
function assente(v) {
  return v == null || v === ''
}

// Scopo: confronto fra il valore corrente e il suo default.
// ⚠️ Non e' un `===` secco: un filtro puo' portare un ARRAY (una multi-select)
//    o un oggetto, e due array uguali non sono lo stesso riferimento — un
//    `===` direbbe «modificato» su un default mai toccato, cioe' un numero blu
//    al posto di uno grigio, senza che nulla fallisca.
function uguale(a, b) {
  if (assente(a) && assente(b)) return true
  if (assente(a) || assente(b)) return false
  if (typeof a === 'object' || typeof b === 'object') {
    return JSON.stringify(a) === JSON.stringify(b)
  }
  return a === b
}

// Scopo: IL SEGNO, in una funzione pura. Tre stati che, sbagliati, non
//        falliscono — mostrano il segno sbagliato — e per questo hanno una
//        spec con un caso ciascuno.
//        · nessun filtro con valore        → `vuoto`: niente a video. La lista
//                                            non e' ristretta, e un segno
//                                            direbbe il falso;
//        · filtri con valore, TUTTI al
//          loro default                     → `default`: numero in GRIGIO;
//        · almeno uno diverso dal default   → `modificato`: numero in BLU.
//
//        `conteggio` e' SEMPRE quanti filtri stanno limitando la lista,
//        default compresi — risponde a «quante cose restringono questo
//        elenco?», non a «quante ne ho toccate io». Con `data_da` al default
//        piu' uno stato scelto vale **2**, ed e' giusto: sono due.
//
// ⛔ `chiavi` le DICHIARA lo store (`filterDefaults`), non le indovina questa
//    funzione: `search`, `limit`, `offset` e l'ordinamento non sono filtri, e i
//    compagni `<chiave>_obj` di `bindLookup` non sono nemmeno nell'elenco.
//    Passare `Object.keys(filtri)` sarebbe un segno che si accende sulla
//    paginazione.
//
// ⚠️ Con `chiavi` vuoto il risultato e' `vuoto`: una lista senza filtri
//    dichiarati non ha niente da segnalare. Chi passa uno store che NON
//    dichiara le chiavi e' un difetto muto — lo dice `FiltriLista`, che ha la
//    console per farlo (qui non si stampa: e' una funzione pura).
//
// ⭐ `neutri` — I VALORI CHE NON RESTRINGONO, e vanno DICHIARATI (2026-09-23,
//    rilievo in-app di Tid). Questa funzione sapeva riconoscerne uno solo:
//    l'assenza (`null`/`''`). Per quasi tutti i filtri basta, ma non per quelli
//    il cui «tutto» e' un valore VERO che deve viaggiare sul filo:
//
//      · `solo_ultima_revisione: false` (offerte, preventivi) — il backend e'
//        `qp_bool(..., default=True)`, quindi «assente» significa «solo
//        l'ultima»: il `false` di «mostra storico» va mandato per forza;
//      · `ambito: 'tutti'` (code di lavoro) — sul filo il parametro parte SOLO
//        quando vale «tutti», quindi il verso e' rovesciato rispetto al dominio;
//      · `ampiezza: 'TUTTI'` (task del lotto) — una `ref` che non va sul filo.
//
//    ⛔ Senza, il numero SALE quando l'operatore ALLARGA la lista, ed e' il
//    verso sbagliato: «mostra storico» acceso non restringe niente e contava 1.
//    E' lo stesso difetto del «mostra tutto» del giornale del lotto, che li' si
//    e' potuto curare con un `computed` perche' la superficie non ha uno store.
//    ⭐ Si DICHIARA nello store, accanto ai `filterDefaults`, come `paramNames`
//    e `gateKeys`: e' conoscenza del filtro, non della funzione che lo conta.
//
// ⚠️ `neutri` tocca il CONTEGGIO, non `modificato`: scegliere il valore neutro
//    resta una scelta dell'operatore, e finche' QUALCOS'ALTRO restringe il
//    colore lo dice (numero blu su una lista che nasceva grigia).
// ⛔ MA QUANDO IL CONTEGGIO ARRIVA A ZERO IL SEGNO SPARISCE, `modificato` o no,
//    e non e' una svista: il segno risponde a «quante cose restringono questo
//    elenco?», e su un elenco intero la risposta e' «nessuna». Un numero in blu
//    su una lista completa direbbe il falso, ed e' esattamente il difetto che
//    questo parametro e' nato per togliere. ⇒ Accendere «mostra storico» su una
//    lista dove e' il solo filtro TOGLIE il segno: e' giusto.
//
// ⭐ ED E' PER QUESTO CHE `modificato` ESCE, e non e' un di piu' (2026-09-23):
//    lo stato `vuoto` risponde «niente restringe», che e' un'altra domanda da
//    «c'e' qualcosa da riportare al default?». Le due divergono proprio nel caso
//    nuovo — un filtro portato al valore neutro, o un default svuotato a mano:
//    li' non c'e' nessun segno da mostrare, ma «Pulisci filtri» ha eccome
//    qualcosa da fare. 🔴 Senza questa uscita il verbo si spegne insieme al
//    segno, cioe' proprio quando serve, e da desktop non si vede nemmeno
//    (il pulsante vive nel drawer compatto).
export function segnoFiltri(filtri, chiavi, defaults = {}, neutri = {}) {
  const f = filtri ?? {}
  const elenco = chiavi ?? []
  const neutro = neutri ?? {}
  let conteggio = 0
  let modificato = false
  for (const k of elenco) {
    const restringe = !assente(f[k]) && !(k in neutro && uguale(f[k], neutro[k]))
    if (restringe) conteggio += 1
    if (!uguale(f[k], defaults[k])) modificato = true
  }
  if (conteggio === 0) return { stato: SEGNO_VUOTO, conteggio: 0, modificato }
  return {
    stato: modificato ? SEGNO_MODIFICATO : SEGNO_DEFAULT,
    conteggio,
    modificato,
  }
}
