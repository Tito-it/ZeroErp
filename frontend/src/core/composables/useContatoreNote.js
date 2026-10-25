// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL PULSANTE «GESTISCI NOTE» STANDARD, col numero delle note
//        (2026-10-25, regola del 2, ok Tid). Ogni documento che ha note le
//        segnala allo stesso modo: il pallino col conteggio sopra l'icona,
//        solo quando ce n'e' almeno una — chi apre il documento vede che ci
//        sono note da leggere senza aprire il sotto-drawer.
//        Era scritto a mano nella sola fattura; gli altri documenti non lo
//        avevano.
//
// ⭐ DUE FONTI, UNA REGOLA. Il numero arriva:
//    · dal DETTAGLIO del documento, `contatori.note` (BB BE
//      `contatori_documento`): nessun round-trip in piu' all'apertura;
//    · dal sotto-drawer delle note dopo ogni create/update/delete: il BB
//      `NoteDrawer` emette `saved` col TOTALE aggiornato, e `aggiorna(totale)`
//      lo prende. Vale finche' il dettaglio non cambia: un dettaglio nuovo (o
//      ricaricato) porta il suo conteggio, fresco dal server, e quello del
//      salvataggio si scarta. Cosi' il drawer non deve ricordarsi di azzerare
//      niente: dettaglio a `null` = zero note = nessun pallino.
//    Chi non ha il dettaglio con i contatori (la scheda articolo, che le note
//    le elenca gia' nel riepilogo) passa solo da `aggiorna` / `azzera`.
//
// ⛔ Lo ZERO non si mostra: il pallino dice «qui c'e' qualcosa», e uno 0
//    non informa (`badge: null`, il BB `ActionBadge` lo nasconde).
//
// Uso nel drawer di un documento:
//   const contatoreNote = useContatoreNote(() => detail.value)
//   const drawerActions = computed(() => [
//     ...,
//     contatoreNote.azione({
//       label: t('vendite.ddt.gestisci_note'),
//       command: () => { noteDrawerVisible.value = true },
//     }),
//   ])
//   <DdtNoteDrawer … @saved="contatoreNote.aggiorna" />
// ------------------------------------------------------------

import { computed, ref, toValue, watch } from 'vue'

import { MANAGE_ICONS } from '../constants'

// La chiave dell'azione nella barra del drawer: la stessa su ogni documento.
export const AZIONE_GESTISCI_NOTE = 'manage-note'

// Scopo: il valore del pallino per un conteggio — `null` (nessun pallino)
//        sotto l'uno, altrimenti il numero.
export function badgeNote(conteggio) {
  return conteggio > 0 ? conteggio : null
}

// Scopo: stato del conteggio e azione standard per `DrawerActionsBar`.
//   `dettaglio` (opzionale): getter, ref o valore del dettaglio del documento,
//   di cui si legge `contatori.note`.
export function useContatoreNote(dettaglio = null) {
  // Il totale comunicato dal sotto-drawer; `null` = vale il dettaglio.
  const dalSalvataggio = ref(null)

  // Un dettaglio nuovo porta il suo conteggio: quello del salvataggio
  // precedente si scarta.
  watch(() => toValue(dettaglio), () => { dalSalvataggio.value = null })

  const conteggio = computed(() => {
    if (dalSalvataggio.value !== null) return dalSalvataggio.value
    const n = Number(toValue(dettaglio)?.contatori?.note ?? 0)
    return Number.isFinite(n) ? n : 0
  })

  const badge = computed(() => badgeNote(conteggio.value))

  // Scopo: il totale emesso dal sotto-drawer dopo un salvataggio. Un valore
  //        che non e' un numero (un wrapper che non lo propaga) si ignora:
  //        meglio il numero di prima che uno inventato.
  function aggiorna(totale) {
    if (typeof totale === 'number' && Number.isFinite(totale)) dalSalvataggio.value = totale
  }

  // Scopo: nessuna nota nota (cambio di entita' senza dettaglio).
  function azzera() {
    dalSalvataggio.value = 0
  }

  // Scopo: l'azione standard per `DrawerActionsBar`. Va chiamata DENTRO il
  //        computed delle azioni: legge `badge`, e cosi' il pallino segue il
  //        conteggio. `resto` passa intatto (`disabled`, `visible`, ...).
  function azione({ label, command, ...resto }) {
    return {
      key: AZIONE_GESTISCI_NOTE,
      kind: 'manage',
      label,
      icon: MANAGE_ICONS.NOTE,
      badge: badge.value,
      command,
      ...resto,
    }
  }

  return { conteggio, badge, aggiorna, azzera, azione }
}
