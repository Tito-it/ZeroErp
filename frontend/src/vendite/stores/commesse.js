// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia della commessa: il cambio di stato della testata e
//        l'avviso ai tab dei documenti che l'annullo riapre.
// Note: La commessa non ha lista ne' CRUD propri: il drawer di gestione legge
//       e scrive le righe dall'API direttamente. Questo store esiste per la
//       sola cosa che lo standard vuole in uno store: il PRODUTTORE
//       dell'avviso cross-tab (frontend-standards §«Producer cross-tab»).
//       Annullare la commessa riapre a monte (brief-db-annullo-a-valle-
//       riapre-a-monte): i documenti che l'hanno riempita tornano da mandare,
//       il reso da accreditare. Un'altra superficie che annulla la commessa
//       passa da qui e avvisa gli stessi tab.
// ------------------------------------------------------------
import { defineStore } from 'pinia'

import { cambiaStatoCommessa } from '../api/commesse'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { STATO_COMMESSA } from '../constants'
import { avvisaDocumentiCollegati } from '../_shared/annullo/avvisoDocumentiCollegati'

export const useCommesseStore = defineStore('vendite-commesse', () => {
  const { emitDataChanged } = useTabEvents()

  // Azione di stato utente (chiudi, riapri, annulla). `dichiarazione`: la
  // conferma dell'annullo con legami (`{ legami_confermati }`); vuota al primo
  // tentativo. L'annullo riapre i documenti dall'altra parte, e se ne
  // avvisano i tab.
  async function cambiaStato(id, nuovoStato, dichiarazione = {}) {
    const res = await cambiaStatoCommessa(id, nuovoStato, dichiarazione)
    if (nuovoStato === STATO_COMMESSA.ANNULLATA) avvisaDocumentiCollegati(emitDataChanged)
    return res.data.data
  }

  return { cambiaStato }
})
