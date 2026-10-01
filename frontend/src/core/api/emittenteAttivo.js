// Scopo: API dell'EMITTENTE ATTIVO — la scelta «dentro quale emittente sto
//        lavorando» (impersonazione di scope). Due chiamate:
//          - listEmittentiSelezionabili() → opzioni della combo di topbar;
//          - switchEmittenteAttivo()      → cambia e riceve l'access NUOVO.
//
//        Il POST riemette i token perche' l'emittente attivo vive in un claim
//        JWT: senza, la combo cambierebbe senza che i dati si restringano —
//        l'interfaccia che mente. Il refresh viaggia nel cookie HttpOnly
//        (lo legge e lo riscrive il backend); nel corpo torna l'access, che
//        chi chiama DEVE tenere prima di ricaricare.

import api from '../api'

// Scopo: emittenti fra cui l'utente puo' scegliere (gia' filtrati dal BE
//        sullo scope di diritto: l'operatore ne vede al piu' uno).
export async function listEmittentiSelezionabili() {
  const response = await api.get('/core/me/emittente-attivo/')
  return response.data?.data?.opzioni ?? []
}

// Scopo: cambia l'emittente attivo. `emittenteFiscaleId = null` significa
//        «Tutti gli emittenti» (modalita' di sola lettura).
//        Il refresh corrente lo porta il cookie: il BE lo riscrive col claim
//        aggiornato e verifica che appartenga a chi chiama.
export async function switchEmittenteAttivo(emittenteFiscaleId) {
  const response = await api.post('/core/me/emittente-attivo/', {
    emittente_fiscale_id: emittenteFiscaleId
  })
  return response.data?.data ?? null
}
