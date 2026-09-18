// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
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
//        come il pannello). Su 403/401 `disponibile` diventa false e il
//        pulsante non compare — come il badge code per chi non ha l'area core.
//        ⭐ La RESA (`statoPallino`) sta in `core/utils/pallinoPresidi.js`,
//        pura e senza import: e' cio' che ha la spec, e importarla da qui
//        trascinerebbe store → auth → i18n → `localStorage` nel test.
//        ⭐ E il pannello «Processi automatici» lo TIENE AGGIORNATO: quando
//        ricarica i presidi, il pallino adotta quei numeri (sono gli stessi tre,
//        letti un istante fa) invece di aspettare il prossimo giro.
// ------------------------------------------------------------
import { computed, ref, watch } from 'vue'
import { getPresidiConteggi } from '../../amministrazione/api/amministrazione'
import { useProcessiAutomaticiStore } from '../../amministrazione/stores/processiAutomatici'
import { useRefreshPeriodico } from './useRefreshPeriodico'
import { statoPallino } from '../utils/pallinoPresidi'

// ⭐ 300 s e NON 60 come il badge code — deciso sul modello, non su una misura:
//    quello segue il drenatore (~1/min); qui la sorgente piu' rapida a catalogo
//    ha soglie di UN'ORA (le tre viste delle code) e il canale di riferimento e'
//    la giornaliera delle 07:00. Cinque minuti dicono la stessa cosa a un quinto
//    del costo, e il costo non e' nullo: ogni tick sono N `count(*)` su viste
//    che scandiscono cataloghi, da ogni scheda aperta.
export const PRESIDI_INTERVAL_MS = 300_000

export function usePresidiPolling() {
  const testata = ref(null)
  // Quando la testata e' stata letta l'ultima volta: e' nel tooltip, perche'
  // un verde senza ora e' un verde di cui non si sa l'eta'.
  const lettoAlle = ref(null)
  // false = endpoint negato (403/401): il pulsante non si mostra e il polling
  // non riparte piu', nemmeno al rientro in primo piano (predicato `abilitato`).
  const disponibile = ref(true)

  const pallino = computed(() => statoPallino(testata.value))

  function adotta(nuova) {
    testata.value = nuova
    lettoAlle.value = new Date()
  }

  const { avvia, ferma } = useRefreshPeriodico(
    async () => {
      try {
        const res = await getPresidiConteggi()
        adotta(res.data?.data ?? null)
      } catch (err) {
        const status = err?.response?.status
        if (status === 403 || status === 401) {
          disponibile.value = false
          ferma()
        }
        // Ogni altro errore mantiene l'ultimo valore: su un contatore
        // ambientale e' meglio di un pallino che sfarfalla a ogni colpo a vuoto.
      }
    },
    {
      intervalMs: PRESIDI_INTERVAL_MS,
      abilitato: () => disponibile.value,
      // Il pallino nascerebbe vuoto: il primo giro serve subito.
      subitoAlMount: true,
    },
  )

  // ⭐ Il pannello e' la lettura piu' fresca che ci sia: quando finisce di
  //    caricare i presidi (senza errore) il pallino adotta la SUA testata —
  //    `presidiTestata` dello store, stessa forma e stessa funzione lato BE —
  //    senza un secondo round-trip. Si guarda la transizione «caricamento →
  //    finito», non i numeri: una ricarica che torna identica aggiorna
  //    comunque l'ora. ⚠️ Lo store la da' `null` se la lettura e' fallita, e
  //    un `null` qui NON si adotta: si tiene l'ultimo valore buono, come per
  //    gli errori del proprio giro.
  const processi = useProcessiAutomaticiStore()
  watch(
    () => processi.presidiLoading,
    (loading, prima) => {
      if (prima && !loading && processi.presidiTestata) {
        adotta(processi.presidiTestata)
      }
    },
  )

  // Scopo: refresh immediato fuori cadenza. `avvia({subito:true})` rispetta da
  //        se' il guard `abilitato`.
  function refresh() {
    avvia({ subito: true })
  }

  return { testata, pallino, lettoAlle, disponibile, refresh, stop: ferma }
}
