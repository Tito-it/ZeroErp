// Composable di POLLING PERIODICO dei conteggi code (badge top bar, FE-1 del
// brief gestione-code-lavori-stampa). Interroga GET tracciamento/code/conteggi/
// a cadenza LENTA e continua (non fino a uno stato terminale: e' un contatore
// ambientale, non il follow-up di un job — per quello c'e' useJobPolling).
//
// ⭐ DAL 2026-08-27 LA MACCHINA DEL TIMER NON VIVE PIU' QUI: e' il BB
//    `useRefreshPeriodico` (cadenza, setTimeout ricorsivo, sospensione a tab
//    nascosta con ripresa immediata, token di generazione contro le catene
//    parallele, cleanup). Erano DUE COPIE della stessa disciplina — questa e
//    quella nata per le liste delle code — e la seconda esisteva solo perche'
//    la prima non era riusabile. Qui resta il DOMINIO: quale endpoint, come si
//    leggono i conteggi, e la politica sugli errori.
// ⭐ E far scendere il secondo consumatore ha migliorato il BB, che e' il modo
//    in cui si vede se un'estrazione era giusta: sono nati `abilitato` (lo
//    spegnimento definitivo su 403, che senza guard si riaccendeva al rientro
//    in primo piano) e `subitoAlMount` (un contatore nasce vuoto, una lista no).
//
// Disciplina (P-3 chiuso):
//  - cadenza 60s: il worker drena ~1/min, una cadenza piu' fitta raddoppierebbe
//    le richieste per lo stesso numero. ⚠️ Le LISTE delle code stanno invece a
//    15s: quelle sono una vista aperta davanti a una persona, questo e' un
//    contatore ambientale che vive su ogni pagina;
//  - errori silenziosi (nessun toast a ogni tick): al primo 403/401 il polling
//    si SPEGNE (l'utente non ha l'area core → il badge non deve comparire);
//    gli errori di rete transitori mantengono l'ultimo valore noto.
//
// Uso (AppTopbar):
//   const { lavoriVivi, stampaVive, workerOk, disponibile, refresh } =
//     useQueueCountsPolling()

import { computed, ref } from 'vue'
import { getCodeConteggi } from '../api/tracciamento'
import { useRefreshPeriodico } from './useRefreshPeriodico'
import { eAccessoNegato } from '../utils/apiError'

const INTERVAL_MS = 60_000

// Scopo: predicati PURI sulla risposta conteggi — fonte unica condivisa con
//        chi la fetcha per conto proprio (CodeLavoroDrawer): vivi = PENDING +
//        IN_CORSO (D-C), worker ok = entrambi i drainer con run recente
//        (null = dato non ancora arrivato, niente falsi allarmi al 1° paint).
// ⭐ Gli stati «vivi» di una riga di coda: in attesa o in lavorazione. La
//    definizione sta QUI e non in tre posti, perche' e' la stessa cosa che il
//    badge conta e che la lista deve mostrare — e due letture della stessa coda
//    che non concordano sono gia' state un difetto (le liste ferme mentre il
//    badge si aggiornava, 2026-08-27).
// ⚠️ `IN_CORSO` da solo NON basta a dire «sta lavorando» all'operatore: i
//    drainer sono oneshot (partono, svuotano, escono) e quella finestra dura
//    millisecondi. Cio' che l'operatore vede — e che deve vedere — e' il tempo
//    che passa in `PENDING` fra l'accodamento e il tick del worker.
export const STATI_CODA_VIVI = ['PENDING', 'IN_CORSO']

// Scopo: la riga di coda e' ancora in lavorazione? (predicato PURO, per la
//        colonna «stato» delle liste code.)
export function rigaCodaViva(stato) {
  return STATI_CODA_VIVI.includes(stato)
}

export function contaVivi(conteggi, coda) {
  const c = conteggi?.[coda]
  return c ? (c.pending ?? 0) + (c.in_corso ?? 0) : 0
}

export function workerOkDaConteggi(conteggi) {
  const w = conteggi?.worker
  if (!w) return null
  return (w.coda_lavori?.attivo === true) && (w.coda_stampa?.attivo === true)
}

// `ammesso`: il chiamante dice se l'utente passa la porta dell'endpoint
// (getter, reattivo; dalla topbar: l'area `strumenti` non bloccata). ⭐ Dal
// 2026-10-02, come il pallino dei presidi: chi non ha l'area non chiama, invece
// di lasciare a ogni accesso un `security.permission_denied` nel log. Assente =
// si prova, e decide il 403.
export function useQueueCountsPolling({ ammesso = () => true } = {}) {
  const conteggi = ref(null)
  // L'endpoint ha risposto 403/401: il polling non riparte piu' — nemmeno
  // tornando in primo piano. E' nel predicato `abilitato` passato al BB:
  // senza, un rientro riaccenderebbe una catena su un endpoint che ha gia'
  // detto di no. Resta come rete: un permesso tolto a sessione aperta.
  const negato = ref(false)
  // false = non ammesso o negato: il badge non si mostra affatto.
  const disponibile = computed(() => ammesso() && !negato.value)

  const lavoriVivi = computed(() => contaVivi(conteggi.value, 'coda_lavori'))
  const stampaVive = computed(() => contaVivi(conteggi.value, 'coda_stampa'))
  const workerOk = computed(() => workerOkDaConteggi(conteggi.value))

  // ⭐ Dal 2026-08-27 la disciplina del timer NON e' piu' scritta qui: e'
  //    `useRefreshPeriodico` (cadenza, sospensione a tab nascosta con ripresa
  //    immediata, token di generazione contro le catene parallele, cleanup).
  //    Erano due copie della stessa macchina — questa e quella delle liste
  //    code — e la seconda e' nata proprio perche' la prima non era riusabile.
  // ⚠️ Qui resta cio' che e' DI QUESTO contatore: la politica sugli errori.
  //    403/401 = «non hai l'area core» → si spegne per sempre; ogni altro
  //    errore mantiene l'ultimo valore, che su un contatore ambientale e'
  //    meglio di un badge che sfarfalla a ogni colpo a vuoto.
  const { avvia, ferma } = useRefreshPeriodico(
    async () => {
      try {
        const res = await getCodeConteggi()
        conteggi.value = res.data?.data ?? null
      } catch (err) {
        if (eAccessoNegato(err)) {
          negato.value = true
          ferma()
        }
      }
    },
    {
      intervalMs: INTERVAL_MS,
      abilitato: () => !negato.value,
      // La porta la giudica il BB (anche quando cambia a vista aperta).
      ammesso,
      // Il badge nascerebbe vuoto: qui il primo giro serve subito.
      subitoAlMount: true,
    },
  )

  // Scopo: refresh immediato fuori cadenza (es. dopo un'azione dal drawer).
  //        `avvia({subito:true})` rispetta da se' il guard `abilitato`.
  function refresh() {
    avvia({ subito: true })
  }

  // Firma storica conservata: `stop()` era esposta e va lasciata tale.
  const stop = ferma

  return { conteggi, lavoriVivi, stampaVive, workerOk, disponibile, refresh, stop }
}
