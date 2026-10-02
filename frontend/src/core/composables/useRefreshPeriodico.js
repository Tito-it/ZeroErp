// Copyright (C) 2026 Michele Carlo Titini
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

// Scopo: ri-eseguire un'azione a intervalli finche' la pagina e' DAVANTI
//        all'operatore, e smettere appena non lo e' piu'.
//
// Nasce per le due schede delle code (lavori e stampa), che mostravano una
// FOTOGRAFIA: caricavano al montaggio e al «Ricarica» a mano, e nient'altro.
// Nel frattempo, un piano piu' su, il badge della topbar si aggiornava da solo
// ogni 60s (`useQueueCountsPolling`) — quindi l'applicazione dava DUE letture
// della stessa coda, una viva e una congelata: il badge poteva dire «2 lavori
// vivi» mentre la lista sotto, aperta da cinque minuti, non mostrava niente.
// ⭐ Una vista di coda che non si aggiorna non e' una vista di coda: e' una
//    fotografia — e il difetto si attribuisce al sistema («la stampa non
//    parte») invece che alla finestra che lo racconta.
//
// ⛔ IL CICLO DI VITA STA TUTTO QUI, ed e' una lezione pagata due volte nella
//    stessa giornata (2026-08-27). `useJobPolling` si sospendeva da se' su
//    `onDeactivated` e lasciava il `resume()` alla view: il primo consumatore
//    lo chiamava, il secondo se l'e' dimenticato, e i verbi «Rendi definitive»
//    restavano spenti per sempre. Qui non c'e' niente da ricordarsi: chi usa
//    questo composable lo invoca e basta.
//    ⚠️ Regola generale: cio' che un building block si prende in carico da solo
//    deve avere il suo CONTRARIO nello stesso posto. Un contratto annotato nel
//    commento lo rispetta il primo che lo legge e lo dimentica il secondo.
//
// Tre modi di «non essere davanti», e si presidiano tutti e tre:
//   · il tab del BROWSER passa in background  → `visibilitychange`
//   · la scheda applicativa passa in background (KeepAlive) → `onDeactivated`
//   · il componente muore → `onUnmounted`
// Al ritorno in primo piano si riparte con un giro IMMEDIATO: chi torna
// a guardare vuole il dato di adesso, non fra un intervallo.
//
// Uso:
//   useRefreshPeriodico(() => load({ silent: true }))
//
// ⚠️ L'azione va passata SILENZIOSA dove esiste l'opzione (`fetchList({silent})`):
//    una maschera di caricamento che lampeggia ogni pochi secondi su una lista
//    che si sta leggendo e' peggio del dato stantio che va a correggere.

import { nextTick, onActivated, onDeactivated, onMounted, onUnmounted, watch } from 'vue'

// 15s: e' una lista aperta DAVANTI a una persona, non un contatore ambientale.
// Il badge della topbar sta a 60s perche' vive su ogni pagina; qui la vista e'
// una sola e alla volta, quindi il carico resta quello di una richiesta ogni
// quindici secondi — e i due drainer girano a 1 e 2 minuti, quindi piu' fitto
// di cosi' non porterebbe nessuna notizia in piu'.
const INTERVAL_MS = 15_000

// Opzioni:
//   intervalMs     cadenza (default 15s)
//   abilitato      () => bool — finche' risponde false NON si gira e NON si
//                  riparte. Serve allo spegnimento DEFINITIVO: il badge delle
//                  code, su 403/401, smette per sempre, e senza questo guard un
//                  rientro in primo piano (o un `onActivated`) lo riaccenderebbe
//                  su un endpoint che ha gia' detto di no.
//                  ⭐ Non c'era nella prima stesura: e' emerso facendo scendere
//                  qui il secondo consumatore, ed e' precisamente cio' che
//                  serve a far collassare due copie — la seconda porta il caso
//                  che la prima non aveva.
//   subitoAlMount  un primo giro IMMEDIATO al montaggio (default false). Le
//                  liste caricano gia' per conto loro e non lo vogliono; un
//                  contatore che nasce vuoto si'.
//   ammesso        () => bool, REATTIVO — il chiamante dice PRIMA della
//                  chiamata se l'utente passa la porta dell'endpoint (un
//                  profilo, un'area). Finche' e' falso non si gira, come con
//                  `abilitato`; a differenza di `abilitato` NON e' definitivo:
//                  diventato vero (il profilo arriva dopo il montaggio, cambia
//                  la veste) si parte con un giro immediato, diventato falso ci
//                  si ferma. ⭐ Dal 2026-10-02 (regola del 2, ok Tid): era
//                  scritto uguale nel pallino dei presidi e nel badge delle
//                  code, che prima provavano l'endpoint per chiunque e si
//                  spegnevano al 403 — ogni non ammesso lasciava a ogni accesso
//                  un falso «accesso negato» nel log di sicurezza.
export function useRefreshPeriodico(azione, {
  intervalMs = INTERVAL_MS,
  abilitato: abilitatoDalChiamante = () => true,
  subitoAlMount = false,
  ammesso = () => true,
} = {}) {
  // Il guard di ogni giro: la porta (`ammesso`) e lo spegnimento definitivo
  // (`abilitato`) insieme. Tutto il resto del BB legge solo questo.
  const abilitato = () => ammesso() && abilitatoDalChiamante()
  // La vista e' montata e davanti (non sotto KeepAlive in background): un
  // `ammesso` che diventa vero fuori da qui non deve accendere una catena che
  // `onDeactivated`/`onUnmounted` hanno appena spento.
  let inVista = false

  let timer = null
  let vivo = false
  // Token di generazione: `refresh()` o un ritorno in primo piano possono
  // partire mentre l'azione di un tick precedente e' ancora in volo (li'
  // `timer` e' gia' null). Senza token la continuazione async del tick vecchio
  // ri-schedulerebbe il SUO timeout, lasciando due catene parallele che
  // `stop()` non puo' piu' fermare — il polling raddoppia e non torna
  // indietro. Stessa difesa di `useQueueCountsPolling`, stessa ragione.
  let gen = 0

  // Scopo: spegne il timer senza dichiarare morta la catena.
  function fermaTimer() {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  // Scopo: un giro — esegue l'azione e ri-schedula, se nel frattempo nulla e'
  //        cambiato. Best-effort: un errore di rete non spegne la catena, si
  //        ritenta al giro dopo. L'errore lo mostra il «Ricarica» a mano, che
  //        e' il gesto in cui l'operatore si aspetta una risposta.
  async function tick() {
    timer = null
    if (!vivo || !abilitato()) return
    const g = ++gen
    try {
      await azione()
    } catch {
      // Silenzio voluto: un refresh di sfondo che apre un toast a ogni colpo a
      // vuoto trasformerebbe una rete incerta in una pioggia di avvisi.
    }
    if (!vivo || !abilitato() || document.hidden || g !== gen) return
    timer = setTimeout(tick, intervalMs)
  }

  // Scopo: (ri)avvia la catena. `subito` fa un giro immediato — e' il caso del
  //        ritorno in primo piano.
  function avvia({ subito = false } = {}) {
    if (!abilitato()) return
    vivo = true
    fermaTimer()
    if (document.hidden) return
    if (subito) {
      tick()
      return
    }
    timer = setTimeout(tick, intervalMs)
  }

  // Scopo: ferma la catena. Idempotente.
  function ferma() {
    vivo = false
    fermaTimer()
  }

  function onVisibilityChange() {
    if (document.hidden) {
      fermaTimer()
      return
    }
    if (vivo && abilitato() && timer === null) tick()
  }

  // ⛔ Sotto KeepAlive `onActivated` scatta ANCHE al primo mount, subito dopo
  //    `onMounted` e nello stesso flush. Senza guard il giro immediato della
  //    riattivazione partirebbe gia' li', cioe' la seconda richiesta identica a
  //    un millisecondo dalla prima — esattamente cio' che `subitoAlMount:false`
  //    esiste per evitare.
  // ⚠️ Il flag si spegne in `nextTick` e non in fondo a `onMounted`: i due hook
  //    sono nello stesso flush, quindi spegnerlo subito lo renderebbe inutile.
  //    E' il guard canonico del progetto, lo stesso di `useLazyTabLoad`.
  let avviatoDalMount = false
  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibilityChange)
    inVista = true
    avviatoDalMount = true
    // Di norma NESSUN giro immediato: il caricamento iniziale lo fa gia' la
    // view. `subitoAlMount` e' per chi non ha un altro caricamento (un
    // contatore che nascerebbe vuoto).
    avvia({ subito: subitoAlMount })
    nextTick(() => { avviatoDalMount = false })
  })
  onActivated(() => {
    inVista = true
    if (avviatoDalMount) return
    avvia({ subito: true })
  })
  onDeactivated(() => {
    inVista = false
    ferma()
  })
  onUnmounted(() => {
    inVista = false
    ferma()
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })

  // La porta che cambia a vista aperta: vero → si parte subito, falso → ci si
  // ferma. `avvia` rispetta da se' anche `abilitato` (un 403 gia' preso resta).
  watch(() => ammesso(), (ora) => {
    if (!inVista) return
    if (ora) avvia({ subito: true })
    else ferma()
  })

  return { avvia, ferma }
}
