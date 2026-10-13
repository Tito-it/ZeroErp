// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Una lettura LEGATA A UN DOCUMENTO che vive dentro il drawer di quel
//        documento — i passaggi (lineage), la situazione merce — e che deve
//        restare allineata a cio' che il drawer ospite ha appena riletto.
// Note: ⭐ Estratto il 2026-10-13 (regola del 2, ok Tid). `useDocumentoPassaggi`
//       e `useSituazioneMerce` erano la stessa lettura scritta due volte, e il
//       difetto stava fuori da entrambe: dopo un'azione la RIlettura la doveva
//       chiedere ogni drawer a mano (`collegamentiRef.value?.reload()`), copiata
//       in cinque drawer e dimenticata in tre. Commessa annullata → i passaggi
//       mostravano ancora il preventivo EVASO (collaudo di Tid, 2026-10-13).
//
//       ⭐ IL SEGNALE E' `versione`: il dettaglio che il drawer ospite ha appena
//       letto (l'oggetto, non un suo campo). Ogni `loadDetail` assegna un
//       oggetto nuovo, quindi ogni rilettura del drawer — dopo un'azione, dopo
//       la chiusura di un documento collegato, o per una ragione che oggi non
//       esiste — rilegge anche qui, senza che nessuno se lo debba ricordare.
//
//       Le tre regole:
//         · cambia `docId`     → azzera (e scarta le risposte in volo): i dati
//                                di un altro documento non restano a video;
//         · cambia `versione`  → rilegge SENZA azzerare: il dato vecchio resta
//                                finche' arriva il nuovo, e la riga in testata
//                                non sparisce e ricompare a ogni azione;
//         · niente `versione`  → legge al cambio di `docId` (il caso in cui la
//                                lettura E' il dettaglio, es. CommessaDrawer).
//       ⚠️ In modalita' agganciata, al cambio di documento NON si legge se la
//       `versione` in mano e' quella gia' letta (del documento di prima): si
//       aspetta il dettaglio nuovo — cosi' l'apertura costa UNA lettura, non due.
//       Si legge invece se il dettaglio nuovo e' arrivato PRIMA dell'id (CREATE).
//
//       ⚠️ `useLetturaTreStati` non va bene qui: azzera a ogni `carica`, ed e'
//       giusto per lei (una lettura che riparte da capo) e sbagliato per un
//       refresh in testata. Il terzo stato vale comunque: su errore `caricati`
//       resta false finche' non e' mai arrivato niente — i consumer non devono
//       mai dire «nessun collegamento» su dati mai letti. Una RIlettura fallita
//       lascia il dato precedente (il toast lo alza `useApiHandler`).
// ------------------------------------------------------------

import { ref, toValue, watch } from 'vue'

import { useApiHandler } from './useApiHandler'
import { useFetchVersion } from './useFetchVersion'

// @param fetcher  (id) => Promise<response axios> — la GET del documento
// @param docId    ref/getter della pk di dominio (null in CREATE: niente lettura)
// @param versione ref/getter del dettaglio letto dal drawer ospite (facoltativo)
// @returns {{dati, caricati, loading, rileggi}}
export function useLetturaDocumento(fetcher, { docId, versione } = {}) {
  const dati = ref(null)
  const caricati = ref(false)
  const { execute, loading } = useApiHandler()
  const { tag, isCurrent, invalidate } = useFetchVersion()
  const agganciata = versione !== undefined

  // Scopo: legge il documento corrente; scrive solo se nel frattempo non e'
  //        partita una lettura piu' nuova o un cambio di documento.
  async function rileggi() {
    const id = toValue(docId)
    if (!id) return
    const mia = tag()
    const risposta = await execute(() => fetcher(id))
    if (!isCurrent(mia) || risposta === null) return
    dati.value = risposta
    caricati.value = true
  }

  // La versione su cui e' partita l'ultima lettura agganciata: si legge quando
  // quella in mano e' un'ALTRA. ⛔ Non il `vPrima` del watch: in CREATE il
  // dettaglio della bozza puo' arrivare PRIMA dell'id (a id ancora null non si
  // legge), e allora al cambio di id `vPrima` e' gia' il dettaglio nuovo — la
  // barra non leggerebbe piu' fino all'azione successiva. Senza documento si
  // azzera: il dettaglio che torna con lo stesso id va letto di nuovo.
  let versioneLetta

  watch(
    [() => toValue(docId), () => (agganciata ? toValue(versione) : null)],
    ([id, v], [idPrima] = []) => {
      const altroDocumento = id !== idPrima
      if (altroDocumento) {
        invalidate()
        dati.value = null
        caricati.value = false
      }
      if (!id) {
        versioneLetta = undefined
        return
      }
      if (!agganciata) {
        if (altroDocumento) rileggi()
        return
      }
      if (v != null && v !== versioneLetta) {
        versioneLetta = v
        rileggi()
      }
    },
    { immediate: true },
  )

  return { dati, caricati, loading, rileggi }
}
