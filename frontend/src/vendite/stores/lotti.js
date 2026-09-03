// Store Pinia del registro lotti di fatturazione (lista configurabile
// `vendite.lotti`).
//
// PERCHE' ESISTE. La lista lotti nasceva con `usePagedDashFetch`, cioe' stato
// locale del componente. Il passaggio a `<ListaConfigurabile>` richiede il
// contratto store atteso da `useSearchTable` / `useListaConfigurabilePage`
// (`filters` con limit/offset/order_by/order_dir, `hasSearched`, `fetchList`,
// `items`, `totalRecords`, `loading`): senza, andrebbero riscritti a mano
// onPage/onSort/export/pageActions — cioe' duplicato il building block.
//
// userScoped: true → reset automatico al logout (autoResetPlugin): items e
// filtri dell'utente non devono sopravvivere all'utente successivo sullo stesso
// browser (memoria feedback_pinia_userscoped).
//
// ⚠️ L'endpoint lotti pagina con `page`/`page_size`, non con `limit`/`offset`:
// la conversione vive in `buildParams`, che e' il confine giusto. Lo store
// espone limit/offset perche' e' cio' che il BB manipola, e il BE riceve la sua
// forma: nessuno dei due si adatta all'altro.

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { PAGINATION } from '../../core/constants'
import { paramsPagina } from '../../core/utils/listParams'
import { listLotti } from '../api/lotti'

export const useLottiStore = defineStore('vendite-lotti', () => {
  const filters = ref({
    // La competenza e' SEMPRE valorizzata dalla view (sidebar anno/mese: non
    // esiste il caso "tutti i mesi"), ma nasce null perche' e' la view a
    // decidere quale mese mostrare all'apertura.
    competenza_mese: null,
    stato_lotto: null,
    // Non esposto al BE: l'endpoint lotti non ha ricerca testuale e
    // `buildParams` la ignora. La chiave esiste perche' fa parte del contratto
    // di `useSearchTable` (che la scrive su deep-link `?search=` e ricerca
    // universale): meglio dichiararla che farla nascere per assegnazione.
    search: '',
    limit: PAGINATION.DEFAULT_ROWS,
    offset: 0,
    // Default allineato all'ordine storico del BE (`fl.data_insert DESC`): la
    // lista si apre come si e' sempre aperta, il giro piu' recente in cima.
    order_by: 'data_insert',
    order_dir: 'desc',
  })

  // Ripartizione per stato del perimetro corrente — `[{stato_lotto, n_lotti}]`
  // — che alimenta i pulsanti-filtro sopra la lista.
  //
  // ⭐ Arriva ACCANTO a `results`/`count` nella stessa risposta, non da un
  //    endpoint suo: pulsanti e righe vengono dalla stessa valutazione del
  //    perimetro, quindi non possono raccontare due cose diverse.
  // ⚠️ Il BE lo calcola SENZA il filtro stato (mese e recuperi restano): e' cio'
  //    che permette di passare da uno stato all'altro con un click. Contando
  //    anche lo stato, scelto «BOZZA» gli altri pulsanti sparirebbero — si
  //    rendono solo sopra zero — e non ci sarebbe piu' modo di tornare indietro.
  const stati = ref([])

  // `alwaysFetch: true`: il registro lotti non e' una lista che parte vuota in
  // attesa di una ricerca — e' la fotografia di un mese, e il mese c'e' sempre.
  const { items, totalRecords, loading, hasSearched, fetchList } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    // ⛔ Qui e non nel `fetchPage` qui sotto: il BB invoca l'hook DOPO il guard
    //    di versione, mentre tappare la promise applicherebbe i conteggi anche
    //    alle risposte scartate. Con la sidebar dei mesi si cambia periodo in
    //    fretta, quindi le fetch concorrenti sono la norma, non il caso limite:
    //    i pulsanti finirebbero a contare un mese diverso da quello a video.
    onPayload: (payload) => { stati.value = payload.stati ?? [] },
    buildParams: (f) => {
      // limit/offset (lingua del BB) -> page/page_size (lingua dell'endpoint),
      // via `paramsPagina` (`core/utils/listParams`, estratto il 2026-08-28
      // alla terza sede: questa era la prima).
      // ⛔ `orderDirDefault: 'asc'` NON e' una svista da uniformare: e' il
      //    ripiego che questo store aveva, diverso da quello degli altri due
      //    consumatori (`desc`). Oggi non scatta — `order_dir` e' sempre
      //    valorizzato nei filtri — ma appianarlo avrebbe cambiato il verso di
      //    questa lista in silenzio il giorno in cui quel ramo si accendesse.
      const params = paramsPagina(f, { orderDirDefault: 'asc' })
      if (f.competenza_mese) params.competenza_mese = f.competenza_mese
      if (f.stato_lotto) params.stato_lotto = f.stato_lotto
      return params
    },
    fetchPage: listLotti,
  })

  return {
    items, totalRecords, loading, hasSearched, filters,
    stati,
    fetchList,
  }
}, {
  userScoped: true,
})
