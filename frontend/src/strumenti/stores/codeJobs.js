// Store Pinia delle due code di lavoro Strumenti (coda lavori dbops /
// coda stampa outbox PDF), promosse a liste configurabili
// (<ListaConfigurabile codice="dbops.coda_lavori" | "vendite.fatture_stampa_coda">,
// ui.lista_definizione id 34/35 — 7° lotto, 2026-08-03). UNA factory per non
// duplicare l'interfaccia useSearchTable-compatibile
// (items/totalRecords/loading/filters/fetchList/hasSearched), come i gemelli
// resi (stores/resiCoda.js).
//
// I filtri di dominio (ambito miei/tutti, stato, periodo col floor standard)
// portano i NOMI di ogni altra lista — `data_da`/`data_a` in stringa ISO — e
// qui si mappano ai query param del BE.
// ⭐ Prima del 2026-09-23 si chiamavano `dataDa`/`dataA` e tenevano OGGETTI
//    `Date`: era l'unica coppia di date del prodotto fuori standard, e per
//    questo l'unica che non poteva passare da `bindPeriodo` — cioe' l'unica
//    senza l'invariante «`da > a` non puo' esistere» e senza il verso giusto
//    degli eventi (una data digitata a mano non applicava il filtro). L'ordinamento viaggia come
// `order_by`/`order_dir` come ogni altra lista (whitelist BE ELENCA_SORT_SQL /
// CODA_STAMPA_SORT_SQL). Fino al 2026-10-20 l'endpoint voleva `sort_by`/`sort_dir`.
//
// Semantica CODA: `alwaysFetch: true` — il lavoro pendente e' visibile al
// mount senza ricerca. userScoped: reset al logout (feedback_pinia_userscoped).

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { listCodaLavori, listCodaStampa } from '../../core/api/tracciamento'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'
import { defaultFiltroDataDaString } from '../../core/utils/date'
import { paramsOrdinamento } from '../../core/utils/listParams'
import { USO_MISURA, misuraDefault } from '../../core/misurePagina'

// Scopo: mappa filtri store → query param degli endpoint coda (limit/offset +
//        filtri opzionali + order_by/order_dir).
function buildCodaParams(f) {
  const p = { limit: f.limit, offset: f.offset }
  if (f.ambito === 'tutti') p.ambito = 'tutti'
  if (f.stato) p.stato = f.stato
  // ⚠️ Gia' in stringa ISO nello store (come ogni altra lista): qui non c'e'
  //    nessuna conversione da fare. Il null non parte affatto — axios omette i
  //    parametri nulli.
  if (f.data_da) p.data_da = f.data_da
  if (f.data_a) p.data_a = f.data_a
  // Interruttore «mostra archiviate»: le righe messe via sono nascoste di
  // default, e il parametro le chiede. ⛔ Il filtro sta nel BACKEND e non qui:
  // la lista è paginata lato server, filtrare a valle filtrerebbe solo la
  // pagina visibile.
  if (f.archiviate) p.archiviate = true
  return { ...p, ...paramsOrdinamento(f) }
}

// Factory: crea uno store coda con l'interfaccia standard delle liste
// configurabili. `id` = id Pinia univoco; `fetchPage` = endpoint API;
// `orderBy` = preset del seed, che replica il default gia' applicato dal BE
// (la lista non si riordina sotto gli occhi dell'operatore al primo
// caricamento).
// ⚠️ Lo stesso fatto vive quindi in TRE sedi che devono concordare: qui,
//    `ordinamento_default` del preset in `ui.lista_preset`, e il `default=`
//    del service. Cambiarne una sola non da' nessun errore: da' una lista che
//    si riordina da sola appena l'operatore tocca qualcosa.
// ⭐ Dal 2026-09-07 entrambe le code ordinano per `data_insert` — «quando e'
//    entrato in coda». Prima la coda lavori usava `started_at`, che un lavoro
//    in ATTESA non ha: finiva in fondo, dopo ogni lavoro mai avviato. Non era
//    filtrato, era sepolto.
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
    // ⭐ I FILTRI DI DOMINIO IN UNA SEDE SOLA (2026-09-23): da qui nascono i
    //    valori di partenza E il contratto che `FiltriLista` legge per il segno
    //    dei filtri attivi.
    const FILTRI_DEFAULT = {
      ambito: 'miei',
      stato: null,
      // Floor temporale di default, regola unica di progetto (core/utils/date).
      data_da: defaultFiltroDataDaString(),
      data_a: null,
      // Le righe ARCHIVIATE sono nascoste di default: l'archiviazione serve a
      // togliere dall'elenco cio' che ha finito, e mostrarle sempre sarebbe
      // non averla. L'interruttore della toolbar le riporta a video.
      archiviate: false,
    }

    const filters = ref({
      ...FILTRI_DEFAULT,
      limit: misuraDefault(USO_MISURA.PAGINA),
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

    // `lista`: lo stato del BB, esposto INTERO nel `return` (`...lista`).
    // ⛔ Non si elencano i suoi ref a mano: un ref nuovo del BB (com'e'
    //    successo con `ricercaFull`, `ricercaMinCaratteri`,
    //    `ricercaCambiaLaRichiesta`) arriverebbe solo agli store che lo
    //    ricordano — e senza errore sugli altri.
    const lista = useListaEmptyStateFetch({
      filters,
      buildParams: buildCodaParams,
      fetchPage,
      alwaysFetch: true,
      // ⛔ L'hook vive nel BB e non nel `fetchPage`: li' fuori applicherebbe
      // il conteggio anche alle risposte SCARTATE dal guard anti-race, e il
      // numero racconterebbe un contesto diverso dalla lista sopra di se'.
      onPayload: (payload) => { archiviateCount.value = payload.archiviate_count ?? 0 },
    })
    const { fetchList } = lista

    // Il contratto che `FiltriLista` legge: chi sono i filtri, com'erano alla
    // nascita, e come si riportano li' («Pulisci filtri»).
    // ⛔ IL VERSO DI `ambito` E' ROVESCIATO rispetto al filo, ed e' il motivo per
    //    cui il valore neutro qui si DICHIARA (2026-09-23): `buildCodaParams`
    //    manda il parametro SOLO quando vale «tutti» — quindi sul filo il
    //    silenzio e' «miei» — mentre nel dominio e' «miei» a restringere e
    //    «tutti» a non restringere niente. Senza questa riga il segno contava un
    //    filtro attivo proprio sull'ambito piu' largo.
    // ⭐ E `archiviate` e' la stessa cosa nell'altro verso, che il primo giro
    //    aveva mancato: `false` NASCONDE le righe archiviate (restringe, conta a
    //    ragione), `true` le include — cioe' l'elenco piu' largo che questa coda
    //    sappia mostrare. Un interruttore «mostra anche X» ha SEMPRE un valore
    //    neutro: e' quello acceso.
    const { chiaviFiltro, filtriDefault, filtriNeutri, azzeraFiltri } = useContrattoFiltriLista({
      filters,
      filterDefaults: FILTRI_DEFAULT,
      filtriNeutri: { ambito: 'tutti', archiviate: true },
      fetchList,
    })

    return {
      ...lista,
      filters,
      archiviateCount,
      chiaviFiltro, filtriDefault, filtriNeutri, azzeraFiltri,
    }
  }, {
    userScoped: true,
  })
}

export const useCodaLavoriStore = createCodaJobsStore(
  'strumenti-coda-lavori', listCodaLavori, { orderBy: 'data_insert' },
)
export const useCodaStampaStore = createCodaJobsStore(
  'strumenti-coda-stampa', listCodaStampa, { orderBy: 'data_insert' },
)
