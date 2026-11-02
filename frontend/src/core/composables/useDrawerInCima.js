// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ ESCE SOLO IL DRAWER IN CIMA (2026-10-04, ok Tid: «da pensare da
//        subito come standard»). Il gemello di `escapeSoloInCima` per i
//        drawer: lo usa `AppDrawer`, e il chiamante non scrive niente.
//
// ⚠️ IL DIFETTO. In PrimeVue 4 ogni `Drawer` aperto registra il suo listener
//    `keydown` su `document`: con due drawer impilati, ESC li chiudeva TUTTI E
//    DUE. Il padre usciva (con la SUA conferma, che del figlio non sa niente)
//    e smontava il figlio, modifiche comprese, senza chiedere. Trovato il
//    2026-10-03 portando la versione di template nel suo drawer; il difetto
//    era gia' di ogni drawer che ne apre un altro sopra di se'.
//
// ⭐ LA REGOLA. Una PILA dei drawer visibili, nell'ordine di apertura: l'uscita
//    (X, ESC, clic fuori, Annulla) e' ammessa solo al drawer in cima. Gli altri
//    la ignorano: ESC la gestisce chi sta sopra, con la sua conferma.
//    ⛔ Pila di MODULO, non `provide`/`inject`: meta' dei drawer figli e'
//    montata ACCANTO al padre, fuori dal suo slot (le note di ordini, DDT,
//    preventivi; i sotto-drawer di articolo e soggetto), e un registro
//    sull'albero dei componenti non li vedrebbe.
//
// ⚠️ ESC dello stesso evento: padre e figlio lo ricevono entrambi, ma la pila
//    cambia solo al ridisegno successivo (la prop `visible` si aggiorna dopo):
//    durante l'evento il figlio e' ancora in cima, e il padre lo ignora.
// ⚠️ Una tab in KeepAlive tiene montato il suo drawer: `AppDrawer` lo toglie
//    dalla pila a tab disattivata (`esce`) e lo rimette in cima alla
//    riattivazione (`entra`), o il drawer di un'altra tab resterebbe «sotto»
//    per sempre.
//
// Uso (in `AppDrawer`):
//   const { inCima, entra, esce } = useDrawerInCima(() => props.visible)
//   function chiudi() { if (!inCima.value) return; ... }

import { computed, getCurrentScope, onScopeDispose, shallowRef, watch } from 'vue'

const pila = shallowRef([])

// `AppDrawer` fornisce ai suoi figli il proprio `inCima`: chi vive DENTRO un
// drawer (la barra di una lista, `useScorciatoie`) sa cosi' se il suo
// livello e' quello davanti. Assente = il livello della pagina.
export const DRAWER_IN_CIMA_KEY = Symbol('drawer-in-cima')

// Scopo: quanti drawer sono aperti. Lo legge `useScorciatoie` (la pagina e'
//        davanti solo senza drawer aperti), e i test.
export function drawerAperti() {
  return pila.value.length
}

export function useDrawerInCima(visibile) {
  const id = Symbol('drawer')

  function esce() {
    if (pila.value.includes(id)) pila.value = pila.value.filter((x) => x !== id)
  }
  // Riaprire sposta in cima: un drawer gia' in pila non si duplica.
  function entra() {
    pila.value = [...pila.value.filter((x) => x !== id), id]
  }

  watch(visibile, (v) => (v ? entra() : esce()), { immediate: true })
  if (getCurrentScope()) onScopeDispose(esce)

  const inCima = computed(() => pila.value.at(-1) === id)
  return { inCima, entra, esce }
}
