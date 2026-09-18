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
//
// ⭐ Dal 2026-09-18 la lista e' `useListaStoreCore`, chiamato qui dentro: era
//    su `useListaEmptyStateFetch` + `buildDocListParams`, la convenzione dei
//    documenti scritta a parte — che era la STESSA forma del core con due
//    filtri in piu' aggiunti a mano. Non e' `createListaStore` perche' il
//    collegamento da soggetti/clienti scrive i filtri in blocco: e' logica di
//    dominio che sta bene accanto ai filtri, non in un `extend`.

import { defineStore } from 'pinia'

import { defaultFiltroDataDaString } from '../../core/utils/date'
import { useListaStoreCore } from '../../core/composables/useListaStoreCore'
import { listFatture } from '../api/fatture'

export const useFattureStore = defineStore('vendite-fatture', () => {
  // Floor temporale standard delle liste documento (oggi-60gg al primo del
  // mese): regola unica di progetto, non ricalcolata qui.
  const defaultDataDa = defaultFiltroDataDaString()

  // Lista con guardia empty-state standard: `data_da` col default standard
  // conta come filtro attivo (`gateKeys`), quindi la lista si popola al mount.
  // ⚠️ `id_fiscale` e' nei `gateKeys` e non basta il resto: arrivando dal
  //    collegamento il pavimento temporale viene TOLTO (vedi sotto), e senza
  //    questa voce un elenco filtrato per soggetto risulterebbe «senza filtri
  //    attivi» — cioe' non verrebbe caricato affatto.
  const lista = useListaStoreCore({
    fetchPage: listFatture,
    filterDefaults: {
      stato_codice_interno: null,
      billing_account_id: null,
      // ⭐ Identificativo fiscale, confronto ESATTO lato server. E' il criterio
      // con cui arriva il collegamento dalla lista SOGGETTI: un soggetto e' una
      // persona giuridica e puo' avere PIU' billing account, quindi «le sue
      // fatture» si raccolgono per codice fiscale / partita IVA, non per conto.
      id_fiscale: null,
      utility_id: null,
      // ⭐ Il filtro proprio del documento fiscale: separa cio' che incassi
      // (FATTURA) da cio' che restituisci (NOTA_CREDITO).
      natura_doc_codice: null,
      data_da: defaultDataDa,
      data_a: null,
    },
    gateKeys: [
      'stato_codice_interno', 'billing_account_id', 'id_fiscale', 'utility_id',
      'data_da', 'data_a',
    ],
    // Il piu' recente in cima, come le sorelle e come il default del backend;
    // il ripiego del verso segue.
    orderBy: 'data',
    orderDir: 'desc',
    orderDirDefault: 'desc',
  })
  const { filters, fetchList } = lista

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
    // Lista: TUTTO il core, non un sottoinsieme (`fetchSospesa` e
    // `erroreCaricamento` li leggono i BB di pagina con un guard `in store`).
    ...lista,
    applicaCollegamento, rimuoviCollegamento,
  }
}, { userScoped: true })
