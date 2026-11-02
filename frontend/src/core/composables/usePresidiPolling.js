// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL PALLINO DEI PRESIDI in topbar — «i controlli che devono restare
//        vuoti sono a posto?» — letto a cadenza lenta e continua dalla testata
//        `GET /amm-software/processi/presidi/conteggi/` (decisione #8 di Tid,
//        2026-09-18; piano-be-fe-osservabilita-pallino-e-superfici §2.3).
// Note: ⭐ E' il GEMELLO di `useQueueCountsPolling`: qui vive il solo DOMINIO
//        (quale endpoint, come si legge la testata, la politica sugli errori,
//        la resa del pallino); la macchina del timer e' il BB
//        `useRefreshPeriodico` (cadenza, sospensione a tab nascosta, ripresa
//        immediata, `abilitato` per lo spegnimento DEFINITIVO su 403/401).
//        ⛔ PERCHE' ESISTE: la giornaliera dei presidi a zero righe NON spedisce
//        (per scelta), quindi chi non riceve posta non sa se «va tutto bene» o
//        se non e' destinatario. Il pallino dice la prima cosa a chi ha
//        l'applicazione davanti — e per dirla deve essere visibile ANCHE a
//        zero: verde con lo zero, non nascosto.
//        ⚠️ Chi lo vede: chi passa la porta dell'endpoint (oggi `AdminAPIView`,
//        come il pannello). ⭐ Lo dice il chiamante PRIMA della chiamata
//        (`ammesso`, dalla topbar: `auth.isSuperAdmin`): fino al 2026-10-02 il
//        pallino PROVAVA l'endpoint per chiunque e si spegneva al 403, e ogni
//        operatore non amministratore lasciava a ogni accesso un falso
//        `security.admin_denied` nel log di sicurezza. Il 403/401 resta come
//        rete: un permesso tolto a sessione aperta spegne il pallino.
//        ⭐ La RESA (`statoPallino`) sta in `core/utils/pallinoPresidi.js`,
//        pura e senza import: e' cio' che ha la spec, e importarla da qui
//        trascinerebbe store → auth → i18n → `localStorage` nel test.
//        ⭐ E il pannello «Processi automatici» lo TIENE AGGIORNATO: quando
//        ricarica i presidi CONSEGNA quei numeri al pallino
//        (`adottaTestataPresidi`), invece di aspettare il prossimo giro.
// ------------------------------------------------------------
import { computed, ref } from 'vue'
import { getPresidiConteggi } from '../api/presidi'
import { useRefreshPeriodico } from './useRefreshPeriodico'
import { statoPallino } from '../utils/pallinoPresidi'
import { creaSegnale } from '../segnale'
import { adesso } from '../utils/date'
import { eAccessoNegato } from '../utils/apiError'

// ⭐ 300 s e NON 60 come il badge code — deciso sul modello, non su una misura:
//    quello segue il drenatore (~1/min); qui la sorgente piu' rapida a catalogo
//    ha soglie di UN'ORA (le tre viste delle code) e il canale di riferimento e'
//    la giornaliera delle 07:00. Cinque minuti dicono la stessa cosa a un quinto
//    del costo, e il costo non e' nullo: ogni tick sono N `count(*)` su viste
//    che scandiscono cataloghi, da ogni scheda aperta.
export const PRESIDI_INTERVAL_MS = 300_000

// Le istanze vive del pallino (una per topbar montata). Chi ha appena letto
// la stessa testata con un'altra strada la CONSEGNA qui, invece di essere
// letto da `core`: il verso della dipendenza e' amministrazione → core, mai il
// contrario (frontend-standards §«Confini fra domini»).
const adozioni = creaSegnale('adozione testata presidi')

// Scopo: consegna al pallino una testata letta altrove — oggi dal pannello
//        «Processi automatici», che la ricarica con i presidi. ⚠️ Una testata
//        `null` (lettura fallita) non si consegna: il pallino tiene l'ultimo
//        valore buono, come per gli errori del proprio giro.
export function adottaTestataPresidi(testata) {
  if (!testata) return
  adozioni.emetti(testata)
}

// `ammesso`: il chiamante dice se l'utente passa la porta dell'endpoint
// (getter, reattivo). Assente = si prova, e decide il 403.
export function usePresidiPolling({ ammesso = () => true } = {}) {
  const testata = ref(null)
  // Quando la testata e' stata letta l'ultima volta: e' nel tooltip, perche'
  // un verde senza ora e' un verde di cui non si sa l'eta'.
  const lettoAlle = ref(null)
  // L'endpoint ha risposto 403/401: il polling non riparte piu', nemmeno al
  // rientro in primo piano (predicato `abilitato`).
  const negato = ref(false)
  // false = non ammesso o negato: il pulsante non si mostra e non si chiama.
  const disponibile = computed(() => ammesso() && !negato.value)

  const pallino = computed(() => statoPallino(testata.value))

  function adotta(nuova) {
    testata.value = nuova
    lettoAlle.value = adesso()
  }

  const { avvia, ferma } = useRefreshPeriodico(
    async () => {
      try {
        const res = await getPresidiConteggi()
        adotta(res.data?.data ?? null)
      } catch (err) {
        if (eAccessoNegato(err)) {
          negato.value = true
          ferma()
        }
        // Ogni altro errore mantiene l'ultimo valore: su un contatore
        // ambientale e' meglio di un pallino che sfarfalla a ogni colpo a vuoto.
      }
    },
    {
      intervalMs: PRESIDI_INTERVAL_MS,
      abilitato: () => !negato.value,
      // La porta la giudica il BB (anche quando cambia a vista aperta).
      ammesso,
      // Il pallino nascerebbe vuoto: il primo giro serve subito.
      subitoAlMount: true,
    },
  )

  // ⭐ Il pannello «Processi automatici» e' la lettura piu' fresca che ci sia:
  //    quando ricarica i presidi consegna qui la SUA testata (stessa forma,
  //    stessa funzione lato BE) con `adottaTestataPresidi`, senza un secondo
  //    round-trip e senza che `core` conosca il suo store.
  adozioni.ascolta(adotta)

  // Scopo: refresh immediato fuori cadenza. `avvia({subito:true})` rispetta da
  //        se' il guard `abilitato`.
  function refresh() {
    avvia({ subito: true })
  }

  return { testata, pallino, lettoAlle, disponibile, refresh, stop: ferma }
}
