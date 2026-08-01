// Scopo: BB filtri lista documenti vendite lato STORE (estratto 2026-07-14,
// regola del 2 alla 3ª copia, ok Tid — unifica i blocchi hasActiveFilters +
// buildParams identici degli store ordini/ddt/resi consumati da
// useListaEmptyStateFetch). Convenzione comune: search >= 3 char,
// stato_codice_interno, billing_account_id, range data_da/data_a,
// limit/offset, order_by+order_dir; `withUtility` aggiunge utility_id per i
// domini che la espongono (ordini/ddt). Gemello BE:
// `extract_doc_list_filters` (vendite/api/_list_filters_helpers.py).

// Scopo: true se almeno un filtro non-search è attivo (il default temporale
//        data_da col default standard conta come filtro: la lista si popola al mount).
export function hasDocListActiveFilters(f, { withUtility = false } = {}) {
  return f.stato_codice_interno != null
    || f.billing_account_id != null
    || (withUtility && f.utility_id != null)
    || f.data_a != null
    || f.data_da != null
}

// Scopo: mappa store.filters + searchTerm nei query param della lista
//        documento (limit/offset based).
export function buildDocListParams(f, searchTerm, { withUtility = false } = {}) {
  const params = {}
  if (searchTerm.length >= 3) params.search = searchTerm
  if (f.stato_codice_interno != null) params.stato_codice_interno = f.stato_codice_interno
  if (f.billing_account_id != null) params.billing_account_id = f.billing_account_id
  if (withUtility && f.utility_id != null) params.utility_id = f.utility_id
  if (f.data_da) params.data_da = f.data_da
  if (f.data_a) params.data_a = f.data_a
  params.limit = f.limit || 25
  params.offset = f.offset || 0
  if (f.order_by) {
    params.order_by = f.order_by
    params.order_dir = f.order_dir || 'desc'
  }
  return params
}
