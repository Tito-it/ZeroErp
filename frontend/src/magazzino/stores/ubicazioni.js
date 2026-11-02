// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Lo store della lista UBICAZIONI DI UN MAGAZZINO
//        (`magazzino.ubicazioni`, lista 81), consumato da
//        `MagazzinoUbicazioniDrawer` attraverso `useDrawerTabLista`; i verbi
//        di scrittura avvisano il MAGAZZINO (il suo `ubicazioni_count` cambia).
// Note: ⭐ IL PADRE E' NELLO STORE, NON NEI FILTRI: `magazzinoId` e' il contesto
//       (il path dell'endpoint), i filtri sono le scelte dell'operatore — al
//       cambio padre i secondi si azzerano, il primo si riscrive.
//       ⚠️ `userScoped: true` (default): le ubicazioni sono del perimetro del
//       magazzino (RLS).
// ------------------------------------------------------------

import { TAB_ENTITIES } from '../../core/constants'
import { invalidateLookup } from '../../core/composables/useGlobalLookup'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { createListaStore } from '../../core/stores/createListaStore'
import {
  aggiornaUbicazione,
  creaUbicazione,
  getUbicazione,
  listUbicazioni,
} from '../api/magazzino'
import { chiaveLookupUbicazioni } from '../vocabolari'

export const useUbicazioniStore = createListaStore('magazzino-ubicazioni', {
  fetchPage: listUbicazioni,
  parentField: 'magazzinoId',
  // Il magazzino e' gia' scelto quando il drawer si apre.
  startsEmpty: false,
  filterDefaults: { attivo: true },
  orderBy: 'codice',
  orderDir: 'asc',
  extend: (base) => {
    const { emitDataChanged } = useTabEvents()

    async function fetchDetail(ubicazioneId) {
      const res = await getUbicazione(base.magazzinoId.value, ubicazioneId)
      return res.data.data
    }

    // ⭐ Un'ubicazione scritta cambia il MAGAZZINO (`ubicazioni_count`): si
    //    avvisa con l'evento del padre, e la lista magazzini si rinfresca. E
    //    la cache del lookup delle ubicazioni di QUESTO magazzino — il picker
    //    del padre in `UbicazioneDrawer` — si invalida. (Il form di riga del
    //    documento interno legge lo stesso endpoint SENZA cache,
    //    `useLetturaTreStati`: non c'e' niente da invalidare li'.)
    function scritto() {
      emitDataChanged(TAB_ENTITIES.MAGAZZINO, base.magazzinoId.value)
      invalidateLookup(chiaveLookupUbicazioni(base.magazzinoId.value))
    }

    async function create(payload) {
      const res = await creaUbicazione(base.magazzinoId.value, payload)
      scritto()
      return res.data.data
    }

    async function update(ubicazioneId, payload) {
      const res = await aggiornaUbicazione(base.magazzinoId.value, ubicazioneId, payload)
      scritto()
      return res.data.data
    }

    return { fetchDetail, create, update }
  },
})
