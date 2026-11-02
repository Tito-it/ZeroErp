// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LO STESSO CONTRATTO DEI FILTRI, PER UNA SUPERFICIE SENZA STORE-LISTA —
//        chi sono i filtri, che valore hanno per default, come ci si torna e
//        che segno mostrano. Qui lo stato non sta in un oggetto `filters`: sta
//        in `ref` (del componente o di uno store scritto a mano).
// Note: ⭐ REGOLA DEL 2 (ok Tid, 2026-09-23, rilettura critica del cantiere
//        filtri). Le CINQUE superfici che passano `:segno` a `FiltriLista` — i
//        due cruscotti (backlog, situazione aperta), il riepilogo permessi, il
//        drawer BoM e le tre sotto-liste del drawer lotto — scrivevano l'elenco
//        dei filtri TRE VOLTE nella stessa chiamata a `segnoFiltri` (l'oggetto
//        dei valori, l'array delle chiavi, l'oggetto dei default), piu' un
//        `pulisciFiltri()` a mano che ripeteva i default una QUARTA volta.
//
//       ⛔ E LA TERZA SEDE SI DIMENTICA IN SILENZIO: in `ArticoloBomDrawer` una
//        chiave stava gia' nell'oggetto dei valori e NON nell'array delle
//        chiavi. Li' era innocuo (era la ricerca, che per D2 non e' un filtro),
//        ma e' esattamente la forma in cui il difetto nasce — un filtro che
//        c'e' e non viene contato e' un segno spento su una superficie che
//        filtra, cioe' la cosa che questo cantiere esiste per impedire.
//
//       ⭐ LA SEDE DIVENTA UNA: chiave, `ref` e default stanno sulla STESSA
//        riga. Chi aggiunge un filtro non ha niente da tenere allineato, e chi
//        ne toglie uno non lascia indietro meta' dichiarazione.
//
//       ⛔ E IL DEFAULT SI DICHIARA SEMPRE, non si fotografa dal `ref` alla
//        chiamata — ed e' una correzione fatta in corsa, perche' la prima
//        stesura lo fotografava. Per un `ref` del componente le due cose
//        coincidono; per un `ref` di uno STORE no: i filtri dei due cruscotti
//        vivono in uno store `userScoped` che SOPRAVVIVE al componente, quindi
//        al secondo montaggio la «nascita» avrebbe fotografato il valore che
//        l'operatore aveva lasciato — numero grigio invece che blu, e «Pulisci»
//        che riporta al filtro di prima invece che al default. Nessun errore,
//        e invisibile finche' non ci si torna sopra due volte.
//        ⭐ E' la stessa regola dei filtri di uno store-lista: `filterDefaults`
//        e' un LETTERALE dichiarato, mai una lettura dello stato corrente.
//
//       ⭐ UN `rif` PUO' ESSERE UN `computed` SCRIVIBILE, ed e' cio' che serve
//        quando il filtro vero non coincide con la variabile del widget: il
//        «mostra tutto» del giornale lotto ALLARGA invece di restringere, quindi
//        il filtro da contare e' il suo opposto («solo problemi»). Contare la
//        variabile del widget direbbe «1 filtro attivo» proprio quando non ne
//        e' attivo nessuno.
//
//       Brief: docs/it/dev/work-done/brief-fe-filtri-lista-su-schermo-compatto.md
// ------------------------------------------------------------

import { computed } from 'vue'

import { clonaValore, congelaProfondo } from '../utils/clonaFiltri'
import { segnoFiltri } from '../utils/segnoFiltri'

// Params:
//   - filtri: `{ <chiave>: { rif, default, neutro? } }` — i filtri DI DOMINIO
//       di questa superficie, uno per riga.
//       ⭐ `neutro` e' il valore che NON RESTRINGE, quando non e' `null`: senza,
//       il segno conta un filtro proprio quando l'operatore ha ALLARGATO la
//       lista (`ampiezza: 'TUTTI'` dei task del lotto, che a DB non filtra
//       niente). Stessa opzione, stesso nome e stesso perche' di `filtriNeutri`
//       sugli store-lista — il dettaglio sta su `segnoFiltri`.
//       ⛔ Non ci va la ricerca (D2) ne' la paginazione: contarle accenderebbe
//       il segno su una superficie intera.
//       ⭐ Il default puo' essere una FUNZIONE quando si ricalcola: «oggi» non
//       e' un valore, e' una domanda. Il drawer BoM filtra «valido al» e nasce
//       su oggi; tenuto come istante fisso, un'applicazione aperta a cavallo
//       della mezzanotte confronterebbe il filtro di oggi col metro di ieri e
//       mostrerebbe il numero in blu invece che in grigio — o, peggio, terrebbe per
//       «default» un giorno che e' passato.
//       ⚠️ La funzione deve tornare un valore STABILE dentro la giornata
//       (`addDaysToToday(0)`, mezzanotte locale) e non l'istante corrente: due
//       `new Date()` a millisecondi di distanza non sono uguali per il segno, e
//       il numero non sarebbe mai grigio.
//   - onAzzera: che cosa fare dopo «Pulisci filtri» (rileggere, ricaricare).
//       ⚠️ Opzionale: le tre sotto-liste del drawer lotto ricaricano da se',
//       con un `watch` sul filtro.
export function useContrattoFiltriLocali(filtri, { onAzzera = null } = {}) {
  const chiaviFiltro = Object.freeze(Object.keys(filtri))

  // ⛔ FAIL-VISIBLE, stesso stampo del guard di `FiltriLista`: una voce senza
  //    `rif` non fa fallire niente — il segno conterebbe `undefined`, cioe'
  //    «nessun filtro» su una superficie che filtra. L'operatore non puo'
  //    accorgersene; chi sviluppa si', se glielo si dice.
  const senzaRif = chiaviFiltro.filter((k) => !filtri[k] || !('rif' in filtri[k]))
  if (senzaRif.length) {
    console.error(
      `[useContrattoFiltriLocali] i filtri ${senzaRif.join(', ')} non dichiarano `
      + '`rif`: ogni voce e\' `{ rif, default }`, e senza `rif` il segno resta '
      + 'spento mentre la superficie filtra.',
    )
  }

  // Scopo: il metro di UN filtro, risolto adesso — staccato (la ragione sta su
  //        `clonaFiltri`: un default ad array condiviso per riferimento si
  //        sposta insieme alla cosa misurata) e congelato in profondita'.
  function risolviDefault(k) {
    const d = filtri[k]?.default
    return congelaProfondo(clonaValore(typeof d === 'function' ? d() : (d ?? null)))
  }

  // Scopo: i valori correnti, nella forma che `segnoFiltri` legge.
  const valori = computed(
    () => Object.fromEntries(chiaviFiltro.map((k) => [k, filtri[k]?.rif?.value])),
  )

  // Scopo: il metro INTERO, risolto adesso.
  // ⛔ E' una FUNZIONE, non un valore ne' una `computed`, ed e' la correzione
  //    che la spec ha trovato in giornata: una `computed` senza dipendenze
  //    reattive — e un default a funzione non ne ha — si calcola UNA volta e
  //    resta cachizzata per sempre. Sarebbe stata di nuovo una fotografia, con
  //    in piu' l'aria di non esserlo.
  // ⚠️ Qui l'asimmetria con `useContrattoFiltriLista.filtriDefault` (che e' un
  //    oggetto) e' nella NATURA della cosa, non nello stile: li' i default sono
  //    un letterale, qui possono essere una domanda.
  function risolviFiltriDefault() {
    return congelaProfondo(Object.fromEntries(chiaviFiltro.map((k) => [k, risolviDefault(k)])))
  }

  // I valori neutri, dichiarati riga per riga accanto al filtro.
  // ⛔ COPIA PROFONDA E CONGELATA, come i default e per la stessa ragione: il
  //    valore arriva da un letterale del chiamante, e con un neutro ad array
  //    `Object.freeze` di primo livello non ferma una `push` — il metro si
  //    sposterebbe insieme alla cosa misurata. E' la simmetria che mancava col
  //    gemello sugli store-lista (`useContrattoFiltriLista`), che ci passava
  //    gia' da `clonaFiltri`.
  const filtriNeutri = congelaProfondo(Object.fromEntries(
    chiaviFiltro
      .filter((k) => 'neutro' in (filtri[k] ?? {}))
      .map((k) => [k, clonaValore(filtri[k].neutro)]),
  ))

  // ⚠️ Il metro si risolve DENTRO la computed del segno, cosi' un default a
  //    funzione («oggi») viene richiesto di nuovo a ogni ricalcolo.

  const segno = computed(
    () => segnoFiltri(valori.value, chiaviFiltro, risolviFiltriDefault(), filtriNeutri),
  )

  // Scopo: «Pulisci filtri» — i filtri tornano al loro default dichiarato.
  // ⚠️ Si riassegna una COPIA del default, mai il default congelato.
  function azzeraFiltri() {
    for (const k of chiaviFiltro) {
      if (filtri[k]?.rif) filtri[k].rif.value = clonaValore(risolviDefault(k))
    }
    return onAzzera ? onAzzera() : undefined
  }

  return { chiaviFiltro, risolviFiltriDefault, filtriNeutri, valori, segno, azzeraFiltri }
}
