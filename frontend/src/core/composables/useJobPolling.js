// Composable di POLLING dei job asincroni della coda lavori generica (C-6/C-7).
// Interroga a intervalli lo stato dei job accodati (es.
// GET /vendite/fatturazione/run/<job_id>/) finche' non raggiungono uno stato
// TERMINALE, poi notifica l'esito. Non bloccante: la pagina resta reattiva.
//
// Perche' un building block e non un setInterval inline:
//  - un solo posto per la disciplina di cleanup (onUnmounted + onDeactivated
//    sotto KeepAlive: mai timer orfani su tab in background);
//  - setTimeout RICORSIVO (non setInterval): il prossimo tick di un job parte
//    solo dopo che la sua risposta e' arrivata → nessun accavallamento di
//    richieste sullo stesso job su rete lenta;
//  - cap di sicurezza: se il worker non e' schedulato il job resta PENDING
//    all'infinito — il polling non deve girare per sempre, si ferma e avvisa
//    "ancora in coda".
//
// ⭐ DAL 2026-08-17 SEGUE PIU' JOB INSIEME (brief-fe-fatturazione-job-concorrenti).
// Prima `start()` SOSTITUIVA il job seguito («l'ultimo giro vince») e l'esito
// del precedente andava perso in silenzio: lotti prodotti, gruppi non serviti e
// falliti parziali sparivano senza che nulla lo dicesse. Non era una scelta, era
// il motivo per cui la pagina chiamante doveva bloccare TUTTO durante un giro.
// Ora i job vivono in una mappa e ognuno porta il PROPRIO contesto fino
// all'esito, cosi' il chiamante puo' attribuire cio' che riceve.
//
// ⚠️ `polling` resta un BOOLEANO (deriva dal conteggio): i consumer storici non
// cambiano di una riga. Chi ha bisogno della grana usa `nJobsInCorso`.
//
// ⚠️ A tetto raggiunto `start()` RIFIUTA (ritorna false) e non sostituisce: la
// sostituzione era il difetto, non un comportamento da conservare. Il default
// `maxConcurrent: 1` mantiene quindi «un giro per volta» SENZA perdere esiti.
//
// Uso:
//   const { start, stop, polling } = useJobPolling({
//     fetchStatus: (jobId) => getFatturazioneRun(jobId),
//     onDone: (stato, context) => { ...refresh... },
//     onTimeout: (context) => notify.info(...),
//     maxConcurrent: Infinity,          // opzionale: default 1
//   })
//   start(jobId, { gruppi, etichetta })  // dopo l'accodamento

import { computed, onActivated, onDeactivated, onUnmounted, ref } from 'vue'

// Stati terminali di default della coda lavori generica (dbops.coda_lavori):
// FATTO (ok), ERRORE (terminale), ANNULLATO (admin). PENDING/IN_CORSO = vivo.
const STATI_TERMINALI_DEFAULT = ['FATTO', 'ERRORE', 'ANNULLATO']

// Oltre questa soglia di job seguiti l'intervallo si allarga in proporzione.
// Senza tetto al numero di giri concorrenti il polling crescerebbe LINEARMENTE
// (un giro = una GET ogni 2s): con dieci giri sarebbero cinque richieste al
// secondo di chiacchiericcio. Allargando l'intervallo il carico resta piatto e
// l'unica cosa che cambia e' la prontezza della notizia, che su un giro di
// fatturazione lungo minuti non e' un prezzo.
const SOGLIA_INTERVALLO_SCALATO = 4

// Stagger fra i tick alla ripresa: rimettere in moto N job insieme produrrebbe
// una raffica di richieste simultanee proprio nell'istante in cui la pagina
// torna in primo piano e sta gia' ricaricando le sue liste.
const STAGGER_RIPRESA_MS = 250
const STAGGER_RIPRESA_MAX_MS = 2000

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
 * @param {(statoObj:Object, context:*) => void} [opts.onDone] - chiamato allo stato terminale (stato + contesto del job)
 * @param {(statoObj:Object, context:*) => void} [opts.onTick] - chiamato a ogni polling non terminale (progress UI)
 * @param {(context:*) => void} [opts.onTimeout] - chiamato se esaurito il budget di attesa senza terminare
 * @param {(stato:string) => boolean} [opts.isTerminal] - predicato stato terminale (default: FATTO/ERRORE/ANNULLATO)
 * @param {number} [opts.intervalMs=2000] - intervallo base tra i tick di un job
 * @param {number} [opts.maxAttempts=90] - cap di sicurezza (default ~3 min a 2s)
 * @param {number} [opts.maxConcurrent=1] - quanti job si seguono insieme (Infinity = nessun tetto)
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
    maxConcurrent = 1,
  } = opts

  // jobId → { timer, attesaMs, context, stato }. Mappa NON reattiva di
  // proposito: la reattivita' che serve al template e' il solo conteggio.
  const jobs = new Map()
  const nJobsInCorso = ref(0)
  const currentStato = ref(null)
  // Sospensione (tab in background): i timer si fermano ma la mappa resta —
  // e' la differenza fra «smetto di guardare» e «dimentico», e prima esisteva
  // solo la seconda.
  let sospeso = false

  // ⚠️ Il cap e' un BUDGET DI ATTESA, non un numero di tick. Con l'intervallo
  // che si allarga al crescere dei job, contare i tick allungherebbe il timeout
  // proprio quando i giri sono tanti: il tempo massimo prima di dire «ancora in
  // coda» deve restare lo stesso in ogni condizione.
  const budgetAttesaMs = maxAttempts * intervalMs

  const polling = computed(() => nJobsInCorso.value > 0)
  const canStart = computed(() => nJobsInCorso.value < maxConcurrent)

  // Scopo: riallinea il conteggio reattivo alla mappa (unica sorgente di verita').
  function sincronizza() {
    nJobsInCorso.value = jobs.size
  }

  // Scopo: intervallo effettivo, allargato in proporzione ai job seguiti.
  function intervalloCorrente() {
    const fattore = Math.max(1, Math.ceil(jobs.size / SOGLIA_INTERVALLO_SCALATO))
    return intervalMs * fattore
  }

  // Scopo: ferma il timer di un job senza toglierlo dalla mappa.
  function fermaTimer(job) {
    if (job.timer !== null) {
      clearTimeout(job.timer)
      job.timer = null
    }
  }

  // Scopo: schedula il prossimo tick di un job scalandone il budget di attesa.
  //        In sospensione non schedula nulla: ci pensa `resume()`.
  //        ⚠️ Idempotente per costruzione (`fermaTimer` prima di schedulare):
  //        un `resume()` mentre la fetch di un tick e' ancora in volo schedula
  //        un timer, e il tick al ritorno ne schedulerebbe un SECONDO —
  //        sovrascrivendo il riferimento senza cancellare il primo. Da li' in
  //        poi due catene di polling parallele per lo stesso job, che
  //        raddoppiano a ogni ciclo sospendi/riattiva.
  function schedula(jobId, delayMs = null) {
    const job = jobs.get(jobId)
    if (!job || sospeso) return
    fermaTimer(job)
    const attesa = delayMs === null ? intervalloCorrente() : delayMs
    job.attesaMs += attesa
    job.timer = setTimeout(() => tick(jobId), attesa)
  }

  // Scopo: smette di seguire UN job (o tutti, se invocata senza argomenti —
  //        firma compatibile con i lifecycle hook, che chiamano senza args).
  //        Idempotente.
  function stop(jobId) {
    if (jobId === null || jobId === undefined) {
      for (const job of jobs.values()) fermaTimer(job)
      jobs.clear()
      sincronizza()
      return
    }
    const job = jobs.get(jobId)
    if (!job) return
    fermaTimer(job)
    jobs.delete(jobId)
    sincronizza()
  }

  // Scopo: un singolo tick di UN job — legge lo stato, decide
  //        terminale/continua/timeout. Best-effort: un errore di rete non ferma
  //        il polling (ritenta al tick successivo), cosi' un colpo a vuoto non
  //        aborta un giro reale.
  async function tick(jobId) {
    const job = jobs.get(jobId)
    if (!job) return
    job.timer = null
    let statoObj
    try {
      statoObj = unwrap(await fetchStatus(jobId))
    } catch {
      statoObj = null
    }
    // Nel frattempo il job puo' essere stato fermato: l'identita' dell'oggetto
    // e' il controllo giusto (una `stop` + `start` sullo stesso id darebbe una
    // voce NUOVA, e il tick vecchio non deve parlare per lei).
    if (jobs.get(jobId) !== job) return

    if (statoObj) {
      job.stato = statoObj
      currentStato.value = statoObj
      if (typeof onTick === 'function') onTick(statoObj, job.context)
      if (isTerminal(statoObj.stato)) {
        const context = job.context
        stop(jobId)
        if (typeof onDone === 'function') onDone(statoObj, context)
        return
      }
    }

    if (job.attesaMs >= budgetAttesaMs) {
      const context = job.context
      stop(jobId)
      if (typeof onTimeout === 'function') onTimeout(context)
      return
    }
    schedula(jobId)
  }

  // Scopo: comincia a seguire `jobId`, portandosi dietro il `context` che
  //        tornera' identico nei callback (e' cio' che permette al chiamante di
  //        attribuire l'esito al giro giusto). Ritorna false se il job e' gia'
  //        seguito o se il tetto e' raggiunto — MAI sostituisce un giro vivo.
  //        Il primo tick e' schedulato (non immediato): il job appena accodato
  //        e' PENDING, dagli un intervallo.
  function start(jobId, context = null) {
    if (jobId === null || jobId === undefined) return false
    // Caso reale, non difensivo: sulla stessa chiave di idempotenza ancora viva
    // il BE restituisce l'id del job ESISTENTE invece di crearne uno nuovo.
    // Seguirlo due volte raddoppierebbe i timer e lo conterebbe due volte.
    if (jobs.has(jobId)) return false
    if (jobs.size >= maxConcurrent) return false
    jobs.set(jobId, { timer: null, attesaMs: 0, context, stato: null })
    currentStato.value = null
    sincronizza()
    schedula(jobId)
    return true
  }

  // Scopo: segue i LAVORI di un gesto solo — la risposta di un endpoint che
  //        accoda un lavoro per azienda (`[{ job_id, ... }]`, BE10 a del
  //        brief-db-revisione-dbops, 2026-11-07). `contestoDi(lavoro)` da' il
  //        contesto di ciascuno (quello che tornera' nei callback). Ritorna
  //        `{ seguiti, giaSeguiti, nonSeguiti }`, tre liste di lavori:
  //          - `seguiti`: presi in carico ADESSO — sono i soli di cui il
  //            chiamante puo' marcare le righe, perche' i soli di cui
  //            arrivera' un esito;
  //          - `giaSeguiti`: la dedup del BE ha restituito un lavoro ancora
  //            vivo che si stava gia' seguendo;
  //          - `nonSeguiti`: accodati ma rifiutati dal tetto — il lavoro parte
  //            lo stesso, l'esito qui non arriva.
  // ⭐ Estratto alla seconda occorrenza (cockpit competenza e lista Lotti,
  //    regola del 2, ok Tid 2026-11-07): il ciclo e' lo stesso, cambia solo
  //    cosa ciascuna vista marca. Le notifiche restano al chiamante: le parole
  //    sono del verbo, non del polling.
  // ⚠️ Una risposta senza `lavori` e' una lista vuota, non un errore: tre liste
  //    vuote dicono al chiamante che non c'e' niente da seguire.
  function seguiLavori(lavori, contestoDi = () => null) {
    const esito = { seguiti: [], giaSeguiti: [], nonSeguiti: [] }
    for (const lavoro of Array.isArray(lavori) ? lavori : []) {
      if (isFollowing(lavoro.job_id)) {
        esito.giaSeguiti.push(lavoro)
      } else if (start(lavoro.job_id, contestoDi(lavoro))) {
        esito.seguiti.push(lavoro)
      } else {
        esito.nonSeguiti.push(lavoro)
      }
    }
    return esito
  }

  // Scopo: sta gia' seguendo questo job? Serve al chiamante per distinguere
  //        «ne hai avviato un altro» da «e' lo stesso di prima».
  function isFollowing(jobId) {
    return jobs.has(jobId)
  }

  // Scopo: sospende i tick senza dimenticare i job (tab in background).
  function suspend() {
    if (sospeso) return
    sospeso = true
    for (const job of jobs.values()) fermaTimer(job)
  }

  // Scopo: riprende i job rimasti in sospeso, sfalsati nel tempo.
  //        ⚠️ `attesaMs` NON si azzera: il budget e' un cap sul tempo totale,
  //        e ripartire da zero a ogni rientro renderebbe possibile un job
  //        seguito per sempre.
  function resume() {
    if (!sospeso) return
    sospeso = false
    let i = 0
    for (const jobId of jobs.keys()) {
      schedula(jobId, Math.min(i * STAGGER_RIPRESA_MS, STAGGER_RIPRESA_MAX_MS))
      i += 1
    }
  }

  // Cleanup: smontato il componente si lascia tutto: i job proseguono lato
  // server. Sul tab KeepAlive messo in background NON si dimentica nulla: si
  // sospende, e al rientro si riprende.
  //
  // ⛔ LA RIPRESA STA QUI, E FINO AL 2026-08-27 NON C'ERA. Il BB si sospendeva
  //    da se' e lasciava il `resume()` alla view — un contratto che il secondo
  //    consumatore ha dimenticato, come era prevedibile: `DashboardCompetenzaView`
  //    lo chiamava, `LottiListView` no. Effetto su quest'ultima: bastava uscire
  //    dal tab e rientrare mentre un giro era in volo perche' i tick non
  //    ripartissero piu'. Il job restava nella mappa, `nJobsInCorso` restava a 1,
  //    e i due verbi «Rendi definitivi» restavano SPENTI per sempre — fino a un
  //    ricarico di pagina. Trovato in-app da Tid: «il pulsante non si sblocca,
  //    come se il lotto non avesse mai terminato».
  //
  // ⚠️ Il difetto e' silenzioso per costruzione: niente fallisce, nessun errore
  //    in console, e la lista si ricarica normalmente — l'unica cosa che manca
  //    e' un pulsante che si riaccende. Ricaricare la LISTA non serve (lo stato
  //    e' in memoria), ricaricare la PAGINA sana: e' la firma di questa classe
  //    di difetti.
  //
  // ⭐ L'asimmetria ERA il difetto: cio' che un BB si prende in carico da solo
  //    (`suspend`) deve avere il suo contrario nello stesso posto. Un contratto
  //    che si annota nel commento del composable viene rispettato dal primo che
  //    lo legge e dimenticato dal secondo (memoria `feedback_bb_legge_non_trasporta`).
  //
  // `resume()` e' idempotente (`if (!sospeso) return`), quindi le view che lo
  // chiamano gia' nel loro `onActivated` non fanno un secondo giro: quelle
  // chiamate diventano ridondanti, non sbagliate.
  onUnmounted(() => stop())
  onDeactivated(() => suspend())
  onActivated(() => resume())

  return {
    start,
    seguiLavori,
    stop,
    suspend,
    resume,
    isFollowing,
    polling,
    nJobsInCorso,
    canStart,
    // ⚠️ Significativo solo con `maxConcurrent: 1`: con piu' job e' l'ultimo
    // stato osservato, qualunque sia il job. Per la grana per-job usare il
    // `context` che arriva in onTick/onDone.
    currentStato,
  }
}
