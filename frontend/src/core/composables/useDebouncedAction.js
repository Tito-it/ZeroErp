// Scopo: ritardare un'azione finche' l'utente smette di digitare — e spegnere
//        il timer quando la pagina non c'e' piu'. Estratto 2026-08-17 (regola
//        del 2, ok Tid) dalla ricerca della lista gruppi fatturabili, seconda
//        occorrenza dopo `useSearchTable`.
//
// PERCHE' NON BASTAVA `useSearchTable`
// Quel composable fa il debounce, ma pretende uno store «ricerca + sort +
// limit» (`store.filters.search`, `store.fetchList()`): i tre cruscotti stanno
// su `usePagedDashFetch` e non possono consumarlo — e' la stessa ragione per cui
// e' nato `useListaAzioni`. Qui resta la sola meccanica del timer, senza
// ipotesi su cosa venga ritardato.
//
// ⚠️ IL PEZZO CHE SI DIMENTICA E' IL CLEANUP, non il timer.
// Un `setTimeout` lasciato vivo scatta su un componente smontato, o su un tab
// KeepAlive messo in background: l'azione parte quando nessuno la sta
// guardando, e se e' una fetch riscrive lo stato di una lista che l'operatore
// ha lasciato. Nessuno se ne accorge finche' non produce un dato incoerente a
// video. Il cleanup vive QUI perche' e' cio' che ogni copia scritta a mano si
// dimentica.
//
// Uso:
//   const cercaOra = useDebouncedAction(() => applicaFiltro())
//   <InputText v-model="search" @input="cercaOra()" />
//
//   // Con annullamento esplicito (es. «pulisci» che deve agire subito):
//   const { run, cancel, flush } = useDebouncedAction(applicaFiltro, { detailed: true })

import { onDeactivated, onUnmounted } from 'vue'

// Ritardo standard della ricerca a video (frontend-standards §Pattern lista:
// «Ricerca con debounce 400ms»). Stesso valore di `useSearchTable`: e' la
// costante che non deve divergere fra le due sedi.
export const SEARCH_DEBOUNCE_MS = 400

/**
 * @param {Function} azione - cosa eseguire a debounce scaduto
 * @param {Object} [opts]
 * @param {number} [opts.delayMs=SEARCH_DEBOUNCE_MS]
 * @param {boolean} [opts.detailed=false] - true ritorna {run, cancel, flush}, altrimenti la sola `run`
 * @returns {Function|{run: Function, cancel: Function, flush: Function}}
 */
export function useDebouncedAction(azione, { delayMs = SEARCH_DEBOUNCE_MS, detailed = false } = {}) {
  let timer = null
  // Ultimi argomenti ricevuti: `flush()` deve eseguire l'azione con quelli, non
  // a mani vuote — altrimenti un «cerca adesso» perderebbe il termine digitato.
  let ultimiArgs = []

  // Scopo: annulla un'esecuzione in attesa (idempotente).
  function cancel() {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  // Scopo: programma l'azione, sostituendo l'attesa precedente.
  function run(...args) {
    ultimiArgs = args
    cancel()
    timer = setTimeout(() => {
      timer = null
      azione(...ultimiArgs)
    }, delayMs)
  }

  // Scopo: esegue SUBITO cio' che era in attesa (es. invio con Enter). Se non
  //        c'e' nulla in attesa non fa nulla: non e' un «esegui comunque».
  function flush() {
    if (timer === null) return
    cancel()
    azione(...ultimiArgs)
  }

  // Mai un timer vivo su componente smontato o su tab KeepAlive in background.
  // ⚠️ `cancel` e non `flush`: l'azione ritardata va ABBANDONATA, non eseguita
  // in fretta mentre si esce. Eseguirla sarebbe la sorpresa peggiore — una
  // fetch che riscrive una lista che l'operatore ha appena lasciato.
  onUnmounted(cancel)
  onDeactivated(cancel)

  return detailed ? { run, cancel, flush } : run
}
