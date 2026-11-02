// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia del giornale TRASVERSALE degli eventi (pezzo G
//        dell'osservabilita'): `createListaStore` con i filtri della
//        whitelist del backend.
// ------------------------------------------------------------
//
// ⭐ Un registro: parte pieno e si legge dal piu' recente. `search` esiste
//    solo perche' `useSearchTable` ci scrive: il backend non ha ricerca
//    testuale.
// ⚠️ `gravita` viaggia come CSV (`ERROR` | `ERROR,WARN`): e' il valore che
//    l'interruttore «solo errori» scrive (`bindToggle`, on/off), non un
//    booleano — il backend legge la lista di gravita'.
// ⚠️ `filo` e' la porta del DEEP-LINK dal registro degli errori tecnici
//    (`?tx_id=`): la view lo legge in `onActivated` e lo scrive qui.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaStoreCore } from '../../core/composables/useListaStoreCore'
import { defaultFiltroDataDaString } from '../../core/utils/date'
import { listGiornale } from '../api/giornale'

// I due valori dell'interruttore «solo errori»: acceso = i soli ERROR
// (col NULL, che il backend include), spento = anche gli avvisi.
export const GRAVITA_SOLO_ERRORI = 'ERROR'
export const GRAVITA_CON_AVVISI = 'ERROR,WARN'

// ⚠️ `defineStore` + `useListaStoreCore` e non `createListaStore`: il
//    contatore delle ritirate lo scrive `onPayload`, che deve chiudere su un
//    ref nato PRIMA del core — la forma di `distintaRighe`.
export const useGiornaleStore = defineStore(
  'vendite-giornale',
  () => {
    // Quante segnalazioni RITIRATE il perimetro sta nascondendo (dal BE):
    // senza, «nessun errore» e «tre errori, tutti superati» si leggono uguali.
    const ritirateCount = ref(0)

    const base = useListaStoreCore({
      fetchPage: listGiornale,
      startsEmpty: false,
      filterDefaults: {
        gravita: GRAVITA_SOLO_ERRORI,
        registro: null,
        entity_type: null,
        filo: null,
        // Floor temporale standard delle liste (`feedback_filtro_data_liste`):
        // e' consultazione, non coda di lavoro.
        data_da: defaultFiltroDataDaString(),
        data_a: null,
      },
      // Allineato al preset `giornale_default` (`quando desc`): l'ultima cosa
      // successa in cima. Il ripiego del verso segue.
      orderBy: 'quando',
      orderDir: 'desc',
      orderDirDefault: 'desc',
      onPayload: (payload) => { ritirateCount.value = payload.ritirate_count ?? 0 },
    })

    function reset() {
      base.reset()
      ritirateCount.value = 0
    }

    return { ...base, reset, ritirateCount }
  },
  { userScoped: true },
)
