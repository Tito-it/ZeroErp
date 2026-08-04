// Scopo: API dell'EMITTENTE ATTIVO — la scelta «dentro quale emittente sto
//        lavorando» (impersonazione di scope). Due chiamate:
//          - listEmittentiSelezionabili() → opzioni della combo di topbar;
//          - switchEmittenteAttivo()      → cambia e riceve token NUOVI.
//
//        Il POST restituisce access+refresh rigenerati perche' l'emittente
//        attivo vive in un claim JWT: senza sostituire i token, la combo
//        cambierebbe senza che i dati si restringano — l'interfaccia che
//        mente. Chi chiama DEVE salvare i token prima di ricaricare.

import api from '../api'

// Scopo: emittenti fra cui l'utente puo' scegliere (gia' filtrati dal BE
//        sullo scope di diritto: l'operatore ne vede al piu' uno).
export async function listEmittentiSelezionabili() {
  const response = await api.get('/core/me/emittente-attivo/')
  return response.data?.data?.opzioni ?? []
}

// Scopo: cambia l'emittente attivo. `emittenteFiscaleId = null` significa
//        «Tutti gli emittenti» (modalita' di sola lettura).
//        Il refresh token corrente e' obbligatorio: il BE ne emette una coppia
//        nuova col claim aggiornato e verifica che appartenga a chi lo invia.
export async function switchEmittenteAttivo(emittenteFiscaleId, refreshToken) {
  const response = await api.post('/core/me/emittente-attivo/', {
    emittente_fiscale_id: emittenteFiscaleId,
    refresh: refreshToken
  })
  return response.data?.data ?? null
}
