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

import { ref } from 'vue'

// `form`    ref del form del drawer (oggetto piatto di valori)
// `ignora`  suffissi/chiavi da NON preservare. Default `_obj`: sono le
//           decorazioni di visualizzazione dei lookup (ragione sociale, codice)
//           che la ricarica ricostruisce dal server — preservarle terrebbe in
//           vita un'etichetta non più coerente con l'id accanto.
export function useDrawerFormPreserve(form, { ignora = ['_obj'] } = {}) {
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
        if (v !== serverForm.value[k]) diff[k] = v
      }
      if (Object.keys(diff).length) pendenti = diff
    }
    return function applica() {
      // Nuova baseline: com'è il documento SECONDO IL SERVER, prima che le
      // modifiche pendenti gli tornino sopra.
      serverForm.value = { ...form.value }
      if (pendenti) Object.assign(form.value, pendenti)
    }
  }

  return { preserva, reset }
}
