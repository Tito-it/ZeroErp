// Store Pinia dell'elenco «fondi fattura da decidere» (lista configurabile
// `vendite.fondi_fattura_da_decidere`, ui.lista_definizione id 44 — seedata il
// 2026-08-15 e rimasta SENZA consumatore frontend fino al 2026-08-22).
//
// Interfaccia useSearchTable-compatibile (items/totalRecords/loading/filters/
// fetchList/hasSearched), la stessa che pretende `useListaConfigurabilePage`.
//
// ⭐ Semantica CODA DI LAVORO, non lista storica: `alwaysFetch: true` e NESSUN
// floor temporale di default. Il floor standard delle liste (oggi-60gg al 1°
// del mese, `defaultFiltroDataDa`) qui nasconderebbe proprio il lavoro
// arretrato — e una riga «da decidere» vecchia di tre mesi e' quella che pesa
// di piu', non quella che conta meno. Stessa scelta delle due code resi e
// delle due code Strumenti.
//
// userScoped: reset al logout (memoria feedback_pinia_userscoped) — lo stato
// di filtri e pagina e' dell'operatore, non del browser.

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { paramsOrdinamento } from '../../core/utils/listParams'
import { listFondiFatturaDaDecidere } from '../api/fondiFattura'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'
import { USO_MISURA, misuraDefault } from '../../core/misurePagina'

// Scopo: mappa i filtri dello store nei query param dell'endpoint.
//
// ⭐ `limit`/`offset` come la lista li tiene, senza conversione: dal 2026-10-20
//    l'endpoint pagina come le altre liste (decisione Tid, brief-be-verifica-
//    documentazione-api §A4). Fino a quel giorno era PAGE-BASED e passava dal
//    BB `paramsPagina` (oggi `paramsFinestra`).
//
// ⚠️ La `search` NON si inoltra: questo endpoint non ha ricerca testuale.
// Passarla sarebbe un parametro ignorato in silenzio — l'operatore digiterebbe
// e vedrebbe la lista intera, convinto di aver cercato. Il campo di ricerca
// infatti non e' montato nella pagina.
function buildParams(f) {
  const p = { limit: f.limit, offset: f.offset, ...paramsOrdinamento(f) }
  if (f.motivo) p.motivo = f.motivo
  return p
}

export const useFondiFatturaDaDecidereStore = defineStore(
  'vendite-fondi-fattura-da-decidere',
  () => {
    // ⭐ I FILTRI DI DOMINIO IN UNA SEDE SOLA (2026-09-23): da qui nascono i valori
    //    di partenza della lista E il contratto che `FiltriLista` legge per il segno
    //    dei filtri attivi (`useContrattoFiltriLista`). ⛔ Due letterali divergono
    //    al primo filtro aggiunto da una parte sola, e il segno si spegnerebbe su
    //    una lista che filtra — senza nessun errore.
    const FILTRI_DEFAULT = {
      // Vocabolario chiuso dei quattro motivi (null = tutti).
      motivo: null,
    }

    const filters = ref({
      ...FILTRI_DEFAULT,
      limit: misuraDefault(USO_MISURA.PAGINA),
      offset: 0,
      // Default `data desc`, lo stesso che applica il backend quando non gli
      // si dice nulla: la lista non si riordina sotto gli occhi
      // dell'operatore al primo caricamento.
      order_by: 'data',
      order_dir: 'desc',
    })

    // `lista`: lo stato del BB, esposto INTERO nel `return` (`...lista`).
    // ⛔ Non si elencano i suoi ref a mano: un ref nuovo del BB (com'e'
    //    successo con `ricercaFull`, `ricercaMinCaratteri`,
    //    `ricercaCambiaLaRichiesta`) arriverebbe solo agli store che lo
    //    ricordano — e senza errore sugli altri.
    const lista = useListaEmptyStateFetch({
      filters,
      buildParams,
      fetchPage: listFondiFatturaDaDecidere,
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
