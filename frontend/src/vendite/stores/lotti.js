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
// ⭐ L'endpoint lotti pagina con `limit`/`offset` come le altre liste (dal
// 2026-10-21, un dialetto solo: fino a quel giorno parlava `page`/`page_size`
// e `buildParams` traduceva).

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { paramsFinestra } from '../../core/utils/listParams'
import { listLotti } from '../api/lotti'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'
import { USO_MISURA, misuraDefault } from '../../core/misurePagina'

// Scopo: IL PERIMETRO DELLA PAGINA come query param, in una sede sola — mese,
//        stato e interruttore degli annullati, cioe' i tre filtri che valgono
//        per TUTTO cio' che la pagina chiede al backend: la lista, la scheda
//        «Recuperi» e i due export.
// ⛔ Estratta il 2026-09-12 (revisione) da QUATTRO copie che traducevano gli
//    stessi filtri negli stessi parametri: coincidevano, e il prossimo filtro
//    di perimetro ne avrebbe dimenticata una senza che niente fallisse — un
//    export con dentro cio' che la lista non mostra, o il contrario. E' la
//    specie di `feedback_bb_legge_non_trasporta`: i punti che trasportano si
//    contano, e qui ora e' uno.
// ⚠️ Pura: riceve l'oggetto dei filtri (lo store passa il suo, la view passa
//    `store.filters`) e non tocca niente. `annullati` viaggia come `1` — la
//    forma che `_parse_lotti_query` legge — e SOLO quando e' acceso: spento e'
//    il default del backend, e un parametro assente e uno falso devono
//    produrre la stessa lista.
export function paramsPerimetro(f) {
  return {
    ...(f.competenza_mese ? { competenza_mese: f.competenza_mese } : {}),
    ...(f.stato_lotto ? { stato_lotto: f.stato_lotto } : {}),
    ...(f.annullati ? { annullati: true } : {}),
  }
}

export const useLottiStore = defineStore('vendite-lotti', () => {
  // ⭐ I FILTRI DI DOMINIO IN UNA SEDE SOLA (2026-09-23): da qui nascono i valori
  //    di partenza della lista E il contratto che `FiltriLista` legge per il segno
  //    dei filtri attivi (`useContrattoFiltriLista`). ⛔ Due letterali divergono
  //    al primo filtro aggiunto da una parte sola, e il segno si spegnerebbe su
  //    una lista che filtra — senza nessun errore.
  const FILTRI_DEFAULT = {
    // La competenza e' SEMPRE valorizzata dalla view (sidebar anno/mese: non
    // esiste il caso "tutti i mesi"), ma nasce null perche' e' la view a
    // decidere quale mese mostrare all'apertura.
    competenza_mese: null,
    stato_lotto: null,
    // ⭐ I lotti ANNULLATI (fiscale abortito) restano FUORI dal perimetro di
    //    default (decisione Tid, 2026-09-12): un lotto annullato e' un guscio —
    //    fatture cancellate, attivita' rimesse «da emettere» — non lavoro.
    //    L'interruttore li rimette dentro OVUNQUE: lista, chip, calendario ed
    //    export leggono lo stesso filtro.
    // ⚠️ Il default e' `false`, non `null`: e' un valore, quindi conta nel
    //    segno dei filtri attivi come ogni altro filtro valorizzato.
    annullati: false,
  }

  const filters = ref({
    ...FILTRI_DEFAULT,
    // Non esposto al BE: l'endpoint lotti non ha ricerca testuale e
    // `buildParams` la ignora. La chiave esiste perche' fa parte del contratto
    // di `useSearchTable` (che la scrive su deep-link `?search=` e ricerca
    // universale): meglio dichiararla che farla nascere per assegnazione.
    search: '',
    limit: misuraDefault(USO_MISURA.PAGINA),
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

  // Quanti lotti annullati il perimetro corrente sta NASCONDENDO: senza questo
  // numero «mese pulito» e «tre lotti annullati» si leggono uguali. Lo produce
  // il BE sullo stesso `WHERE` della lista (stato compreso); a interruttore
  // acceso vale 0 — non c'e' niente di nascosto.
  const annullatiCount = ref(0)

  // `alwaysFetch: true`: il registro lotti non e' una lista che parte vuota in
  // attesa di una ricerca — e' la fotografia di un mese, e il mese c'e' sempre.
  // `lista`: lo stato del BB, esposto INTERO nel `return` (`...lista`).
  // ⛔ Non si elencano i suoi ref a mano: un ref nuovo del BB (com'e'
  //    successo con `ricercaFull`, `ricercaMinCaratteri`,
  //    `ricercaCambiaLaRichiesta`) arriverebbe solo agli store che lo
  //    ricordano — e senza errore sugli altri.
  const lista = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    // ⛔ Qui e non nel `fetchPage` qui sotto: il BB invoca l'hook DOPO il guard
    //    di versione, mentre tappare la promise applicherebbe i conteggi anche
    //    alle risposte scartate. Con la sidebar dei mesi si cambia periodo in
    //    fretta, quindi le fetch concorrenti sono la norma, non il caso limite:
    //    i pulsanti finirebbero a contare un mese diverso da quello a video.
    onPayload: (payload) => {
      stati.value = payload.stati ?? []
      annullatiCount.value = payload.annullati_count ?? 0
    },
    buildParams: (f) => {
      // La finestra via `paramsFinestra` (`core/utils/listParams`, nato il
      // 2026-08-28 come `paramsFinestra` alla terza sede: questa era la prima).
      // ⛔ `orderDirDefault: 'asc'` NON e' una svista da uniformare: e' il
      //    ripiego che questo store aveva, diverso da quello degli altri due
      //    consumatori (`desc`). Oggi non scatta — `order_dir` e' sempre
      //    valorizzato nei filtri — ma appianarlo avrebbe cambiato il verso di
      //    questa lista in silenzio il giorno in cui quel ramo si accendesse.
      return { ...paramsFinestra(f, { orderDirDefault: 'asc' }), ...paramsPerimetro(f) }
    },
    fetchPage: listLotti,
  })
  const { fetchList } = lista

  // Il contratto che `FiltriLista` legge: chi sono i filtri, com'erano alla
  // nascita, e come si riportano li' («Pulisci filtri»).
  // ⛔ `annullati: true` NON RESTRINGE, e va dichiarato (2026-09-23): spento
  //    (`false`, il default) i lotti annullati restano fuori — restringe, e
  //    conta a ragione; acceso il parametro parte (`annullati: true`) e l'elenco
  //    diventa il piu' largo possibile. Senza questa riga il segno contava un
  //    filtro proprio quando l'operatore aveva tolto la restrizione.
  const { chiaviFiltro, filtriDefault, filtriNeutri, azzeraFiltri } = useContrattoFiltriLista({
    filters,
    filterDefaults: FILTRI_DEFAULT,
    filtriNeutri: { annullati: true },
    fetchList,
  })

  return {
    ...lista,
    filters,
    stati, annullatiCount,
    chiaviFiltro, filtriDefault, filtriNeutri, azzeraFiltri,
  }
}, {
  userScoped: true,
})
