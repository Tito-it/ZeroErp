// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LE ISCRIZIONI DI PAGAMENTI — cio' che il dominio aggiunge alle
//        schermate degli altri (frontend-standards §«Confini fra domini»).
//        I movimenti contabili puntano alla fattura: il drawer della fattura
//        non conosce pagamenti, e il saldo ci arriva da qui. Lo carica
//        `main.js` all'avvio.
// ------------------------------------------------------------
import { contribuisci, PUNTI_ESTENSIONE } from '../core/estensioni'

// Il saldo della fattura, in testa alla scheda «Documento».
contribuisci(PUNTI_ESTENSIONE.FATTURA_DRAWER_SEZIONI, {
  chiave: 'saldo',
  componente: () => import('./components/SaldoFatturaSezione.vue'),
})
