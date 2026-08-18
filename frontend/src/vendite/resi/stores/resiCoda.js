// Store Pinia delle due code di lavoro resi (da accreditare / da ri-consegnare),
// promosse a liste configurabili (<ListaConfigurabile codice="vendite.resi_da_*">,
// ui.lista_definizione id 10/11). Ogni coda ha il proprio stato
// filtri/paginazione/sort: due store distinti (singleton Pinia per id), prodotti
// da UNA factory per non duplicare l'interfaccia useSearchTable-compatibile
// (items/totalRecords/loading/filters/fetchList/hasSearched).
//
// userScoped: true → reset al logout (autoResetPlugin): lo stato utente non
// deve sopravvivere al cambio operatore (memoria feedback_pinia_userscoped).
//
// Semantica CODA DI LAVORO: niente floor temporale `data_da` di default (il
// floor standard delle liste nasconderebbe il lavoro arretrato pendente):
// `alwaysFetch: true` carica sempre
// al mount tutte le righe pertinenti; i filtri data restano opzionali. Le viste
// BE si auto-limitano ai resi CONFERMATO con copertura/credito pendente.

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../../core/composables/useListaEmptyStateFetch'
import { listDaAccreditare, listDaRiconsegnare } from '../api/resiApi'

// Scopo: mappa filtri store → query params degli endpoint coda. Search ignorata
//        sotto i 3 caratteri (parità lista resi/DDT). order_by/order_dir e
//        paginazione sempre inoltrati.
function buildCodaParams(f, searchTerm) {
  const p = {
    limit: f.limit,
    offset: f.offset,
    order_by: f.order_by,
    order_dir: f.order_dir,
  }
  if (searchTerm.length >= 3) p.search = searchTerm
  if (f.billing_account_id != null) p.billing_account_id = f.billing_account_id
  if (f.data_da) p.data_da = f.data_da
  if (f.data_a) p.data_a = f.data_a
  // Solo coda accrediti (forma contatore): DOVUTA (a credito, NC obbligatoria)
  // | FACOLTATIVA (per ri-consegna, opzione DL-26). null = tutte.
  if (f.etichetta) p.etichetta = f.etichetta
  // Restrizione a UN documento: e' il collegamento dal pannello situazione
  // merce (FE-2). I due sono ALTERNATIVI — il backend rifiuta la coppia con
  // E_RESO_VALIDAZIONE — e qui non si prova a comporli: sarebbe due domande
  // in una, con la seconda che restringe la prima in silenzio.
  if (f.ddt_id != null) p.ddt_id = f.ddt_id
  else if (f.ordine_id != null) p.ordine_id = f.ordine_id
  return p
}

// Factory: crea uno store coda con l'interfaccia standard delle liste
// configurabili. `id` = id Pinia univoco; `fetchPage` = endpoint API della
// coda; `extraFilters` = filtri specifici della singola coda (solo la coda
// accrediti ha `etichetta`: lo store riconsegne non deve esporre un filtro
// che il suo endpoint non legge — sarebbe un no-op silenzioso).
function createResiCodaStore(id, fetchPage, extraFilters = {}) {
  return defineStore(id, () => {
    const filters = ref({
      search: '',
      billing_account_id: null,
      data_da: null,
      data_a: null,
      // Filtro documento del deep-link dal pannello situazione merce: vive
      // nello store (non solo nella query) perche' la coda lo deve DICHIARARE
      // a video — un elenco corto senza spiegazione si legge come «non c'e'
      // quasi niente da fare».
      ddt_id: null,
      ordine_id: null,
      ...extraFilters,
      limit: 25,
      offset: 0,
      // Default sort `data desc` (parità lista resi/DDT), allineato al
      // default backend e al defaultSortField della ResiCodaTable.
      order_by: 'data',
      order_dir: 'desc',
    })

    // alwaysFetch: la coda parte piena (lavoro pendente sempre visibile).
    const { items, totalRecords, loading, hasSearched, fetchList } =
      useListaEmptyStateFetch({
        filters,
        buildParams: buildCodaParams,
        fetchPage,
        alwaysFetch: true,
      })

    return { items, totalRecords, loading, hasSearched, filters, fetchList }
  }, {
    userScoped: true,
  })
}

export const useResiCodaAccreditareStore = createResiCodaStore(
  'vendite-resi-coda-accreditare', listDaAccreditare, { etichetta: null },
)
export const useResiCodaRiconsegnareStore = createResiCodaStore(
  'vendite-resi-coda-riconsegnare', listDaRiconsegnare,
)
