// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I vocabolari CHIUSI del dominio incassi che il frontend deve
//        conoscere, in un punto solo.
// Note: ⛔ QUI STANNO SOLO I VOCABOLARI CHE **NON** HANNO UN CATALOGO. Sono
//       `CHECK` del database o whitelist del backend: non esiste una tabella da
//       interrogare, quindi il frontend una copia la tiene per forza — e allora
//       la tiene in UN posto, dove si vede.
//       ⛔ Gli STATI (distinta e riga) NON stanno qui: sono tabelle di catalogo
//       (`pagamenti.vendite_contabili_stati`, `..._righe_stati`), gia' in
//       whitelist per il lookup generico, e il dettaglio della distinta se li
//       porta dietro coi flag che governano l'interfaccia. Copiarli qui
//       vorrebbe dire nascondere in silenzio lo stato che nascera' domani.
//       ⚠️ Ogni etichetta si risolve **fail-visible** (`labelOrCode`): un valore
//       che il backend aggiunge e i locales non conoscono si vede come CODICE,
//       non come cella vuota.
//       ⚠️ Nessun import di pinia o di store: questo modulo lo carica anche il
//       ROUTER, che non deve tirarsi dietro uno store per leggere una costante.
// ------------------------------------------------------------

// Le tre code della lista righe (Q-4 -> c). Contratto: `GET /pagamenti/righe/`
// param `coda`. ⛔ Vocabolario chiuso lato backend: un valore inventato e' un
// **400**, non una lista vuota.
// ⚠️ `TUTTE` e' parte del contratto ma **non ha una porta**: le voci di menu
//    sono due, ed erano due nella decisione. Resta dichiarata perche' e' il
//    vocabolario dell'endpoint, non perche' qualcuno la usi oggi.
export const CODE = Object.freeze({
  DA_ABBINARE: 'DA_ABBINARE',
  SOSPESE: 'SOSPESE',
  TUTTE: 'TUTTE',
})

// ⭐ Le DUE porte, e la rotta di ciascuna. Serve al selettore in pagina, che
//    NAVIGA invece di cambiare uno stato interno: la rotta e' l'unica verita' —
//    altrimenti l'etichetta del tab direbbe «Sospese» mentre a video si guarda
//    «Da abbinare», e a quel punto il deep-link non descrive piu' la pagina.
export const ROTTA_PER_CODA = Object.freeze({
  [CODE.DA_ABBINARE]: 'pagamenti-coda-abbinare',
  [CODE.SOSPESE]: 'pagamenti-coda-sospese',
})

// Origine della distinta — `CHECK` su `pagamenti.vendite_contabili.origine`.
export const ORIGINI_DISTINTA = Object.freeze(['MANUALE', 'AUTOMATICA', 'GENERATA'])

// Perche' una rata e' fuori capienza — whitelist `MOTIVI_FUORI_CAPIENZA` del
// backend. ⚠️ Sono DUE mondi diversi, non due sfumature: sovra-incasso (e'
// entrato piu' del dovuto) e movimento contrario (un segno che non torna).
export const MOTIVI_FUORI_CAPIENZA = Object.freeze(['SOVRA_INCASSATA', 'MOVIMENTO_CONTRARIO'])

// Di chi sono i soldi in eccedenza. ⛔ Sbagliare il verso significa rimborsare
// cio' che si deve incassare: e' un filtro esposto e una colonna a colori, non
// un segno da leggere dentro un numero.
export const CHI_E_IN_CREDITO = Object.freeze(['CLIENTE', 'AZIENDA'])

// Il colore del verso. ⚠️ `CLIENTE` in credito = c'e' qualcosa da restituire,
// quindi arancio; `AZIENDA` in credito = da incassare, informativo.
export const SEVERITY_CHI_E_IN_CREDITO = Object.freeze({
  CLIENTE: 'warn',
  AZIENDA: 'info',
})

// I quattro tipi di canale di incasso — `CHECK chk_enti_incasso_tipo`.
export const TIPI_CANALE = Object.freeze(['BANCA', 'POSTE', 'PSP', 'ALTRO'])

// ⛔ Il tipo che pretende la FILIALE, e la pretende in ESCLUSIVA: il
//    `CHECK chk_enti_incasso_bank_branch_tipo` vuole `bank_branch_id` NOT NULL
//    su BANCA e NULL su tutti gli altri. Non e' «facoltativo altrove»: e'
//    vietato — un valore rimasto in memoria dopo un cambio di tipo e' un
//    rifiuto del database, non un campo di troppo.
export const TIPO_CANALE_CON_FILIALE = 'BANCA'

// ⛔ Il tipo che pretende il SOGGETTO PSP (`trgfn_enti_incasso_guard_psp`): il
//    soggetto_ruolo dev'esserci, essere di ruolo PSP e avere una riga attiva in
//    `anagrafiche.psp`. Le altre due condizioni le verifica il database.
export const TIPO_CANALE_PSP = 'PSP'

// Il codice del tipo ruolo da cercare per il soggetto di un canale PSP.
export const RUOLO_PSP = 'PSP'

// ⭐ Le tre destinazioni di una sistemazione. Non sono tre modi di dire la
//    stessa cosa: producono DUE specie diverse di oggetto — un fondo fattura
//    (riporto) oppure una distinta contabile (rimborso, compensazione).
export const DESTINAZIONI = Object.freeze(['RIPORTO', 'RIMBORSO', 'COMPENSAZIONE'])

// Le destinazioni che vogliono un SECONDO documento: il denaro va da qualche
// parte. ⛔ Sul rimborso e' vietato — li' il denaro esce dal sistema, e un
// secondo documento non esiste.
export const DESTINAZIONI_CON_DESTINATARIO = Object.freeze(['RIPORTO', 'COMPENSAZIONE'])

// ⭐ L'unica destinazione che chiede il CANALE, e lo chiede alla CONFERMA: da
//    quale conto esce il bonifico e' una decisione del momento in cui si paga.
export const DESTINAZIONE_CON_CANALE = 'RIMBORSO'

// ⭐ L'unica destinazione che lascia dietro un FONDO invece di una distinta —
//    ed e' la ragione per cui e' anche l'unica che si puo' annullare dopo la
//    conferma: le altre due si disfano con la correzione guidata sulla loro
//    distinta, che esiste gia'. Due strade per disfare lo stesso fatto e' il
//    modo in cui due meccanismi cominciano a divergere.
export const DESTINAZIONE_CON_FONDO = 'RIPORTO'

// Gli stati di un atto di sistemazione — `CHECK chk_sistemazioni_stato`, senza
// tabella di catalogo (tre stati e due passaggi: la regola sta nel guard, non
// nei dati).
// ⚠️ ANNULLATA e' terminale. ~~CONFERMATA e' terminale~~ 🔴 **non piu' dal
//    2026-08-31**: il varco `CONFERMATA -> ANNULLATA` e' aperto per il SOLO
//    `RIPORTO` (changeSet `20260831-66`, G-5). Su `RIMBORSO` e `COMPENSAZIONE`
//    resta vero, e il rifiuto NOMINA la correzione guidata invece di dire
//    «immutabile».
export const STATI_SISTEMAZIONE = Object.freeze(['BOZZA', 'CONFERMATA', 'ANNULLATA'])
export const STATO_SISTEMAZIONE_TERMINALI = Object.freeze(['CONFERMATA', 'ANNULLATA'])

// ⭐ L'unico stato su cui i due verbi hanno senso. ⚠️ Sta QUI e non come stringa
//    dentro un componente perche' e' un vocabolario **senza catalogo**: la
//    tabella `sistemazioni` non ha stati a tabella (lo dice il commento del
//    guard: «chi cerca la regola nei dati non la trova»), quindi la copia nel
//    frontend e' inevitabile — e allora sta in un posto solo, dove si vede.
export const STATO_SISTEMAZIONE_BOZZA = 'BOZZA'

// ⭐ Serve da quando `CONFERMATA` non e' piu' solo «terminale»: e' lo stato su
//    cui l'annullo del RIPORTO e' ammesso, quindi un componente deve poterlo
//    NOMINARE. Sta qui per la stessa ragione della riga sopra — vocabolario
//    senza catalogo, quindi la copia nel frontend e' inevitabile e sta in un
//    posto solo, dove si vede.
export const STATO_SISTEMAZIONE_CONFERMATA = 'CONFERMATA'

// ⭐ L'AZIONE DI PROCESSO che apre la registrazione — il codename di
//    `config.azioni_processo` che il backend dichiara come `post_permission`
//    su OGNI verbo che scrive un movimento: «Registra» la distinta e «Abbina e
//    registra» la riga (la tardiva, D20-b). ⛔ Un solo nome: tre letterali in
//    due file divergono al primo rename senza nessun errore, e il pulsante
//    resterebbe visibile a chi il backend rifiuta.
export const AZIONE_REGISTRA_DISTINTA = 'registra_distinta'

// ⭐ Gli esiti della REGISTRAZIONE — vocabolario chiuso della funzione madre
//    (`fn_posta_contabile`), senza tabella di catalogo. ⛔ `NULLA_DA_POSTARE`
//    NON e' un errore: e' la risposta vera di una distinta che non aveva righe
//    registrabili, e va detta come **avviso** — un toast di successo su un
//    gesto che non e' successo e' la bugia peggiore di tutto il cantiere.
export const ESITO_POSTATA = 'POSTATA'
export const ESITO_NULLA_DA_POSTARE = 'NULLA_DA_POSTARE'
