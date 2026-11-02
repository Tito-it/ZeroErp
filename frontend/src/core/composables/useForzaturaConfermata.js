// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il doppio tempo «rifiuto parlante → conferma → ripeti» — cioe' il
//        gesto che il database ammette solo se qualcuno lo conferma.
// Note: ⭐ Astrae un COMPORTAMENTO, non un elenco di codici: riconosce
//       l'`ui_action` **`confirm_and_retry`** (Q-1 del brief incassi, decisione
//       di Tid 2026-08-24). ⛔ Un elenco di codici nel frontend costa zero oggi
//       e se lo dimentica qualcuno al terzo codice — e li' l'operatore resta
//       BLOCCATO su un caso che il dominio dichiara ammesso.
//
//       Il giro, lato database:
//         1° tentativo, senza la dichiarazione -> RIFIUTATO, con la ragione
//         2° tentativo, con la dichiarazione   -> ACCETTATO
//       La DICHIARAZIONE e' del dominio, e la passa il chiamante a `conferma`:
//         - pagamenti (`E_RIGA_CONTABILE_CAPIENZA_SUPERATA`): `forzata` + motivo
//           (`forzaturaConMotivo`), che resta scritto sulla riga;
//         - amministrazione (`E_CREDENZIALE_DA_CONFERMARE`, dal 2026-09-27):
//           `riusa_auth_user_id`, l'id della credenziale che l'admin ha visto.
//       ⭐ Generalizzato il 2026-09-27 (regola del 2, ok Tid): prima `conferma`
//       riceveva il solo motivo e componeva lei `{forzata, motivo_forzatura}`,
//       cioe' parlava la lingua dei pagamenti.
//
//       ⛔ NON e' un pattern proponi/approva: nessun permesso, nessun secondo
//       operatore, un tempo solo.
//       ⚠️ Il primo tentativo si manda SEMPRE senza dichiarazione: dichiarare al
//       primo colpo «per semplificare» significa nascondere invece di chiedere.
// ------------------------------------------------------------

import { ref } from 'vue'

import { useApiHandler } from './useApiHandler'

// L'unica `ui_action` che questo BB riconosce. ⚠️ Vive qui e non nel dominio:
// e' il vocabolario trasversale delle `ui_action`, non una parola di pagamenti.
export const CONFERMA_E_RIPETI = 'confirm_and_retry'

// Scopo: esegue un gesto che il database puo' rifiutare in modo CONFERMABILE.
// @returns {{esegui, conferma, annulla, richiestaConferma, loading, campiErrati}}
//
// Uso:
//   const { esegui, richiestaConferma, conferma, annulla } = useForzaturaConfermata()
//   await esegui((extra) => abbinaRiga(id, { ...payload, ...extra }),
//                { successMessage: t('...') })
//   // se `richiestaConferma` si valorizza, il chiamante mostra la domanda con
//   // `richiestaConferma.messaggio`, raccoglie cio' che serve e ripete con la
//   // dichiarazione: `conferma(forzaturaConMotivo(motivo))`.
export function useForzaturaConfermata() {
  const { execute, loading, azioneUi, messaggioErrore, campiErrati } = useApiHandler()

  // La domanda in sospeso: `{ messaggio }` oppure `null`.
  // ⭐ Contratto: ogni domanda del database e' un oggetto NUOVO, anche con lo
  //    stesso messaggio. Il chiamante lo confronta per identita' per sapere se,
  //    dopo `conferma`, il database ha chiesto di NUOVO (dati cambiati: si
  //    rilegge) o se la domanda e' ancora quella di prima (errore vero).
  // ⭐ Il messaggio e' quello del DATABASE, e porta gia' i numeri: non si
  //    riscrive nel frontend una frase che il catalogo compone meglio, e che
  //    per giunta e' multilingua.
  const richiestaConferma = ref(null)

  // La chiamata da ripetere. ⚠️ Non e' un ref: non serve alla resa, e tenerla
  // reattiva inviterebbe a leggerla dal template — dove non significa niente.
  let inSospeso = null

  // Scopo: primo tentativo, SENZA forzatura.
  // Note: ⚠️ `azioniGestite` e non `silent`: il toast non parte SOLO sul rifiuto
  //       confermabile. Su tutto il resto — errore di sistema compreso — la
  //       gestione resta quella di `useApiHandler`, che e' l'unica sede in cui
  //       si decide fra `systemError`, gesto e toast normale.
  async function esegui(chiamata, opts = {}) {
    richiestaConferma.value = null
    inSospeso = { chiamata, opts }
    const esito = await execute(() => chiamata({}), {
      ...opts,
      azioniGestite: [CONFERMA_E_RIPETI],
    })
    if (esito !== null) {
      inSospeso = null
      return esito
    }
    if (azioneUi.value === CONFERMA_E_RIPETI) {
      // Non e' un fallimento: e' una domanda, e la si porta a video com'e'.
      richiestaConferma.value = { messaggio: messaggioErrore.value }
    } else {
      // Rifiuto vero: il toast l'ha gia' mostrato `useApiHandler`.
      inSospeso = null
    }
    return null
  }

  // Scopo: secondo tentativo, con la DICHIARAZIONE (`dichiarazione` si
  //        aggiunge al payload: `forzaturaConMotivo(motivo)` nei pagamenti,
  //        `{ riusa_auth_user_id }` nella creazione dell'operatore).
  // Note: ⚠️ Qui il toast di errore torna normale, SALVO un nuovo rifiuto
  //       confermabile: se nel frattempo il dato e' cambiato (un'altra
  //       credenziale sulla stessa email) il database fa di nuovo la domanda,
  //       e la domanda si ripropone invece di diventare un banner rosso.
  async function conferma(dichiarazione) {
    if (!inSospeso) return null
    const { chiamata, opts } = inSospeso
    const esito = await execute(
      () => chiamata(dichiarazione),
      { ...opts, azioniGestite: [CONFERMA_E_RIPETI] },
    )
    if (esito !== null) {
      richiestaConferma.value = null
      inSospeso = null
    } else if (azioneUi.value === CONFERMA_E_RIPETI) {
      richiestaConferma.value = { messaggio: messaggioErrore.value }
    }
    return esito
  }

  // Scopo: l'operatore rinuncia. ⭐ Non e' un no-op: senza, la domanda resterebbe
  //        appesa e la prossima riga la troverebbe gia' aperta.
  function annulla() {
    richiestaConferma.value = null
    inSospeso = null
  }

  // ⭐ `campiErrati` e' quello dell'handler INTERNO (2026-09-14): un form che
  //    salva con `esegui` e tiene il rosso sui campi con un secondo handler
  //    non vedrebbe mai i campi del 400 — il primo li riceve, il secondo li
  //    mostra, e non sono lo stesso oggetto.
  return { esegui, conferma, annulla, richiestaConferma, loading, campiErrati }
}
