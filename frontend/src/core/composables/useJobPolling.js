// Composable di POLLING di un job asincrono (coda lavori generica, C-6/C-7).
// Interroga a intervalli lo stato di un job accodato (es.
// GET /vendite/fatturazione/run/<job_id>/) finche' non raggiunge uno stato
// TERMINALE, poi notifica l'esito. Non bloccante: la pagina resta reattiva.
//
// Perche' un building block e non un setInterval inline:
//  - un solo posto per la disciplina di cleanup (onUnmounted + onDeactivated
//    sotto KeepAlive: mai timer orfani su tab in background);
//  - setTimeout RICORSIVO (non setInterval): il prossimo tick parte solo dopo
//    che la risposta e' arrivata → nessun accavallamento di richieste su rete
//    lenta;
//  - cap di sicurezza (maxAttempts): se il worker non e' schedulato il job
//    resta PENDING all'infinito — il polling non deve girare per sempre,
//    si ferma e avvisa "ancora in coda".
//
// Errori di rete durante il polling: silenziosi (nessun toast a ogni tick) —
// un colpo a vuoto non deve spammare; solo il timeout finale avvisa.
//
// Uso:
//   const { start, stop, polling } = useJobPolling({
//     fetchStatus: (jobId) => getFatturazioneRun(jobId),
//     onDone: (stato) => { ...refresh... },
//     onTimeout: () => notify.info(...),
//   })
//   start(jobId)   // dopo l'accodamento

import { onDeactivated, onUnmounted, ref } from 'vue'

// Stati terminali di default della coda lavori generica (dbops.coda_lavori):
// FATTO (ok), ERRORE (terminale), ANNULLATO (admin). PENDING/IN_CORSO = vivo.
const STATI_TERMINALI_DEFAULT = ['FATTO', 'ERRORE', 'ANNULLATO']

// Scopo: estrae il payload dall'envelope standard backend { data: { data } }
//        (o gia' unwrapped). Speculare a useApiHandler.
function unwrap(response) {
  const body = response && typeof response === 'object' && 'data' in response
    ? response.data
    : response
  return (body && typeof body === 'object' && 'data' in body) ? body.data : body
}

/**
 * @param {Object} opts
 * @param {(jobId:number|string) => Promise<*>} opts.fetchStatus - ritorna la Promise axios dello stato job
 * @param {(statoObj:Object) => void} [opts.onDone] - chiamato allo stato terminale (riceve il dict stato)
 * @param {(statoObj:Object) => void} [opts.onTick] - chiamato a ogni polling non terminale (progress UI)
 * @param {() => void} [opts.onTimeout] - chiamato se superato maxAttempts senza terminare
 * @param {(stato:string) => boolean} [opts.isTerminal] - predicato stato terminale (default: FATTO/ERRORE/ANNULLATO)
 * @param {number} [opts.intervalMs=2000] - intervallo tra i tick
 * @param {number} [opts.maxAttempts=90] - cap di sicurezza (default ~3 min a 2s)
 */
export function useJobPolling(opts) {
  const {
    fetchStatus,
    onDone,
    onTick,
    onTimeout,
    isTerminal = (stato) => STATI_TERMINALI_DEFAULT.includes(stato),
    intervalMs = 2000,
    maxAttempts = 90,
  } = opts

  const polling = ref(false)
  const currentStato = ref(null)
  let timer = null
  let attempts = 0
  let activeJobId = null

  // Scopo: ferma il polling e libera il timer (idempotente).
  function stop() {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
    polling.value = false
    activeJobId = null
  }

  // Scopo: un singolo tick — legge lo stato, decide terminale/continua/timeout.
  //        Best-effort: un errore di rete non ferma il polling (ritenta al tick
  //        successivo), cosi' un colpo a vuoto non aborta un giro reale.
  async function tick(jobId) {
    // Se nel frattempo e' stato fermato o rimpiazzato da un nuovo job, esci.
    if (jobId !== activeJobId) return
    attempts += 1
    let statoObj
    try {
      statoObj = unwrap(await fetchStatus(jobId))
    } catch {
      statoObj = null
    }
    if (jobId !== activeJobId) return

    if (statoObj) {
      currentStato.value = statoObj
      if (typeof onTick === 'function') onTick(statoObj)
      if (isTerminal(statoObj.stato)) {
        stop()
        if (typeof onDone === 'function') onDone(statoObj)
        return
      }
    }

    if (attempts >= maxAttempts) {
      stop()
      if (typeof onTimeout === 'function') onTimeout()
      return
    }
    timer = setTimeout(() => tick(jobId), intervalMs)
  }

  // Scopo: avvia il polling di `jobId`. Un eventuale polling in corso viene
  //        sostituito (l'ultimo giro vince). Il primo tick e' schedulato (non
  //        immediato): il job appena accodato e' PENDING, dagli un intervallo.
  function start(jobId) {
    stop()
    if (jobId === null || jobId === undefined) return
    activeJobId = jobId
    attempts = 0
    currentStato.value = null
    polling.value = true
    timer = setTimeout(() => tick(jobId), intervalMs)
  }

  // Cleanup: mai lasciare un timer vivo su componente smontato o tab KeepAlive
  // messo in background (onDeactivated). Il job prosegue lato server; alla
  // riattivazione il refresh dei dati mostra comunque l'avanzamento.
  onUnmounted(stop)
  onDeactivated(stop)

  return { start, stop, polling, currentStato }
}
