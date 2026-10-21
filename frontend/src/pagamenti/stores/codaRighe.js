// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia della CODA DEL RICONCILIATORE — le righe contabili da
//        lavorare, viste attraverso le distinte (lista `pagamenti.righe`).
// Note: ⭐ UNA LISTA, DUE PORTE (Q-4 -> c): «da abbinare» e «sospese» sono la
//       stessa lista con il filtro `coda` gia' impostato, ed e' il motivo per
//       cui a catalogo il seed e' UNO. Chi apre la voce di menu passa la coda
//       che gli compete.
//       ⛔ `coda` NON e' opzionale come gli altri filtri: e' un vocabolario
//       CHIUSO (`DA_ABBINARE` | `SOSPESE` | `TUTTE`) e un valore inventato e'
//       un **400**, non una lista vuota — su elenchi che esistono per non far
//       sparire del denaro, «nessun risultato» sarebbe la risposta piu'
//       rassicurante e piu' falsa.
//       ⭐ Nessun pavimento temporale: e' una coda di lavoro, e la riga vecchia
//       e' quella che pesa di piu'.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { paramsFinestra, paramsRicerca } from '../../core/utils/listParams'
import { CODE } from '../vocabolari'
import { listCodaRighe } from '../api/pagamenti'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'
import { USO_MISURA, misuraDefault } from '../../core/misurePagina'

function buildParams(f, _termine, ricerca) {
  const p = paramsFinestra(f)
  // La ricerca libera con la regola comune (`paramsRicerca`: trim, soglia della
  // lista — `ricerca` = `{ minCaratteri }`, passato dal BB di stato).
  Object.assign(p, paramsRicerca(f, ricerca))
  // ⚠️ Sempre inviata: senza, il backend non saprebbe quale coda serve.
  p.coda = f.coda || CODE.DA_ABBINARE
  if (f.billing_account_id != null) p.billing_account_id = f.billing_account_id
  if (f.data_da) p.data_da = f.data_da
  if (f.data_a) p.data_a = f.data_a
  return p
}

export const useCodaRigheStore = defineStore(
  'pagamenti-coda-righe',
  () => {
    // ⭐ I FILTRI DI DOMINIO IN UNA SEDE SOLA (2026-09-23): da qui nascono i valori
    //    di partenza della lista E il contratto che `FiltriLista` legge per il segno
    //    dei filtri attivi (`useContrattoFiltriLista`). ⛔ Due letterali divergono
    //    al primo filtro aggiunto da una parte sola, e il segno si spegnerebbe su
    //    una lista che filtra — senza nessun errore.
    const FILTRI_DEFAULT = {
      coda: CODE.DA_ABBINARE,
      billing_account_id: null,
      data_da: null,
      data_a: null,
    }

    const filters = ref({
      ...FILTRI_DEFAULT,
      // La ricerca libera: la scrive `useSearchTable` (casella nel `#sempre`
      // di `FiltriLista`, ricerca universale, deep-link `?search=`), la
      // inoltra `buildParams` (`paramsRicerca`). Le colonne le decide il
      // catalogo (brief-be-ricerca-full-liste-residue §5.3).
      search: '',
      limit: misuraDefault(USO_MISURA.PAGINA),
      offset: 0,
      order_by: 'data_pagamento',
      order_dir: 'desc',
    })

    // ⭐ Il CATALOGO degli stati di riga e le uscite richiedibili DA OGNI STATO
    //    (`transizioni_riga`, dalla matrice del database) arrivano ACCANTO alle
    //    righe (FE-4, 2026-09-19): dalla coda si lavora — abbina, sospendi,
    //    scarta, riporta — e le voci del kebab si costruiscono dalla matrice,
    //    come nel drawer. ⛔ Non un elenco cablato qui: il giorno che nasce uno
    //    stato nuovo, una copia nel frontend lo nasconderebbe senza dirlo.
    const statiRiga = ref([])
    const transizioniRiga = ref({})

    // `lista`: lo stato del BB, esposto INTERO nel `return` (`...lista`).
    // ⛔ Non si elencano i suoi ref a mano: un ref nuovo del BB (com'e'
    //    successo con `ricercaFull`, `ricercaMinCaratteri`,
    //    `ricercaCambiaLaRichiesta`) arriverebbe solo agli store che lo
    //    ricordano — e senza errore sugli altri.
    const lista = useListaEmptyStateFetch({
      filters,
      buildParams,
      fetchPage: listCodaRighe,
      alwaysFetch: true,
      // Dopo il guard di versione: una risposta scartata perche' stantia non
      // riscrive il catalogo sotto quella piu' recente.
      onPayload: (payload) => {
        statiRiga.value = payload.stati_riga ?? []
        transizioniRiga.value = payload.transizioni_riga ?? {}
      },
    })
    const { fetchList } = lista

    // Il contratto che `FiltriLista` legge: chi sono i filtri, com'erano alla
    // nascita, e come si riportano li' («Pulisci filtri»).
    const { chiaviFiltro, filtriDefault, azzeraFiltri } = useContrattoFiltriLista({
      filters, filterDefaults: FILTRI_DEFAULT, fetchList,
    })

    // Scopo: la voce di menu sceglie la coda e ricarica.
    // Note: ⚠️ Azzera l'offset: restare a pagina 3 passando da una coda
    //       all'altra mostrerebbe una pagina che in quella coda non esiste, e
    //       l'elenco risulterebbe vuoto senza motivo apparente.
    function apriCoda(coda) {
      filters.value.coda = coda || CODE.DA_ABBINARE
      filters.value.offset = 0
      return fetchList()
    }

    return {
      ...lista,
      filters, apriCoda,
      statiRiga, transizioniRiga,
      chiaviFiltro, filtriDefault, azzeraFiltri,
    }
  },
  { userScoped: true },
)
