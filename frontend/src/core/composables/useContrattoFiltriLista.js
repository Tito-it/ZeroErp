// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL CONTRATTO CHE UNA LISTA OFFRE AI SUOI FILTRI — chi sono i filtri di
//        quella lista (`chiaviFiltro`), che valore avevano alla nascita
//        (`filtriDefault`) e come ci si torna (`azzeraFiltri`). Sono le tre
//        cose che `FiltriLista` legge per accendere il segno dei filtri attivi
//        e per «Pulisci filtri».
// Note: ⭐ ESTRATTO DA `useListaStoreCore` IL 2026-09-23 (regola del 2, ok Tid),
//        e il core stesso lo consuma: non e' una seconda copia delle tre righe,
//        e' la loro UNICA sede. La ragione e' l'adozione (lotto L2 del brief dei
//        filtri compatti): quattordici liste vere — distinte, eccedenze, rate
//        fuori capienza, coda righe e canali d'incasso dei pagamenti, le code
//        resi, i lotti, i fondi fattura, le definizioni di workflow, le
//        impostazioni, i due cruscotti — hanno lo store scritto a mano su
//        `useListaEmptyStateFetch` e quindi NON dichiarano i filtri.
//
//       ⛔ L'ALTERNATIVA ERA IL CONTEGGIO NELLE VIEW (`:segno` calcolato dal
//        chiamante), ed e' proprio cio' che il brief vieta: sarebbe una seconda
//        sede dello stato dei filtri, che diverge al primo filtro aggiunto —
//        e una lista che «dimentica» di contare direbbe «nessun filtro» mentre
//        filtra, senza nessun errore.
//       ⭐ Il contratto e' di TRE MEMBRI, non dell'intero `useListaStoreCore`:
//        uno store a mano lo adotta in tre righe, senza cedere il proprio
//        `buildParams` (che per quelle liste diverge davvero — code di lavoro
//        senza pavimento temporale, nomi sul filo propri).
//
//       ⚠️ `fetchList` si passa GIA' DEFINITA: qui si tiene il riferimento, e
//        uno store che chiamasse questo composable prima di dichiararla
//        prenderebbe `undefined` (o una TDZ, se e' una `const`). In
//        `useListaStoreCore` la funzione e' una dichiarazione — quindi issata —
//        e negli store a mano arriva da `useListaEmptyStateFetch`, che si
//        destruttura prima.
//
//       Brief: docs/it/dev/work-done/brief-fe-filtri-lista-su-schermo-compatto.md
// ------------------------------------------------------------

import { clonaFiltri, clonaValore, congelaProfondo } from '../utils/clonaFiltri'

// Params:
//   - filters: il `ref` dei filtri della lista (la sede unica dello stato).
//   - filterDefaults: i filtri DI DOMINIO col loro valore di nascita. ⛔ Non
//       `search`/`limit`/`offset`/`order_*`: la ricerca non e' un filtro (D2) e
//       la paginazione non restringe niente — contarle accenderebbe il segno su
//       una lista intera.
//   - filtriNeutri: i VALORI CHE NON RESTRINGONO, quando non sono `null`
//       (`{ solo_ultima_revisione: false }`, `{ ambito: 'tutti' }`). ⛔ Senza,
//       il segno conta un filtro che sta ALLARGANDO la lista: il perche' per
//       intero sta su `segnoFiltri`.
//   - fetchList: la rilettura della lista dopo «Pulisci filtri».
export function useContrattoFiltriLista({
  filters, filterDefaults = {}, filtriNeutri: neutri = {}, fetchList,
}) {
  // ⚠️ Una COPIA congelata, non `filterDefaults`: l'oggetto e' un letterale del
  //    chiamante, e un consumatore che vi scrivesse dentro cambierebbe i default
  //    di uno store vivo — cioe' il metro insieme alla cosa misurata.
  // ⛔ E la copia e' PROFONDA, non uno spread: con un default ad array lo spread
  //    condivide il riferimento e `Object.freeze` di primo livello non ferma una
  //    `push`. Il perche' sta una volta sola, su `clonaFiltri`.
  const chiaviFiltro = Object.freeze(Object.keys(filterDefaults))
  const filtriDefault = congelaProfondo(clonaFiltri(filterDefaults))
  const filtriNeutri = congelaProfondo(clonaFiltri(neutri))

  // ⛔ FAIL-VISIBLE, stesso stampo del guard di `FiltriLista` e del gemello
  //    `useContrattoFiltriLocali`: un neutro dichiarato su una chiave che NON e'
  //    un filtro e' un no-op silenzioso — il refuso non fallisce, semplicemente
  //    il segno continua a contare il filtro che si voleva zittire. E' la forma
  //    del difetto gia' visto nel drawer BoM, dove una chiave stava nei valori
  //    e non nell'elenco delle chiavi.
  // ⚠️ Qui il controllo e' possibile perche' le due sedi sono separate; nel
  //    gemello locale non serve, perche' li' `neutro` sta sulla riga del filtro
  //    e una chiave sbagliata non esiste.
  const neutriSconosciuti = Object.keys(filtriNeutri).filter((k) => !chiaviFiltro.includes(k))
  if (neutriSconosciuti.length) {
    console.error(
      `[useContrattoFiltriLista] \`filtriNeutri\` dichiara ${neutriSconosciuti.join(', ')}, `
      + 'che non sono filtri di questa lista (non stanno in `filterDefaults`): '
      + 'la riga non fa niente e il segno continua a contare il filtro vero.',
    )
  }

  // Scopo: «Pulisci filtri» — riporta i SOLI filtri di dominio al loro default,
  //        torna a pagina 1 e rilegge la lista.
  // ⛔ NON e' `reset()`, e la differenza non e' cosmetica: quello azzera anche
  //    il padre, cioe' su una lista dentro un drawer scollegherebbe la lista dal
  //    documento che la ospita — a video resterebbe vuota, senza errori, e la
  //    causa non somiglierebbe al gesto.
  // ⚠️ La ricerca NON si tocca (D2): «pulisci filtri» non e' «annulla la
  //    ricerca». Chi vuole svuotare la casella la svuota.
  // ⚠️ I compagni `<chiave>_obj` di `bindLookup` non si azzerano qui: il watch
  //    del binder li butta quando l'id diventa `null`, e al rimonto
  //    `ricordato()` li rifiuta perche' l'id non corrisponde piu'. Toccarli
  //    sarebbe una seconda sede della stessa pulizia.
  // ⚠️ `offset` si azzera solo se la lista ce l'ha: esistono elenchi senza
  //    paginazione (le definizioni di workflow, che si leggono tutte in un
  //    colpo) e scriverci dentro una chiave che non hanno significherebbe
  //    inventare un parametro che nessuno manda e nessuno legge.
  function azzeraFiltri() {
    // ⚠️ Si riassegna una COPIA, non il valore congelato: un default ad array
    //    finirebbe nei filtri vivi per riferimento, e il primo widget che ci
    //    scrive dentro muterebbe il metro (e la scrittura su un oggetto
    //    congelato solleverebbe in strict mode).
    for (const k of chiaviFiltro) filters.value[k] = clonaValore(filtriDefault[k])
    if ('offset' in filters.value) filters.value.offset = 0
    return fetchList()
  }

  return { chiaviFiltro, filtriDefault, filtriNeutri, azzeraFiltri }
}
