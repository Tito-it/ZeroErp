// Scopo: client API per il profilo portale (namespace autenticato
// /api/v1/portale/profile/*). Usa l'istanza axios condivisa, che aggiunge
// automaticamente il JWT e gestisce il refresh.

import api from '../../core/api'

// Scopo: Avvia l'attivazione della veste SHOP per l'utente portale
// corrente (§8.4.3 stub PR-B, MVP reale in PR-C). Oggi risponde 501
// `E_SHOP_NON_DISPONIBILE` — il componente chiamante gestisce l'errore
// mostrando un messaggio "funzione in arrivo".
//
// TODO PR-C: quando il BE smettera' di rispondere 501 e l'endpoint
// iniziera' a creare token + identita, aggiungere `Idempotency-Key`
// header (UUID generato client-side) come gli altri POST che modificano
// stato — coerente con la policy idempotency BE.
export function attivaAccessoShop() {
  return api.post('/portale/profile/activate-shop/')
}
