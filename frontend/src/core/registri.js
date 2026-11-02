// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ IL REGISTRO DI ISCRIZIONE — come un motore o `core` offre un punto
//        a cui i domini si agganciano SENZA che lui li nomini (decisione Tid,
//        2026-09-26, frontend-standards §«Confini fra domini»).
//
//        Chi possiede il registro ne definisce la forma e lo legge; ogni
//        dominio iscrive le PROPRIE voci dal suo `iscrizioni.js`, che
//        `main.js` carica all'avvio. Cosi' un dominio nuovo (acquisti) si
//        aggiunge scrivendo il suo file, senza toccare il motore.
//
// ⛔ Una chiave iscritta due volte e' un ERRORE all'avvio, non un «vince
//    l'ultimo»: due domini che rivendicano la stessa chiave sono un conflitto
//    del modello, e scoperto in silenzio diventerebbe un drawer sbagliato che
//    si apre a seconda dell'ordine di caricamento dei file.
// ⚠️ Una chiave NON iscritta risponde `null`: e' il caso normale di un
//    vocabolario aperto (un tipo che nessuna schermata sa ancora aprire), e
//    chi legge decide il degrado — di solito, nessun pulsante.
// ------------------------------------------------------------

// Scopo: crea un registro con nome (il nome compare solo negli errori).
export function creaRegistro(nome) {
  const voci = new Map()

  return Object.freeze({
    // Scopo: iscrive una voce. Chiave vuota o gia' presente = errore.
    iscrivi(chiave, voce) {
      if (!chiave) throw new Error(`Registro «${nome}»: chiave vuota`)
      if (voci.has(chiave)) throw new Error(`Registro «${nome}»: «${chiave}» iscritta due volte`)
      voci.set(chiave, voce)
    },
    // Scopo: la voce di una chiave, o `null` se nessuno l'ha iscritta.
    voce(chiave) {
      return chiave ? (voci.get(chiave) ?? null) : null
    },
    // Scopo: le chiavi iscritte, nell'ordine di iscrizione.
    chiavi() {
      return [...voci.keys()]
    },
  })
}

// Scopo: un PUNTO DI ESTENSIONE — come un registro, ma ogni chiave raccoglie
//        un ELENCO di contributi (piu' domini aggiungono qualcosa alla stessa
//        schermata). Ogni contributo ha una `chiave` propria, unica nel punto,
//        e un `ordine` facoltativo (default 100) che decide dove compare.
export function creaPuntiEstensione(nome) {
  const punti = new Map()

  return Object.freeze({
    contribuisci(punto, contributo) {
      if (!punto) throw new Error(`Estensioni «${nome}»: punto vuoto`)
      if (!contributo?.chiave) throw new Error(`Estensioni «${nome}»: contributo senza chiave in «${punto}»`)
      const elenco = punti.get(punto) ?? []
      if (elenco.some(c => c.chiave === contributo.chiave)) {
        throw new Error(`Estensioni «${nome}»: «${contributo.chiave}» contribuito due volte in «${punto}»`)
      }
      elenco.push(contributo)
      elenco.sort((a, b) => (a.ordine ?? 100) - (b.ordine ?? 100))
      punti.set(punto, elenco)
    },
    // Scopo: i contributi di un punto, in ordine; elenco vuoto se nessuno.
    contributi(punto) {
      return [...(punti.get(punto) ?? [])]
    },
  })
}
