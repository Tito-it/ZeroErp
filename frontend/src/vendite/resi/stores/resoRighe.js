// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista RIGHE di un reso (lista configurabile
//        `vendite.reso_righe`), montato da
//        `RigheMasterDetailTable` (brief-db-liste-righe-documento, lotto B).
// Note: la forma e' la factory condivisa `createRigheListaStore`; uno store
//       per drawer (`storePerIstanza`), perche' due documenti aperti insieme
//       non si scrivano addosso pagina, ricerca e ordinamento.
// ------------------------------------------------------------
import { storePerIstanza } from '../../../core/stores/storePerIstanza'
import { createRigheListaStore } from '../../_shared/righe/createRigheListaStore'
import { listRigheLista } from '../api/resiApi'

export const useResoRigheStore = storePerIstanza(
  'vendite-reso-righe',
  (id) => createRigheListaStore(id, { fetchPage: listRigheLista }),
)
