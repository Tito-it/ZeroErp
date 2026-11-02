// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Lo store della lista LOTTI DI UN ARTICOLO (`magazzino.lotti`, lista
//        82), consumato da `ArticoloLottiDrawer` attraverso `useDrawerTabLista`.
// Note: ⭐ Il padre e' l'ARTICOLO (uuid) e viaggia come query `articolo_id`,
//       non nel path: `parentField` lo tiene fuori dai filtri come per le
//       liste col padre nel path, e `fetchPage` lo mette sul filo.
//       ⚠️ Niente RLS su `lotti` (un lotto e' dell'articolo) — `userScoped`
//       resta il default della factory per coerenza con le altre liste.
// ------------------------------------------------------------

import { TAB_ENTITIES } from '../../core/constants'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { createListaStore } from '../../core/stores/createListaStore'
import { aggiornaLotto, creaLotto, getLotto, listLotti } from '../api/magazzino'

export const useLottiStore = createListaStore('magazzino-lotti', {
  fetchPage: (articoloId, params) => listLotti({ articolo_id: articoloId, ...params }),
  parentField: 'articoloId',
  startsEmpty: false,
  filterDefaults: { attivo: true },
  // Il default del backend: `data_arrivo DESC, id DESC` — la partita piu'
  // recente in cima, e il ripiego del verso segue.
  orderBy: 'data_arrivo',
  orderDir: 'desc',
  orderDirDefault: 'desc',
  extend: (base) => {
    const { emitDataChanged } = useTabEvents()

    async function fetchDetail(lottoId) {
      const res = await getLotto(lottoId)
      return res.data.data
    }

    // Il lotto e' dell'articolo: si avvisa con l'evento dell'ARTICOLO, cosi'
    // la scheda che mostra «Lotti (N)» si rinfresca.
    async function create(payload) {
      const res = await creaLotto({ articolo_id: base.articoloId.value, ...payload })
      emitDataChanged(TAB_ENTITIES.ARTICOLO, base.articoloId.value)
      return res.data.data
    }

    async function update(lottoId, payload) {
      const res = await aggiornaLotto(lottoId, payload)
      emitDataChanged(TAB_ENTITIES.ARTICOLO, base.articoloId.value)
      return res.data.data
    }

    return { fetchDetail, create, update }
  },
})
