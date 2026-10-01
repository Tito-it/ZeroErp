// Scopo: building block "guard di versione" (token monotono) per scartare le
//        risposte asincrone stantie quando il contesto cambia piu' in fretta
//        del ritorno delle fetch. Unica primitiva per due scenari fino al
//        2026-06-05 biforcati in due composable gemelli (`useTokenedFetch`,
//        ritirato e fuso qui — regola del 2):
//
//   1. Drawer/lista fire-and-forget: una `api.fetch().then(...)` senza await
//      e l'utente cambia entita' (chiude/riapre il drawer su un id diverso)
//      prima che la prima risposta arrivi → le due Promise possono risolversi
//      in ordine inverso al lancio e la risposta "stantia" sovrascrive lo
//      stato fresco. Consumer: OffertaDrawer, PreventiviDrawer (fetch del
//      dettaglio; le revisioni passano dal guard dello store-lista).
//   2. Switch rapido di contesto su lookup/preview/list: cambio articolo o
//      cambio riga espansa mentre una fetch lenta e' ancora in volo. Consumer:
//      `useRigaComponenti` (lista componenti BoM), `useArticoloUomOptions`
//      (lookup UoM) e i drawer riga (preview).
//
// Pattern: ogni fetch cattura un tag monotono (`tag()`) prima dell'await; al
// ritorno il caller confronta col valore corrente (`isCurrent(tag)`) — se
// diverso e' partita una fetch piu' nuova nel frattempo, la risposta va
// scartata. `invalidate()` bumpa il contatore senza emettere una nuova fetch
// (reset/cleanup: es. cambio riga padre svuota la lista e impedisce a risposte
// vecchie di ripopolarla).
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
// Chi preferisce il nome `nextToken` (semantica scenario 2) puo' aliasare in
// destructuring: `const { tag: nextToken, isCurrent, invalidate } = useFetchVersion()`.
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
