// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: l'`Idempotency-Key` di un GESTO, non di una chiamata. Un gesto
//        irreversibile (registrare, numerare, fatturare, cancellare) che va
//        in timeout lato client puo' essere arrivato in fondo lato server:
//        se l'operatore riclicca, deve partire la STESSA key, cosi' il
//        backend in modalita' forte (`handle_post_json(require_idempotency_key=True)`,
//        `dbops.idempotency_keys`) risponde con l'esito della prima esecuzione
//        (replay, 200 + `X-Idempotency-Replayed`) invece di rieseguire.
// Note: ⭐ Il ciclo di vita della key (approvato da Tid, 2026-10-21):
//         - nasce al primo invio del gesto;
//         - si RIUSA nei reinvii con lo STESSO payload (confronto per valore,
//           JSON a chiavi ordinate: `improntaStabile`);
//         - si AZZERA a successo, a payload cambiato (un payload diverso e'
//           un'operazione diversa), su `azzera()` — che il chiamante invoca
//           quando il contesto del gesto si chiude o si riapre (il dialog che
//           resta aperto sul rifiuto, per esempio) — e, come ultimo argine,
//           dopo `durataMs`: un reinvio e' tale se arriva a ridosso del primo.
//       ⚠️ Su un ERRORE la key resta: il server ha marcato la sua riga
//          `failed` e la stessa key RIESEGUE (`IdempotencyStore.claim_or_replay`),
//          mentre su un timeout o un 409 `E_IDEMPOTENCY_IN_PROGRESS` e'
//          proprio la key da rimandare.
//       ⛔ Una key per CHIAMATA resta la regola di `applicaIdempotencyKey`
//          (core/api.js): questo BB la scavalca passandola negli header, dove
//          «una key gia' presente vince». Serve SOLO dove il backend fa
//          claim/replay; altrove una key riusata non cambia nulla.
//       ⛔ E' UNA FACTORY: ogni chiamata ha il suo stato
//          (`feedback_estrarre_non_condividere_stato`).
// ------------------------------------------------------------
import { generateIdempotencyKey } from '../utils/idempotency'

export const HEADER_IDEMPOTENCY_KEY = 'Idempotency-Key'

// Oltre questa distanza dal primo invio un nuovo clic e' un gesto nuovo, non
// un reinvio: la key dimenticata dopo un timeout non deve trasformare, ore
// dopo, un gesto voluto nel replay di uno vecchio.
export const DURATA_GESTO_MS = 10 * 60 * 1000

// Scopo: l'impronta di un payload per confrontarlo PER VALORE. JSON con le
//        chiavi degli oggetti ordinate (l'ordine di scrittura non cambia
//        l'operazione); l'ordine degli array resta, e `undefined` vale come
//        chiave assente — come nel corpo che parte davvero.
export function improntaStabile(valore) {
  return JSON.stringify(valore ?? null, (_k, v) => {
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      return Object.keys(v).sort().reduce((acc, k) => {
        acc[k] = v[k]
        return acc
      }, {})
    }
    return v
  })
}

export function useChiaveGesto({ durataMs = DURATA_GESTO_MS, ora = () => Date.now() } = {}) {
  let chiave = null
  let impronta = null
  let nataAlle = 0

  function azzera() {
    chiave = null
    impronta = null
    nataAlle = 0
  }

  // Scopo: la key del gesto per QUESTO payload — la stessa del giro prima se
  //        il payload e' uguale e il gesto e' ancora vivo, una nuova altrimenti.
  function chiaveDi(payload) {
    const nuova = improntaStabile(payload)
    const scaduta = chiave !== null && durataMs > 0 && ora() - nataAlle > durataMs
    if (chiave === null || impronta !== nuova || scaduta) {
      chiave = generateIdempotencyKey()
      impronta = nuova
      nataAlle = ora()
    }
    return chiave
  }

  // Scopo: la config axios da passare alla funzione API.
  function configDi(payload) {
    return { headers: { [HEADER_IDEMPOTENCY_KEY]: chiaveDi(payload) } }
  }

  // Scopo: invia il gesto. `chiamata(config)` riceve la config con la key e
  //        ritorna la Promise axios; a successo la key si azzera, su errore
  //        resta e l'errore risale (a `useApiHandler.execute`, di solito).
  async function invia(payload, chiamata) {
    const risposta = await chiamata(configDi(payload))
    azzera()
    return risposta
  }

  return { invia, configDi, azzera }
}
