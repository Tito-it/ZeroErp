// Scopo: Thin wrapper sopra `useRigaComponenti` (BB generico, Fase H
//        2026-05-14) che chiude le API specifiche preventivi + emit
//        `TAB_ENTITIES.PREVENTIVO`. Esisteva come composable autonomo
//        prima dell'estrazione; mantenuto come API ergonomica per i
//        consumer preventivi (PreventiviRigaComponentiPanel + i 2-3
//        callsite indiretti).
//
//        Per nuovi consumer (contratti/ordini/ddt) usare direttamente
//        `useRigaComponenti(documentoId, { apiList, apiUpdate, apiDelete,
//        tabEntity })`.

import {
  listRigaComponenti,
  updateRigaComponente,
  deleteRigaComponente,
} from '../../vendite/preventivi/api/preventiviApi'

import { useRigaComponenti } from './useRigaComponenti'
import { TAB_ENTITIES } from '../constants'

// preventivoIdInput: scalar number, ref<number> o getter `() => x`.
// Quando il consumer e' un componente con `props.preventivoId` che puo'
// cambiare senza rimount, passare `() => props.preventivoId`. Vedi
// `useRigaComponenti` per dettagli su reattivita' e modalita' `soloAttivi`.
export function usePreventivoRigaComponenti(
  preventivoIdInput, { soloAttivi = true } = {},
) {
  return useRigaComponenti(preventivoIdInput, {
    apiList: listRigaComponenti,
    apiUpdate: updateRigaComponente,
    apiDelete: deleteRigaComponente,
    soloAttivi,
    tabEntity: TAB_ENTITIES.PREVENTIVO,
  })
}
