// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La scheda attiva di una vista a tab, pilotabile da fuori con `?tab=`.
// Note: estratto 2026-09-04 (regola del 2, ok Tid) da CodeLavoroView +
//       UnitaMisuraView, che lo avevano scritto identico.
// ------------------------------------------------------------
import { ref, watch, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'

// ── Perche' un BB e non due copie ────────────────────────────────────────────
//
// Il blocco e' corto, ma porta dentro TRE cose che si dimenticano — e che nella
// prima stesura delle due copie erano sbagliate o assenti in almeno una:
//
//  1. ⛔ **il guard sulla propria rotta.** Sotto KeepAlive i watcher di una
//     vista restano vivi anche quando la vista non e' a video: senza il
//     controllo, una vista in cache reagisce a un `?tab=` diretto a un'ALTRA
//     schermata e la `replace` qui sotto ripulisce una query che non e' sua —
//     l'altra vista si apre sulla scheda sbagliata, senza errori, e te ne
//     accorgi solo tornandoci. ⚠️ Guardare i soli VALORI ammessi non basta: due
//     vocabolari disgiunti lo sono per caso, non per costruzione.
//  2. ⚠️ **servono ENTRAMBI `watch` e `onActivated`**, e nessuno dei due copre
//     l'altro: `onActivated` prende l'arrivo da un'altra rotta (la vista vive
//     sotto KeepAlive con `:key="$route.path"`, quindi un deep-link su una
//     vista gia' in cache non rimonta niente — [[feedback_keepalive_onactivated]]);
//     il `watch` prende il caso in cui si e' GIA' sulla pagina e cambia solo la
//     query (path invariato ⇒ nessuna riattivazione).
//  3. ⚠️ **la query si pulisce dopo l'uso.** Lasciarla ri-forzerebbe la scheda a
//     ogni ritorno sulla vista, anche dopo che l'operatore ne ha scelta
//     un'altra a mano. La `replace` ri-scatena il watch con il parametro
//     assente, che esce subito dalla guardia: e' idempotente per costruzione.
//
// ⛔ Non scrive MAI la query quando l'operatore cambia scheda a mano: `?tab=` e'
//    un ingresso, non lo specchio dello stato. Scriverlo farebbe di ogni click
//    sui tab una voce nella cronologia del browser.

// Scopo: ritorna il ref della scheda attiva, da legare a `v-model:value` dei
//        `Tabs`, applicando il deep-link `?tab=` quando arriva.
// @param {string}          nomeRotta  nome della rotta che possiede questa vista
// @param {object|string[]} ammessi    i valori validi (l'enum delle schede)
// @param {string}          [iniziale] scheda di partenza (default: il primo)
// @param {string}          [parametro='tab'] nome del query param
// @param {boolean}         [ripartiDaIniziale=false] chi rientra nella vista
//                          trova la scheda iniziale, non quella dell'ultima
//                          visita (il deep-link `?tab=` vince comunque).
// ⭐ `ripartiDaIniziale` (Tid 2026-10-24, Processi automatici): sotto KeepAlive
//    la vista resta in cache e conserva la scheda; per una vista che ha una
//    scheda «di casa» chi entra se la aspetta.
// ⛔ Si torna all'iniziale all'USCITA (`onDeactivated`), non all'ingresso: un
//    deep-link verso la vista in cache lo applica il `watch` (la rotta cambia
//    prima della riattivazione) e la query e' gia' pulita quando arriva
//    `onActivated` — che, azzerando li', annullerebbe la scheda appena chiesta.
export function useTabDaQuery({ nomeRotta, ammessi, iniziale, parametro = 'tab', ripartiDaIniziale = false }) {
  const route = useRoute()
  const router = useRouter()
  const valori = Array.isArray(ammessi) ? ammessi : Object.values(ammessi)

  // ⚠️ Un valore iniziale fuori dall'enum non fallisce: `Tabs` non trova il
  //    pannello e la pagina resta SENZA CONTENUTO (§Pattern Tab-View, il caso
  //    dei tab condizionali). Si dichiara in sviluppo e si ripiega sul primo.
  let partenza = iniziale ?? valori[0]
  if (!valori.includes(partenza)) {
    if (import.meta.env.DEV) {
      console.warn(`[useTabDaQuery] scheda iniziale "${partenza}" fuori dagli ammessi:`, valori)
    }
    partenza = valori[0]
  }

  // ⚠️ Dichiarato PRIMA del watch che lo tocca (TDZ silenziosa).
  const attivo = ref(partenza)

  function applicaDaQuery() {
    if (route.name !== nomeRotta) return
    const richiesta = route.query[parametro]
    if (!valori.includes(richiesta)) return
    attivo.value = richiesta
    const resto = { ...route.query }
    delete resto[parametro]
    router.replace({ query: resto })
  }

  watch(() => route.query[parametro], applicaDaQuery)
  onActivated(applicaDaQuery)
  if (ripartiDaIniziale) {
    onDeactivated(() => { attivo.value = partenza })
  }

  return attivo
}
