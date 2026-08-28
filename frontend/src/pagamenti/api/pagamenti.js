// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Client API del dominio INCASSI — le 23 rotte di `/api/v1/pagamenti/`.
// Note: Brief: docs/it/dev/work-in-progress/brief-be-fe-posting-e-abbinamento-rata.md
//       ⭐ Sul filo la risorsa si chiama `distinte`, non `contabili`: e' la
//       parola che l'operatore legge sulla schermata (§4 del brief). La tabella
//       a DB resta `pagamenti.vendite_contabili`.
//       ⛔ `spezza` NON esiste: cade con D1-ter — «il pagamento di una rata non
//       si spezza». Se ti serve, e' il gesto a essere sbagliato, non la rotta.
// ------------------------------------------------------------

import api from '../../core/api'
import { generateIdempotencyKey } from '../../core/utils/idempotency'

const BASE = '/pagamenti'

// Scopo: header di una scrittura. Il backend dichiara `require_idempotency_key`
//        su tutte le POST che muovono stato: senza, rispondono 400.
function idem() {
  return { headers: { 'Idempotency-Key': generateIdempotencyKey() } }
}

// ══════════════════════════════════════════════════════════════
//  Distinte contabili
// ══════════════════════════════════════════════════════════════

// Elenco paginato. ⚠️ PAGE-BASED (`page`/`page_size`): la conversione da
// `limit`/`offset` — la lingua di `useSearchTable` — la fa lo store, una volta.
export function listDistinte(params = {}) {
  return api.get(`${BASE}/distinte/`, { params })
}

// ⭐ È un *get or create*: sulla stessa terna (centro, data, canale) NON crea un
// doppione, ridà quella che c'è già — e lo dichiara con `gia_popolata` nella
// risposta (Q-3). ⚠️ Chi chiama DEVE guardare quel campo: entrare in silenzio in
// una distinta che ha già righe è il modo in cui si registra due volte credendo
// di cominciare.
// Payload: `centro_riscossione_id` (obbligatorio), `data_contabile`,
// `ente_incasso_id`, `importo_dichiarato`, `meta`.
export function creaDistinta(payload) {
  return api.post(`${BASE}/distinte/`, payload, idem())
}

// Dettaglio: testata + totali derivati + righe + i DUE cataloghi di stato, in un
// round-trip. ⭐ Gli stati si leggono da lì (`is_postabile`, `is_final`,
// `richiede_abbinamento`), non si riscrivono nel frontend.
export function getDistinta(contabileId) {
  return api.get(`${BASE}/distinte/${contabileId}/`)
}

// PATCH dei soli campi che una persona compila.
export function aggiornaDistinta(contabileId, payload) {
  return api.patch(`${BASE}/distinte/${contabileId}/`, payload)
}

// Cambio stato della distinta: `VALIDATA` · `BOZZA` · `ANNULLATA`.
export function cambiaStatoDistinta(contabileId, nuovoStato) {
  return api.post(
    `${BASE}/distinte/${contabileId}/stato/`,
    { nuovo_stato: nuovoStato },
    idem(),
  )
}

// ══════════════════════════════════════════════════════════════
//  Righe della distinta
// ══════════════════════════════════════════════════════════════

export function listRigheDistinta(contabileId) {
  return api.get(`${BASE}/distinte/${contabileId}/righe/`)
}

// La riga nasce `DA_ABBINARE`. Payload: `importo` (obbligatorio),
// `riferimento_ente`, `data_pagamento`, `data_valuta`, `data_operazione`,
// `motivo_sospeso`, `meta`.
export function creaRiga(contabileId, payload) {
  return api.post(`${BASE}/distinte/${contabileId}/righe/`, payload, idem())
}

// I FATTI della riga (importo, riferimento, date) — non il suo percorso.
export function aggiornaRiga(rigaId, payload) {
  return api.patch(`${BASE}/righe/${rigaId}/`, payload)
}

// Il PERCORSO della riga. ⚠️ `motivo_sospeso` è ammesso qui perché sospendere
// senza dire perché produce una coda che nessuno sa lavorare.
export function cambiaStatoRiga(rigaId, nuovoStato, motivoSospeso = null) {
  const payload = { nuovo_stato: nuovoStato }
  if (motivoSospeso) payload.motivo_sospeso = motivoSospeso
  return api.post(`${BASE}/righe/${rigaId}/stato/`, payload, idem())
}

// ⭐ IL VERBO CHE PORTA L'INCASSO ALLA RATA. Fattura obbligatoria, cliente e
// rata facoltativi, e la forzatura a DUE TEMPI: il primo tentativo si manda
// SENZA `forzata`; se la rata non ha capienza il backend rifiuta con la ragione
// e i numeri (`ui_action = confirm_and_retry`), e solo dopo la conferma
// dell'operatore si ripete con `forzata: true` + `motivo_forzatura`.
// ⛔ Non si manda `forzata: true` al primo colpo per «semplificare»: quel flag
// resta SCRITTO sulla riga ed è ciò che l'elenco delle rate fuori capienza
// legge. Forzare senza che nessuno l'abbia chiesto nasconde invece di
// registrare.
export function abbinaRiga(rigaId, payload) {
  return api.post(`${BASE}/righe/${rigaId}/abbina/`, payload, idem())
}

// ══════════════════════════════════════════════════════════════
//  La registrazione — l'unico gesto irreversibile del cantiere
// ══════════════════════════════════════════════════════════════

// La fotografia PRIMA di registrare, coi MOTIVI per cui una riga resta indietro.
// ⭐ Non è una cortesia: è ciò che rende la conferma una decisione invece di un
// salto nel buio.
export function anteprimaRegistrazione(contabileId) {
  return api.get(`${BASE}/distinte/${contabileId}/anteprima-registrazione/`)
}

// ⛔ IRREVERSIBILE. `righe_attese`/`totale_atteso` sono la dichiarazione di ciò
// che l'operatore ha davanti: se il database trova numeri diversi si ferma.
// ⚠️ Lo ZERO è legittimo (una distinta senza righe registrabili): non si
// filtrano i valori a 0, o si trasforma un esito vero in un errore falso.
export function registraDistinta(contabileId, { righeAttese, totaleAtteso } = {}) {
  const payload = {}
  if (righeAttese != null) payload.righe_attese = righeAttese
  if (totaleAtteso != null) payload.totale_atteso = totaleAtteso
  return api.post(`${BASE}/distinte/${contabileId}/registra/`, payload, idem())
}

// ══════════════════════════════════════════════════════════════
//  Le code del riconciliatore
// ══════════════════════════════════════════════════════════════

// ⭐ UN ENDPOINT SOLO, due voci di menu (Q-4 → c): `coda` vale
// `DA_ABBINARE` | `SOSPESE` | `TUTTE`. ⚠️ Un valore inventato è un **400**, non
// una lista vuota: su un vocabolario chiuso «nessun risultato» sarebbe
// indistinguibile da «non c'è niente da fare».
export function listCodaRighe(params = {}) {
  return api.get(`${BASE}/righe/`, { params })
}

// L'elenco che rende ONESTA la forzatura: senza, forzare nasconde invece di
// registrare. Prima colonna `motivo` — due popolazioni diverse (sovra-incasso e
// movimento contrario) che non vanno confuse.
export function listRateFuoriCapienza(params = {}) {
  return api.get(`${BASE}/rate/fuori-capienza/`, { params })
}

// ══════════════════════════════════════════════════════════════
//  La base dei saldi (§2.7) — forma unica a ogni livello
// ══════════════════════════════════════════════════════════════
//
// ⭐ VINCOLO, non rifinitura: `residuo · in_lavorazione · incassato` è lo stesso
// vocabolario a tutti e tre i livelli — documento, rata e (quando si accenderà)
// cliente. Un saldo calcolato in due posti diverge alla prima regola nuova, e
// sono numeri su cui qualcuno decide se sollecitare un cliente.
// ⚠️ «Incassato» NON è «postato»: è ciò che è entrato davvero in cassa, esclusi
// i giri interni. Una rata coperta da una compensazione è regolata anche se in
// banca non è entrato niente.

export function getSaldoRata(scadenzaId) {
  return api.get(`${BASE}/rate/${scadenzaId}/saldo/`)
}

// ⚠️ Vive in `pagamenti` con `skip_area_check` e non in `vendite`: `api.md`
// vieta le chiamate laterali fra moduli di pari livello (correzione a Q-8).
// Lo consuma il drawer fattura, che sta in `vendite`.
export function getSaldoFattura(fatturaId) {
  return api.get(`${BASE}/fatture/${fatturaId}/saldo/`)
}

// Le rate di una fattura COL LORO SALDO, in un giro solo: un elenco di rate
// senza saldo non risponde alla domanda per cui lo si apre.
export function listRateFattura(fatturaId) {
  return api.get(`${BASE}/fatture/${fatturaId}/rate/`)
}

// ══════════════════════════════════════════════════════════════
//  Le sistemazioni — che cosa si fa del denaro di troppo
// ══════════════════════════════════════════════════════════════

// ⭐ Ordinato per CLIENTE di default (D15-b): compensare ha senso a quel
// livello, e un elenco per documento nasconde la decisione.
export function listEccedenze(params = {}) {
  return api.get(`${BASE}/eccedenze/`, { params })
}

// Registra la DECISIONE, non la esegue: l'atto nasce in bozza.
// 🔴 Cliente ed emittente NON si dichiarano — si derivano dalla fattura di
// origine, e il payload li rifiuta apposta: «non li sceglie una persona in un
// modulo, li deriva chi costruisce l'atto».
export function creaSistemazione(payload) {
  return api.post(`${BASE}/sistemazioni/`, payload, idem())
}

// ⚠️ REGISTRARE NON È ESEGUIRE: il controllo dell'eccedenza sta QUI, alla
// conferma, perché fra decidere e confermare può arrivare un altro incasso.
// E il canale del rimborso si chiede adesso: da quale conto esce il bonifico è
// una decisione del momento in cui si paga.
export function confermaSistemazione(sistemazioneId, payload = {}) {
  return api.post(`${BASE}/sistemazioni/${sistemazioneId}/conferma/`, payload, idem())
}

export function annullaSistemazione(sistemazioneId, payload = {}) {
  return api.post(`${BASE}/sistemazioni/${sistemazioneId}/annulla/`, payload, idem())
}

export function getSistemazione(sistemazioneId) {
  return api.get(`${BASE}/sistemazioni/${sistemazioneId}/`)
}

// Gli atti di un documento — ⭐ sono più di uno per natura: si può rimborsare
// una parte e riportare il resto.
export function listSistemazioniFattura(fatturaId) {
  return api.get(`${BASE}/fatture/${fatturaId}/sistemazioni/`)
}

// ══════════════════════════════════════════════════════════════
//  I canali di incasso (configurazione)
// ══════════════════════════════════════════════════════════════

export function listEntiIncasso(params = {}) {
  return api.get(`${BASE}/enti-incasso/`, { params })
}

export function creaEnteIncasso(payload) {
  return api.post(`${BASE}/enti-incasso/`, payload, idem())
}

export function getEnteIncasso(enteId) {
  return api.get(`${BASE}/enti-incasso/${enteId}/`)
}

export function aggiornaEnteIncasso(enteId, payload) {
  return api.patch(`${BASE}/enti-incasso/${enteId}/`, payload)
}

// ⭐ I conti AGGANCIABILI a un canale, cioè i soli conti di incasso del ruolo.
// Non è una comodità: il database rifiuta un conto che non è di incasso con un
// errore parlante, ma **un elenco che lo propone fa sbagliare**, e chi sbaglia
// se ne accorge dopo aver compilato tutto il resto.
// ⚠️ Un elenco VUOTO si DICHIARA (`nessun_conto_di_incasso`): è una condizione
// prevista, ma un menu vuoto senza spiegazione sembra un guasto.
// ⚠️ Ogni riga porta `conto_utility_descrizione`, che è `null` in due casi
// legittimi e diversi — conto senza istanza (è il conto *generico* del ruolo) o
// istanza senza PDP: a video è «nessuna utility», non un campo vuoto.
export function listContiIncasso(soggettoRuoloId) {
  return api.get(`${BASE}/conti-incasso/`, {
    params: { soggetto_ruolo_id: soggettoRuoloId },
  })
}
