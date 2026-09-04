// Store Pinia delle due code di lavoro Strumenti (coda lavori dbops /
// coda stampa outbox PDF), promosse a liste configurabili
// (<ListaConfigurabile codice="dbops.coda_lavori" | "vendite.fatture_stampa_coda">,
// ui.lista_definizione id 34/35 — 7° lotto, 2026-08-03). UNA factory per non
// duplicare l'interfaccia useSearchTable-compatibile
// (items/totalRecords/loading/filters/fetchList/hasSearched), come i gemelli
// resi (stores/resiCoda.js).
//
// I filtri di dominio (ambito miei/tutti, stato, range date col floor
// standard) restano con i NOMI della CodaFiltriToolbar condivisa
// (ambito/stato/dataDa/dataA — la toolbar muta l'oggetto per riferimento);
// qui si mappano ai query param del BE. L'ordinamento viaggia come
// `sort_by`/`sort_dir` (convenzione endpoint tracciamento, whitelist BE
// ELENCA_SORT_SQL / CODA_STAMPA_SORT_SQL).
//
// Semantica CODA: `alwaysFetch: true` — il lavoro pendente e' visibile al
// mount senza ricerca. userScoped: reset al logout (feedback_pinia_userscoped).

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { listCodaLavori, listCodaStampa } from '../../core/api/tracciamento'
import { defaultFiltroDataDa, toDateString } from '../../core/utils/date'

// Scopo: mappa filtri store → query param degli endpoint coda (limit/offset +
//        filtri opzionali + sort_by/sort_dir maiuscolo come da contratto BE).
function buildCodaParams(f) {
  const p = { limit: f.limit, offset: f.offset }
  if (f.ambito === 'tutti') p.ambito = 'tutti'
  if (f.stato) p.stato = f.stato
  if (f.dataDa) p.data_da = toDateString(f.dataDa)
  if (f.dataA) p.data_a = toDateString(f.dataA)
  // Interruttore «mostra archiviate»: le righe messe via sono nascoste di
  // default, e il parametro le chiede. ⛔ Il filtro sta nel BACKEND e non qui:
  // la lista è paginata lato server, filtrare a valle filtrerebbe solo la
  // pagina visibile.
  if (f.archiviate) p.archiviate = 1
  if (f.order_by) {
    p.sort_by = f.order_by
    p.sort_dir = f.order_dir === 'asc' ? 'ASC' : 'DESC'
  }
  return p
}

// Factory: crea uno store coda con l'interfaccia standard delle liste
// configurabili. `id` = id Pinia univoco; `fetchPage` = endpoint API;
// `orderBy` = preset del seed, che replica il default gia' applicato dal BE
// (la lista non si riordina sotto gli occhi dell'operatore al primo
// caricamento).
//
// ⛔ NESSUNO STATO PRESELEZIONATO, su nessuna delle due code (decisione di
//    Tid, 2026-09-04). Fino a quel giorno la coda lavori si apriva su
//    `IN_CORSO` — «la domanda primaria e' cosa sta girando ora» — e la scelta
//    ha smesso di reggere quando la scheda ha preso il verbo «Archivia»:
//    l'archiviazione vale SOLO su una riga non viva, quindi la scheda si
//    apriva esattamente sull'unico stato in cui quel verbo non puo' mai
//    applicarsi. ⚠️ Non e' un fatto dei dati di oggi (misurati: 83 righe, tutte
//    terminali, e la scheda ne mostrava zero): vale sempre, anche a coda
//    piena — un operatore non incontra mai una riga archiviabile finche' non
//    tocca il filtro. Un verbo dietro un filtro che lo esclude e' come non
//    averlo consegnato.
function createCodaJobsStore(id, fetchPage, { orderBy }) {
  return defineStore(id, () => {
    const filters = ref({
      ambito: 'miei',
      stato: null,
      // Floor temporale di default, regola unica di progetto (core/utils/date).
      dataDa: defaultFiltroDataDa(),
      dataA: null,
      // Le righe ARCHIVIATE sono nascoste di default: l'archiviazione serve a
      // togliere dall'elenco cio' che ha finito, e mostrarle sempre sarebbe
      // non averla. L'interruttore della toolbar le riporta a video.
      archiviate: false,
      limit: 25,
      offset: 0,
      order_by: orderBy,
      order_dir: 'desc',
    })

    // Quante righe l'archiviazione lascia FUORI dall'elenco, dichiarate dal BE
    // accanto alla lista. ⚠️ Senza questo numero «coda pulita» e «tre righe
    // messe via» si leggono uguali — ed e' proprio il caso in cui la
    // differenza conta. Zero quando le archiviate sono incluse: li' non c'e'
    // niente di nascosto da dichiarare.
    const archiviateCount = ref(0)

    const { items, totalRecords, loading, hasSearched, fetchList } =
      useListaEmptyStateFetch({
        filters,
        buildParams: buildCodaParams,
        fetchPage,
        alwaysFetch: true,
        // ⛔ L'hook vive nel BB e non nel `fetchPage`: li' fuori applicherebbe
        // il conteggio anche alle risposte SCARTATE dal guard anti-race, e il
        // numero racconterebbe un contesto diverso dalla lista sopra di se'.
        onPayload: (payload) => { archiviateCount.value = payload.archiviate_count ?? 0 },
      })

    return {
      items, totalRecords, loading, hasSearched, filters, fetchList,
      archiviateCount,
    }
  }, {
    userScoped: true,
  })
}

export const useCodaLavoriStore = createCodaJobsStore(
  'strumenti-coda-lavori', listCodaLavori, { orderBy: 'started_at' },
)
export const useCodaStampaStore = createCodaJobsStore(
  'strumenti-coda-stampa', listCodaStampa, { orderBy: 'data_update' },
)
