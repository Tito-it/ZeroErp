// Composable di POLLING PERIODICO dei conteggi code (badge top bar, FE-1 del
// brief gestione-code-lavori-stampa). Interroga GET tracciamento/code/conteggi/
// a cadenza LENTA e continua (non fino a uno stato terminale: e' un contatore
// ambientale, non il follow-up di un job — per quello c'e' useJobPolling).
//
// Disciplina (P-3 chiuso):
//  - cadenza 60s: il worker drena ~1/min, una cadenza piu' fitta raddoppierebbe
//    le richieste per lo stesso numero;
//  - setTimeout RICORSIVO (mai setInterval): il prossimo tick parte dopo la
//    risposta → nessun accavallamento su rete lenta;
//  - SOSPESO quando la tab del browser e' nascosta (visibilitychange): riprende
//    con un fetch immediato al ritorno — niente traffico da tab in background;
//  - errori silenziosi (nessun toast a ogni tick): al primo 403/401 il polling
//    si SPEGNE (l'utente non ha l'area core → il badge non deve comparire);
//    gli errori di rete transitori mantengono l'ultimo valore noto.
//
// Uso (AppTopbar):
//   const { lavoriVivi, stampaVive, workerOk, disponibile, refresh } =
//     useQueueCountsPolling()

import { computed, onUnmounted, ref } from 'vue'
import { getCodeConteggi } from '../api/tracciamento'

const INTERVAL_MS = 60_000

// Scopo: predicati PURI sulla risposta conteggi — fonte unica condivisa con
//        chi la fetcha per conto proprio (CodeLavoroDrawer): vivi = PENDING +
//        IN_CORSO (D-C), worker ok = entrambi i drainer con run recente
//        (null = dato non ancora arrivato, niente falsi allarmi al 1° paint).
export function contaVivi(conteggi, coda) {
  const c = conteggi?.[coda]
  return c ? (c.pending ?? 0) + (c.in_corso ?? 0) : 0
}

export function workerOkDaConteggi(conteggi) {
  const w = conteggi?.worker
  if (!w) return null
  return (w.coda_lavori?.attivo === true) && (w.coda_stampa?.attivo === true)
}

export function useQueueCountsPolling() {
  const conteggi = ref(null)
  // false = endpoint negato (403/401): il badge non si mostra affatto.
  const disponibile = ref(true)
  let timer = null
  let stopped = false
  // Token di generazione della catena di polling: refresh()/ritorno in
  // foreground possono partire mentre il fetch di un tick precedente è
  // ancora in-flight (timer è null proprio durante il fetch) — senza token
  // la continuazione async del vecchio tick rischedulerebbe il SUO timeout,
  // creando una seconda catena orfana che stop() non può più fermare
  // (polling raddoppiato per sempre). Ogni tick si autoproclama catena
  // corrente (++gen); una continuazione con gen stantio non rischedula.
  let gen = 0

  const lavoriVivi = computed(() => contaVivi(conteggi.value, 'coda_lavori'))
  const stampaVive = computed(() => contaVivi(conteggi.value, 'coda_stampa'))
  const workerOk = computed(() => workerOkDaConteggi(conteggi.value))

  function _clearTimer() {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  // Scopo: un tick — fetch e rischedula. 403/401 spegne il polling (endpoint
  //        non accessibile); altri errori mantengono l'ultimo valore.
  async function tick() {
    if (stopped) return
    const g = ++gen
    try {
      const res = await getCodeConteggi()
      conteggi.value = res.data?.data ?? null
    } catch (err) {
      const status = err?.response?.status
      if (status === 403 || status === 401) {
        disponibile.value = false
        stop()
        return
      }
    }
    if (stopped || document.hidden || g !== gen) return
    timer = setTimeout(tick, INTERVAL_MS)
  }

  // Scopo: sospende in background, riprende con fetch immediato al ritorno.
  function onVisibilityChange() {
    if (document.hidden) {
      _clearTimer()
    } else if (!stopped && disponibile.value && timer === null) {
      tick()
    }
  }

  function stop() {
    stopped = true
    _clearTimer()
    document.removeEventListener('visibilitychange', onVisibilityChange)
  }

  // Scopo: refresh immediato fuori cadenza (es. dopo un'azione dal drawer).
  function refresh() {
    if (stopped || !disponibile.value) return
    _clearTimer()
    tick()
  }

  document.addEventListener('visibilitychange', onVisibilityChange)
  tick()
  onUnmounted(stop)

  return { conteggi, lavoriVivi, stampaVive, workerOk, disponibile, refresh, stop }
}
