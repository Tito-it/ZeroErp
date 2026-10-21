// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: L'elenco dei canali di incasso ATTIVI da mettere in una tendina.
// Note: ⭐ Estratto il 2026-08-28 alla rilettura critica (regola del 2): lo
//       chiedevano gia' in due — l'apertura di una distinta e la conferma di un
//       rimborso — con la stessa pagina, lo stesso filtro e lo stesso terzetto
//       di stati. La seconda copia e' il momento in cui una delle due smette di
//       aggiornarsi.
//       ⛔ I tre stati («ci sono» · «non ce ne sono» · «non li ho letti») li
//       tiene il BB `useLetturaTreStati`: qui resta solo la DOMANDA.
//       ⚠️ Si ricarica a ogni apertura di chi lo usa: un canale configurato un
//       minuto fa deve comparire senza ricaricare la pagina.
// ------------------------------------------------------------

import { RISULTATI, useLetturaTreStati } from '../../core/composables/useLetturaTreStati'
import { listEntiIncasso } from '../api/pagamenti'

// Quanti canali si chiedono in una volta. ⚠️ E' il MASSIMO che il backend
// accetta (`limit` max 200): una tendina di configurazione non si pagina, e
// se un giorno i canali superassero questo numero la tendina ne nasconderebbe
// una parte **senza dirlo** — e allora smette di essere una tendina.
const CANALI_PER_TENDINA = 200

export function useCanaliIncasso() {
  const { dati: canali, caricati, errore, loading, carica, azzera } = useLetturaTreStati(
    () => listEntiIncasso({ attivo: true, limit: CANALI_PER_TENDINA }),
    { estrai: RISULTATI, vuoto: [] },
  )
  return { canali, caricati, errore, loading, carica, azzera }
}
