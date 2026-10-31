// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Gli store delle liste di NOTE, uno per tabella-madre `<schema>.note`
//        (D-2 di brief-db-liste-datatable-grezze-secondo-giro, 2026-10-31):
//        `vendite.note` (lista 109) e `catalogo.note` (110). Li consuma
//        `NoteDrawer` attraverso `ListaConFormInline`.
// Note: ⭐ IL PADRE E' IL PERCORSO DELLE NOTE (`makeNotesApi(...).basePath`,
//       `/vendite/preventivi/12`, `/catalogo/articoli/<uuid>`): l'endpoint e'
//       `<basePath>/note/`, e la lista non deve sapere di che documento si
//       tratta. Le note di vendita hanno il perimetro dell'emittente: il padre
//       e' composto, e l'emittente del documento va come parametro.
//       ⭐ Uno store PER ISTANZA del drawer (`storePerIstanza`, dal
//       2026-10-31): due `NoteDrawer` della stessa sede vivi insieme (le note
//       dell'articolo e quelle di un componente della sua BoM, due viste
//       sotto KeepAlive) non si azzerano ne' si sovrascrivono la lista.
//       ⚠️ Una chiamata per istanza: la fa `NoteDrawer` nel suo setup.
//       `userScoped` (default di `createListaStore`).
// ------------------------------------------------------------

import { listNotePerPercorso } from '../api/notes'
import { createListaStore } from './createListaStore'
import { storePerIstanza } from './storePerIstanza'

const STORE_NOTE = {
  'vendite.note': storePerIstanza('note-lista-vendite', (id) => createListaStore(id, {
    fetchPage: listNotePerPercorso,
    parentField: 'padreId',
    emittenteParam: 'emittente_fiscale_id',
    startsEmpty: false,
  })),
  'catalogo.note': storePerIstanza('note-lista-catalogo', (id) => createListaStore(id, {
    fetchPage: listNotePerPercorso,
    parentField: 'padreId',
    startsEmpty: false,
  })),
}

// Il codice lista dice se il padre porta l'emittente (perimetro).
export const NOTE_CON_EMITTENTE = Object.freeze({ 'vendite.note': true, 'catalogo.note': false })

// Scopo: uno store NUOVO della lista di note di quella sede, per l'istanza
//        che lo chiama (si distrugge con il suo scope). Un codice sconosciuto
//        e' un errore del chiamante, non una lista vuota.
export function useNoteListaStore(codice) {
  const store = STORE_NOTE[codice]
  if (!store) throw new Error(`useNoteListaStore: nessuna lista di note per '${codice}'`)
  return store()
}
