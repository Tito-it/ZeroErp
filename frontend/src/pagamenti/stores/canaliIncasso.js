// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia dei CANALI DI INCASSO (`pagamenti.enti_incasso`) —
//        la configurazione da cui il denaro entra.
// Note: ⛔ Questa lista NON e' una `<ListaConfigurabile>`, e non e' una
//        dimenticanza: non ha un seed in `ui.lista_definizione` (verificato sul
//        database il 2026-08-28 — le liste seminate del dominio sono quattro, e
//        i canali non ci sono). Montarla sul BB senza seed significherebbe
//        mandare al backend il `campo_sorgente` di colonne che nessuno ha
//        dichiarato, e l'intestazione risponderebbe **400** al click.
//        📮 Il giorno in cui il seed esiste, `ENTI_INCASSO_SORT_COLUMNS` va
//        riscritto sui nomi FISICI (`centro` -> `centro_descrizione`): oggi e'
//        chiavato sui codici logici, ed e' legittimo solo finche' la tendina
//        delle colonne non esiste. Il commento nel repository lo dice.
//        ⚠️ Nessun pavimento temporale: la configurazione non ha una «data da»,
//        e un canale creato l'anno scorso e' vivo quanto quello di stamattina.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { paramsFinestra } from '../../core/utils/listParams'
import { listEntiIncasso } from '../api/pagamenti'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'
import { USO_MISURA, misuraDefault } from '../../core/misurePagina'

function buildParams(f) {
  // ⚠️ `orderDirDefault: 'asc'`: e' l'ordine naturale di un elenco di codici, ed
  //    e' anche il default del backend — mandare `desc` mostrerebbe la
  //    configurazione al contrario di come la legge chi la mantiene.
  const p = paramsFinestra(f, { orderDirDefault: 'asc' })
  if (f.tipo) p.tipo = f.tipo
  if (f.centro_riscossione_id != null) p.centro_riscossione_id = f.centro_riscossione_id
  // ⚠️ `!= null` e non un test di verita': `false` e' un filtro legittimo
  //    («mostrami i canali spenti»), e uno `if (f.attivo)` lo perderebbe.
  if (f.attivo != null) p.attivo = f.attivo
  return p
}

export const useCanaliIncassoStore = defineStore(
  'pagamenti-canali-incasso',
  () => {
    // ⭐ I FILTRI DI DOMINIO IN UNA SEDE SOLA (2026-09-23): da qui nascono i valori
    //    di partenza della lista E il contratto che `FiltriLista` legge per il segno
    //    dei filtri attivi (`useContrattoFiltriLista`). ⛔ Due letterali divergono
    //    al primo filtro aggiunto da una parte sola, e il segno si spegnerebbe su
    //    una lista che filtra — senza nessun errore.
    const FILTRI_DEFAULT = {
      tipo: null,
      centro_riscossione_id: null,
      attivo: null,
    }

    const filters = ref({
      ...FILTRI_DEFAULT,
      // Dichiarata per contratto con `useSearchTable`, che la scrive su
      // deep-link `?search=`. Il backend dei canali non ha ricerca testuale.
      search: '',
      limit: misuraDefault(USO_MISURA.PAGINA),
      offset: 0,
      order_by: 'codice',
      order_dir: 'asc',
    })

    // `lista`: lo stato del BB, esposto INTERO nel `return` (`...lista`).
    // ⛔ Non si elencano i suoi ref a mano: un ref nuovo del BB (com'e'
    //    successo con `ricercaFull`, `ricercaMinCaratteri`,
    //    `ricercaCambiaLaRichiesta`) arriverebbe solo agli store che lo
    //    ricordano — e senza errore sugli altri.
    const lista = useListaEmptyStateFetch({
      filters,
      buildParams,
      fetchPage: listEntiIncasso,
      alwaysFetch: true,
    })
    const { fetchList } = lista

    // Il contratto che `FiltriLista` legge: chi sono i filtri, com'erano alla
    // nascita, e come si riportano li' («Pulisci filtri»).
    const { chiaviFiltro, filtriDefault, azzeraFiltri } = useContrattoFiltriLista({
      filters, filterDefaults: FILTRI_DEFAULT, fetchList,
    })

    return {
      ...lista,
      filters,
      chiaviFiltro, filtriDefault, azzeraFiltri,
    }
  },
  { userScoped: true },
)
