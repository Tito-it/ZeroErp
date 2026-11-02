// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LE ISCRIZIONI DI PORTALE — cio' che il dominio aggiunge alle
//        schermate degli altri (frontend-standards §«Confini fra domini»).
//        Gli accessi web puntano al soggetto: l'anteprima del soggetto non
//        conosce portale, e il badge ci arriva da qui. Lo carica `main.js`.
// ------------------------------------------------------------
import { contribuisci, PUNTI_ESTENSIONE } from '../core/estensioni'

// Il badge «accessi web» (portale + shop) nell'anteprima di cliente e fornitore.
contribuisci(PUNTI_ESTENSIONE.SOGGETTO_ANTEPRIMA_BADGE, {
  chiave: 'accessi-web',
  componente: () => import('./components/WebAccessiBadge.vue'),
})
