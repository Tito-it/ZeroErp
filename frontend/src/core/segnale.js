// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ IL SEGNALE — un elenco di ascoltatori vivi a cui qualcuno, senza
//        conoscerli, consegna qualcosa (o chiede di fare qualcosa). E' la
//        forma di `chiudiTuttiIDrawer` (ogni drawer registra come si chiude)
//        e di `adottaTestataPresidi` (ogni pallino registra come adotta una
//        testata letta altrove).
//
//        Estratto il 2026-09-26 alla seconda occorrenza (regola del 2, ok
//        Tid): la seconda copia era nata SENZA le due protezioni della prima,
//        che qui stanno una volta sola.
//
// ⚠️ `emetti` itera su una COPIA, cioe' sugli ascoltatori vivi AL MOMENTO
//    dell'emissione. Un ascoltatore puo' montare un componente che si
//    registra mentre il ciclo gira: sul Set vivo il nuovo verrebbe chiamato
//    nello stesso giro, e uno che si ri-registra (smonta e rimonta) terrebbe
//    il ciclo aperto per sempre.
// ⚠️ Ogni ascoltatore e' ISOLATO: se uno solleva, gli altri partono comunque.
//    Un segnale non fallisce: e' un avviso, non un'operazione.
// ⚠️ Dentro uno scope reattivo (setup, `effectScope`) l'ascoltatore si
//    de-registra da solo allo smontaggio: su una view KeepAlive che monta e
//    smonta a ripetizione, restare nel Set sarebbe una perdita che cresce.
// ------------------------------------------------------------
import { getCurrentScope, onScopeDispose } from 'vue'

// Scopo: crea un segnale con nome (il nome compare solo nei log).
export function creaSegnale(nome) {
  // Set e non array: la stessa funzione non si registra due volte, e la
  // rimozione non ha da cercare indici.
  const ascoltatori = new Set()

  return Object.freeze({
    // Scopo: registra un ascoltatore. Ritorna la de-registrazione manuale,
    //        per chi non ha uno scope.
    ascolta(fn) {
      ascoltatori.add(fn)
      const rimuovi = () => ascoltatori.delete(fn)
      if (getCurrentScope()) onScopeDispose(rimuovi)
      return rimuovi
    },
    // Scopo: chiama tutti gli ascoltatori vivi con gli argomenti dati.
    emetti(...args) {
      // Snapshot, non il Set vivo (vedi sopra). In una costante perche' lo
      // spread dentro il `for…of` e' indistinguibile, per il linter, da una
      // copia inutile — qui e' il punto della funzione.
      const daChiamare = Array.from(ascoltatori)
      for (const fn of daChiamare) {
        try {
          fn(...args)
        } catch (e) {
          console.warn(`segnale «${nome}»: un ascoltatore ha sollevato`, e)
        }
      }
    },
  })
}
