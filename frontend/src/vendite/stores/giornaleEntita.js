// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: gli store della STORIA di un'entita' — la lista a catalogo
//        `vendite.giornale` filtrata su UNA fattura o su UN lotto (e le sue
//        fatture), consumata da `GiornaleEntitaTab` via `useDrawerTabLista`.
// Note: ⭐ DUE store da UNA factory, e non uno solo condiviso: `FatturaDrawer`
//       e `LottoDrawer` possono essere aperti uno dentro l'altro (la fattura
//       dal kebab dei documenti del lotto), e uno store unico scriverebbe la
//       pagina e i filtri di una Storia nell'altra
//       (`feedback_estrarre_non_condividere_stato`).
//       ⭐ IL PADRE E' COMPOSTO — l'entita' (nel path) e il suo EMITTENTE —
//       ed e' il padre composto del core (`emittenteParam`, 2026-09-27).
//       L'emittente non sta nel path: `vendite.giornale` e'
//       `perimetro_emittente = t` e `multi_emittente = f`, e l'endpoint lo
//       legge in query (`emittente_soggetto_ruolo_id`, il
//       `lista_emittente_param` della view) per non sbarrare (422) chi ha piu'
//       emittenti nello scope dentro un drawer gia' aperto su un documento
//       che l'emittente lo dichiara. ⚠️ E' NOT NULL su fatture e lotti:
//       finche' manca, il dettaglio non e' ancora qui, e la lista aspetta
//       (`attesaPadre`) invece di leggere. E' CONTESTO, non filtro: per
//       questo non sta in `filterDefaults`, dove «Pulisci filtri» lo
//       toglierebbe e il segno dei filtri lo conterebbe.
//       ⚠️ `defineStore` + `useListaStoreCore` e non `createListaStore`: i
//       contatori di cio' che il filtro nasconde li scrive `onPayload`, che
//       deve chiudere su ref nati PRIMA del core — la forma di `giornale.js`
//       (il trasversale) e di `distintaRighe`.
//       ⛔ Non e' `useGiornaleStore` (il trasversale): quello porta i filtri
//       dell'operatore di una schermata (gravita', registro, date, filo), e
//       condividerlo li scriverebbe dentro la Storia di un documento.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaStoreCore } from '../../core/composables/useListaStoreCore'
import { storePerIstanza } from '../../core/stores/storePerIstanza'
import { listFatturaGiornale } from '../api/fatture'
import { listLottoGiornale } from '../api/lotti'

// Scopo: la factory dei due store. `fetchPage(entitaId, params)` e' l'endpoint
//        annidato dell'entita'; `filterDefaults`/`filtriNeutri` i filtri che
//        quella Storia ha in piu' (solo il lotto ne ha uno).
function creaStoreGiornaleEntita(storeIdBase, { fetchPage, filterDefaults = {}, filtriNeutri = {} }) {
  // ⭐ Uno store per DRAWER (`storePerIstanza`), non per tipo: due fatture
  //    aperte insieme (una vista sotto KeepAlive, l'altra nel tool di
  //    fatturazione) si scrivevano la Storia l'una nell'altra.
  return storePerIstanza(storeIdBase, (storeId) => defineStore(
    storeId,
    () => {
      // Quante righe il filtro sta nascondendo (dal BE): le RITIRATE (tentativi
      // poi rifatti) e — sul lotto — le INFO. ⛔ Senza, «nessun evento» e «tre
      // eventi, tutti superati» si leggono uguali.
      const ritirateCount = ref(0)
      const infoCount = ref(0)

      const base = useListaStoreCore({
        fetchPage,
        parentField: 'entitaId',
        emittenteParam: 'emittente_soggetto_ruolo_id',
        startsEmpty: false,
        filterDefaults,
        filtriNeutri,
        // Allineato al preset `giornale_default` di `vendite.giornale` (`quando
        // desc`): l'ultima cosa successa in cima. ⚠️ Fino al 2026-09-27 la
        // Storia partiva dalla gravita': «c'e' un errore?» lo dice ora il
        // banner della fattura, con una fonte sua nel dettaglio.
        orderBy: 'quando',
        orderDir: 'desc',
        orderDirDefault: 'desc',
        onPayload: (payload) => {
          ritirateCount.value = payload.ritirate_count ?? 0
          infoCount.value = payload.info_count ?? 0
        },
      })

      function reset() {
        base.reset()
        ritirateCount.value = 0
        infoCount.value = 0
      }

      return { ...base, reset, ritirateCount, infoCount }
    },
    { userScoped: true },
  ))
}

// La Storia della FATTURA: tutte le gravita', nessun filtro proprio — sul
// documento singolo le righe sono poche e si mostrano tutte.
export const useFatturaGiornaleStore = creaStoreGiornaleEntita('vendite-fattura-giornale', {
  fetchPage: listFatturaGiornale,
})

// La Storia del LOTTO: il lotto PIU' le sue fatture, di default senza le righe
// di routine. ⭐ Il filtro e' `info` sul filo («anche le INFO»): `false` =
// «solo problemi», il default, che RESTRINGE; `true` = «tutto», che non
// restringe niente — ed e' per questo che e' il suo valore NEUTRO. ⛔ Senza,
// il segno dei filtri attivi conterebbe 1 proprio su «tutto», cioe' sulla
// lista piu' larga (il verso sbagliato, pagato il 2026-09-23).
export const useLottoGiornaleStore = creaStoreGiornaleEntita('vendite-lotto-giornale', {
  fetchPage: listLottoGiornale,
  filterDefaults: { info: false },
  filtriNeutri: { info: true },
})
