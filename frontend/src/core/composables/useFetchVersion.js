// Scopo: building block "guard di versione" per fetch asincroni fire-and-forget.
//
// Problema risolto: quando un drawer/lista lancia una `api.fetch().then(...)`
// senza await e l'utente cambia entita' (es. chiude/riapre il drawer su un
// id diverso) prima che la prima risposta arrivi, le due Promise possono
// risolversi in ordine inverso al lancio → la risposta "stantia" sovrascrive
// lo stato fresco. Risultato visibile: dati del record precedente in quello
// nuovo per il tempo che intercorre fino al ritorno della seconda risposta.
//
// Pattern duplicato in OffertaDrawer (fgVersion), ContrattoRigheDrawer
// (fgVersion) e introdotto su PreventiviDrawer per la tab Revisioni. La
// regola del 2 (`feedback_regola_del_2_estrai_bb`) richiede l'estrazione
// alla seconda occorrenza: questo composable la centralizza.
//
// Uso tipico in un drawer/lista:
//
//   const fv = useFetchVersion()
//
//   async function loadDetail() {
//     const t = fv.tag()                // marca questa chiamata
//     const data = await api.fetch()
//     if (!fv.isCurrent(t)) return      // arrivata in ritardo, scarta
//     state.value = data
//   }
//
//   watch(visible, v => {
//     if (!v) fv.invalidate()           // invalidate cancella tutte le call
//   })                                  // in volo (qualunque tag !== current)
//
// Nota: non e' un ref reattivo. Il valore vive in una closure `let` e serve
// solo per il confronto async (no rendering). Volutamente piu' snello di
// `ref(0)` per evitare reattivita' inutile.

export function useFetchVersion() {
  let _v = 0
  return {
    // Scopo: marca una nuova call asincrona, ritorna il tag da usare nel guard.
    tag: () => ++_v,
    // Scopo: vero se `t` corrisponde alla call piu' recente (non scartare).
    isCurrent: (t) => t === _v,
    // Scopo: invalida tutte le call in volo (chiusura drawer, cambio entita').
    // Equivalente a `tag()` ma piu' espressivo quando il valore non serve.
    invalidate: () => { _v++ },
  }
}
