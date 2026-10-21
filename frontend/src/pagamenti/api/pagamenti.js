// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Client API del dominio INCASSI — le 28 rotte di `/api/v1/pagamenti/`.
// Note: Brief: docs/it/dev/work-in-progress/brief-be-fe-posting-e-abbinamento-rata.md
//       ⭐ Sul filo la risorsa si chiama `distinte`, non `contabili`: e' la
//       parola che l'operatore legge sulla schermata (§4 del brief). La tabella
//       a DB resta `pagamenti.vendite_contabili`.
//       ⛔ `spezza` NON esiste: cade con D1-ter — «il pagamento di una rata non
//       si spezza». Se ti serve, e' il gesto a essere sbagliato, non la rotta.
// ------------------------------------------------------------

import api from '../../core/api'

const BASE = '/pagamenti'


// ══════════════════════════════════════════════════════════════
//  Distinte contabili
// ══════════════════════════════════════════════════════════════

// Elenco paginato con `limit`/`offset`, come ogni lista (fino al 2026-10-21
// PAGE-BASED: la conversione la faceva lo store).
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
  return api.post(`${BASE}/distinte/`, payload)
}

// Dettaglio: testata + totali derivati + i DUE cataloghi di stato, in un
// round-trip. ⭐ Gli stati si leggono da lì (`is_postabile`, `is_final`,
// `richiede_abbinamento`), non si riscrivono nel frontend.
// ⚠️ Le righe NON viaggiano più qui (dal 18/09): sono la lista paginata
//    `listRigheDistinta`, con la sua pagina e il suo export.
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
  )
}

// ══════════════════════════════════════════════════════════════
//  Righe della distinta
// ══════════════════════════════════════════════════════════════

// Le righe di UNA distinta — la lista `pagamenti.distinta_righe` (18/09).
// ⚠️ `params` porta limit/offset/order_by/order_dir: la lista PAGINA dal
//    2026-09-18 (decisione di Tid), come ogni altra lista configurabile.
export function listRigheDistinta(contabileId, params = {}) {
  return api.get(`${BASE}/distinte/${contabileId}/righe/`, { params })
}

// Scopo: export CSV/Excel delle righe di una distinta — «la contabile in un file».
// ⚠️ `formato` e non `format`: quest'ultimo è un parametro magico di DRF e
//    collide col content negotiation (`feedback_drf_format_magic_param`).
//    Risposta Blob: errore 422 se il dataset supera il cap.
export function exportRigheDistinta(contabileId, params = {}) {
  return api.get(`${BASE}/distinte/${contabileId}/righe/export/`, {
    params,
    responseType: 'blob',
  })
}

// ⭐ La riga nasce CON LA DESTINAZIONE (D16, 14/09): coi fatti — `importo`
// (obbligatorio), `riferimento_ente`, `data_pagamento`, `data_valuta`,
// `data_operazione`, `motivo_sospeso`, `meta` — viaggiano `fattura_id`,
// `billing_account_id` (facoltativo: il backend lo legge dalla fattura),
// `scadenza_id` (facoltativa) e la forzatura a due tempi (`forzata`,
// `motivo_forzatura`), come in `abbinaRiga`. Con la fattura nasce ABBINATA in
// un INSERT solo; senza nasce DA_ABBINARE — l'eccezione che si dichiara.
export function creaRiga(contabileId, payload) {
  return api.post(`${BASE}/distinte/${contabileId}/righe/`, payload)
}

// ⭐ N RATE → N RIGHE in un Salva (D19-d): le rate scelte nel picker diventano
// righe della distinta, ognuna con la propria destinazione. Payload: i FATTI
// COMUNI (`data_pagamento`, `data_valuta`, `data_operazione`,
// `riferimento_ente`, `meta`) + `righe: [{scadenza_id, importo, forzata?,
// motivo_forzatura?}]` (tetto 200, `scadenza_id` duplicato = 400).
// ⚠️ La risposta è un ESITO A TRE STATI, e lo status è 200 anche su
// `PARZIALE`/`ERRORE`: chi legge guarda `esito`, `creati[]` e `falliti[]` — ogni
// fallita porta il suo errore INTERO (`code`, `message`, `hint`, `ui_action`,
// `fields`, `targets`), quindi la capienza che non regge risale «confermabile»
// PER RIGA e il secondo tempo è un giro nuovo con le sole righe rimaste.
export function creaRigheDaRate(contabileId, payload) {
  return api.post(`${BASE}/distinte/${contabileId}/righe/da-rate/`, payload)
}

// I FATTI della riga (importo, riferimento, date) — non il suo percorso, e
// non la destinazione (quella e' di `abbinaRiga`). ⭐ Dal 15/09 anche il
// secondo tempo della capienza, `forzata` + `motivo_forzatura`, come alla
// nascita: correggere un importo incontra lo stesso guard della rata.
export function aggiornaRiga(rigaId, payload) {
  return api.patch(`${BASE}/righe/${rigaId}/`, payload)
}

// ⭐ ELIMINA una riga (D17, 14/09): `attivo = false`, solo su una distinta
// manuale in bozza — e a dirlo e' il database (409 `E_RIGA_CONTABILE_DISTINTA_*`),
// la stessa check che spegne il cestino in lista (`elimina_blocco_*`).
// ⚠️ Il metodo dice il verbo: niente `/elimina/` nel path. E' una scrittura,
// quindi porta l'`Idempotency-Key` come le POST.
export function eliminaRiga(rigaId) {
  return api.delete(`${BASE}/righe/${rigaId}/`)
}

// Il PERCORSO della riga. ⚠️ `motivo_sospeso` è ammesso qui perché sospendere
// senza dire perché produce una coda che nessuno sa lavorare.
export function cambiaStatoRiga(rigaId, nuovoStato, motivoSospeso = null) {
  const payload = { nuovo_stato: nuovoStato }
  if (motivoSospeso) payload.motivo_sospeso = motivoSospeso
  return api.post(`${BASE}/righe/${rigaId}/stato/`, payload)
}

// Scopo: Il SECONDO TEMPO della capienza, cioe' cio' che si aggiunge al
//        payload quando l'operatore conferma: `forzata` + il suo motivo (vuoto =
//        null). Una sede per la forma che `abbinaRiga`, `registraRigaTardiva` e
//        `aggiornaRiga`/`creaRiga` ricevono; la passano a
//        `useForzaturaConfermata().conferma(...)`, che non conosce le parole
//        dei pagamenti.
export function forzaturaConMotivo(motivo) {
  return { forzata: true, motivo_forzatura: motivo }
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
export function abbinaRiga(rigaId, payload, config = {}) {
  return api.post(`${BASE}/righe/${rigaId}/abbina/`, payload, config)
}

// ⭐ LA REGISTRAZIONE TARDIVA (D20-b): una riga SOSPESA sotto una distinta
// già REGISTRATA si abbina E si registra nello stesso gesto — movimento
// scritto, riga POSTATA, distinta che resta CHIUSA. Il payload è quello di
// `abbinaRiga`, col suo stesso doppio tempo della capienza (`confirm_and_retry`
// → `forzata: true` + motivo). Stesso cancello di `registraDistinta`.
// ⛔ Non è un esito «nulla da postare»: una tardiva che non si può fare è un
// 409 con la sua frase (`E_RIGA_CONTABILE_TARDIVA_*`).
export function registraRigaTardiva(rigaId, payload, config = {}) {
  return api.post(`${BASE}/righe/${rigaId}/registra/`, payload, config)
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
export function registraDistinta(contabileId, { righeAttese, totaleAtteso } = {}, config = {}) {
  const payload = {}
  if (righeAttese != null) payload.righe_attese = righeAttese
  if (totaleAtteso != null) payload.totale_atteso = totaleAtteso
  return api.post(`${BASE}/distinte/${contabileId}/registra/`, payload, config)
}

// ⭐ LA CORREZIONE GUIDATA (Q-7): da una distinta REGISTRATA nasce una distinta
// nuova, in bozza, con le righe di **segno opposto** già compilate — fattura e
// rata comprese. ⛔ Non ricopiatura a mano: su venti righe è lì che nasce il
// secondo errore.
// ⭐ Le righe nascono in `DA_ABBINARE`, non `ABBINATA`, ed è una decisione
// misurata (C-1): su una rata saldata dal movimento che si sta correggendo non
// c'è capienza in nessuna direzione, quindi «già abbinata» avrebbe richiesto di
// scrivere `forzata = true` **al posto dell'operatore**. La correzione guida
// tutto tranne l'ultimo clic.
// ⛔ NON si chiama «storno»: `STORNATA` è fuori dal catalogo dal 21/08.
// ⚠️ `esito = NULLA_DA_CORREGGERE` **non è un errore**: è la risposta vera di
// una distinta senza righe postate, e arriva con `distinta: null`.
export function correggiDistinta(contabileId, { dataContabile, motivo } = {}) {
  const payload = {}
  if (dataContabile) payload.data_contabile = dataContabile
  if (motivo) payload.motivo = motivo
  return api.post(`${BASE}/distinte/${contabileId}/correggi/`, payload)
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

// ⭐ L'ELENCO DELLE RATE COL SALDO (lista `pagamenti.rate`, D19-c): la sorgente
// del picker della distinta e, domani, dello scadenzario. Offset-based
// (`limit`/`offset`, la lingua di `useSearchTable`). Criteri: `billing_account_id`,
// `fattura_numero` (ESATTO: 101 non porta 1010; `serie`/`anno` per disambiguare),
// `search` (min 3, cerca il CLIENTE — mai il numero), `solo_aperte` (residuo ≠ 0),
// `data_scadenza_da/a`, `natura_doc_codice`. Ogni riga porta la vista
// `vw_fatture_scadenze_lista` più `residuo · in_lavorazione · incassato ·
// has_movimenti` dalla base unica dei saldi.
// ⛔ Nessun criterio è obbligatorio QUI: lo pretende il picker (D19-c), non la rotta
// — lo scadenzario la chiama senza.
export function listRate(params = {}) {
  return api.get(`${BASE}/rate/`, { params })
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

// Scopo: i query param del «prima di se'», uguali sui due livelli — cosi' il
//        nome del parametro non puo' divergere fra rata e documento.
function paramsEsclusione({ escludiRigaId = null } = {}) {
  return escludiRigaId != null ? { escludi_riga_id: escludiRigaId } : undefined
}

// ⭐ `escludiRigaId` chiede lo spazio PRIMA DI SE' (il backend lo accetta dal
//    lotto 5): serve a chi sta CORREGGENDO una riga, perche' senza, il saldo
//    conta fra gli «in lavorazione» proprio i soldi che sta cambiando.
export function getSaldoRata(scadenzaId, opzioni = {}) {
  return api.get(`${BASE}/rate/${scadenzaId}/saldo/`, { params: paramsEsclusione(opzioni) })
}

// ⚠️ Vive in `pagamenti` con `skip_area_check` e non in `vendite`: `api.md`
// vieta le chiamate laterali fra moduli di pari livello (correzione a Q-8).
// Lo consuma il drawer fattura, che sta in `vendite`.
// ⭐ `escludiRigaId` anche qui dal 2026-09-18 (P-6 del brief D19): lo stesso
//    «prima di se'» della rata, per chi corregge una riga SENZA rata (il fondo
//    fattura e' cosi'). Fino a quel giorno il pannello dichiarava di non
//    saperla escludere.
export function getSaldoFattura(fatturaId, opzioni = {}) {
  return api.get(`${BASE}/fatture/${fatturaId}/saldo/`, { params: paramsEsclusione(opzioni) })
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
  return api.post(`${BASE}/sistemazioni/`, payload)
}

// ⚠️ REGISTRARE NON È ESEGUIRE: il controllo dell'eccedenza sta QUI, alla
// conferma, perché fra decidere e confermare può arrivare un altro incasso.
// E il canale del rimborso si chiede adesso: da quale conto esce il bonifico è
// una decisione del momento in cui si paga.
export function confermaSistemazione(sistemazioneId, payload = {}) {
  return api.post(`${BASE}/sistemazioni/${sistemazioneId}/conferma/`, payload)
}

export function annullaSistemazione(sistemazioneId, payload = {}) {
  return api.post(`${BASE}/sistemazioni/${sistemazioneId}/annulla/`, payload)
}

export function getSistemazione(sistemazioneId) {
  return api.get(`${BASE}/sistemazioni/${sistemazioneId}/`)
}

// Gli atti di un documento — ⭐ sono più di uno per natura: si può rimborsare
// una parte e riportare il resto.
// ⚠️ `params` porta limit/offset/order_by/order_dir: la lista PAGINA dal
//    2026-09-02, come ogni altra lista configurabile.
export function listSistemazioniFattura(fatturaId, params = {}) {
  return api.get(`${BASE}/fatture/${fatturaId}/sistemazioni/`, { params })
}

// Scopo: export CSV/Excel degli atti di sistemazione di una fattura.
// ⚠️ `formato` e non `format`: quest'ultimo è un parametro magico di DRF e
//    collide col content negotiation (`feedback_drf_format_magic_param`).
//    Risposta Blob: errore 422 se il dataset supera il cap.
export function exportSistemazioniFattura(fatturaId, params = {}) {
  return api.get(`${BASE}/fatture/${fatturaId}/sistemazioni/export/`, {
    params,
    responseType: 'blob',
  })
}

// ══════════════════════════════════════════════════════════════
//  I canali di incasso (configurazione)
// ══════════════════════════════════════════════════════════════

export function listEntiIncasso(params = {}) {
  return api.get(`${BASE}/enti-incasso/`, { params })
}

export function creaEnteIncasso(payload) {
  return api.post(`${BASE}/enti-incasso/`, payload)
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
