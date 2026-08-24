// Store Pinia della LISTA fatture — la settima del ciclo attivo.
//
// ⭐ Perché esiste: fino al 2026-08-24 la fattura era l'unico documento del
// ciclo attivo senza la sua lista, e si raggiungeva solo passando da un lotto,
// da un cruscotto o da un collegamento.
//
// ⚠️ SOLA LETTURA, e non è una svista: la fattura si produce dalla pipeline di
// fatturazione, non da un form. Niente `create`/`update`/`delete` — per questo
// non passa da `createCrudStore`, che quel contratto lo pretende.
//
// `userScoped: true` → reset al logout (autoResetPlugin): items e filtri di un
// utente non devono restare al successivo sullo stesso browser
// (memoria feedback_pinia_userscoped).

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { defaultFiltroDataDaString } from '../../core/utils/date'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { buildDocListParams, hasDocListActiveFilters } from '../_shared/listaDocumenti'
import { listFatture } from '../api/fatture'

export const useFattureStore = defineStore('vendite-fatture', () => {
  // Floor temporale standard delle liste documento (oggi-60gg al primo del
  // mese): regola unica di progetto, non ricalcolata qui.
  const defaultDataDa = defaultFiltroDataDaString()

  const filters = ref({
    search: '',
    stato_codice_interno: null,
    billing_account_id: null,
    // ⭐ Identificativo fiscale, confronto ESATTO lato server. È il criterio con
    // cui arriva il collegamento dalla lista SOGGETTI: un soggetto è una
    // persona giuridica e può avere PIÙ billing account, quindi «le sue
    // fatture» si raccolgono per codice fiscale / partita IVA, non per conto.
    id_fiscale: null,
    utility_id: null,
    // ⭐ Il filtro proprio del documento fiscale: separa ciò che incassi
    // (FATTURA) da ciò che restituisci (NOTA_CREDITO).
    natura_doc_codice: null,
    data_da: defaultDataDa,
    data_a: null,
    limit: 25,
    offset: 0,
    // Il più recente in cima, come le sorelle e come il default del backend.
    order_by: 'data',
    order_dir: 'desc',
  })

  const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
    filters,
    // ⚠️ `id_fiscale` va aggiunto qui e non basta il BB: arrivando dal
    // collegamento il pavimento temporale viene TOLTO (vedi sotto), e senza
    // questa voce un elenco filtrato per soggetto risulterebbe «senza filtri
    // attivi» — cioè non verrebbe caricato affatto.
    hasActiveFilters: (f) =>
      hasDocListActiveFilters(f, { withUtility: true }) || f.id_fiscale != null,
    // ⚠️ `natura_doc_codice` non è nella convenzione comune dei documenti
    // (`buildDocListParams`): è proprio di questo dominio e si aggiunge qui,
    // invece di allargare il BB per un caso solo.
    buildParams: (f, searchTerm) => ({
      ...buildDocListParams(f, searchTerm, { withUtility: true }),
      ...(f.natura_doc_codice ? { natura_doc_codice: f.natura_doc_codice } : {}),
      ...(f.id_fiscale ? { id_fiscale: f.id_fiscale } : {}),
    }),
    fetchPage: listFatture,
  })

  // Scopo: arrivo da un COLLEGAMENTO (lista soggetti o clienti) — applica il
  //        criterio e ricarica.
  //
  // ⛔ TOGLIE IL PAVIMENTO TEMPORALE, ed è la parte che conta. La lista nasce
  //    con `data_da` = oggi−60gg al primo del mese (regola di progetto delle
  //    liste documento), ma chi arriva da un cliente chiede «le SUE fatture»,
  //    non «le sue fatture recenti»: con il pavimento attivo un soggetto con
  //    documenti di sei mesi fa riceverebbe «Nessuna fattura» — cioè una
  //    risposta FALSA che non sembra un errore. Il filtro data resta a video e
  //    l'operatore può rimetterlo quando vuole.
  // ⚠️ Azzera anche gli altri criteri: un collegamento che eredita i filtri
  //    lasciati dall'ultima visita mostrerebbe un sottoinsieme senza dirlo.
  function applicaCollegamento({ billingAccountId = null, idFiscale = null } = {}) {
    filters.value.billing_account_id = billingAccountId
    filters.value.id_fiscale = idFiscale
    filters.value.search = ''
    filters.value.stato_codice_interno = null
    filters.value.natura_doc_codice = null
    filters.value.data_da = null
    filters.value.data_a = null
    filters.value.offset = 0
    return fetchList()
  }

  // Scopo: toglie il criterio di arrivo e rimette il pavimento standard — così
  //        la lista torna quella di sempre, non una lista senza data.
  function rimuoviCollegamento() {
    filters.value.billing_account_id = null
    filters.value.id_fiscale = null
    filters.value.data_da = defaultDataDa
    filters.value.offset = 0
    return fetchList()
  }

  return {
    filters, items, totalRecords, loading, hasSearched, fetchList,
    applicaCollegamento, rimuoviCollegamento,
  }
}, { userScoped: true })
