// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LE ISCRIZIONI DI MAGAZZINO — cio' che il dominio aggiunge alle
//        schermate degli altri (frontend-standards §«Confini fra domini»).
//        `magazzino.lotti` punta a `catalogo.articoli`: la scheda e la lista
//        articoli non conoscono magazzino, e i lotti ci arrivano da qui.
//        Lo carica `main.js` all'avvio.
// ------------------------------------------------------------
import { MANAGE_ICONS } from '../core/constants'
import { contribuisci, PUNTI_ESTENSIONE } from '../core/estensioni'

// La sezione «Lotti di magazzino» della scheda articolo, in modifica.
contribuisci(PUNTI_ESTENSIONE.ARTICOLO_DRAWER_SEZIONI, {
  chiave: 'lotti',
  componente: () => import('./components/ArticoloLottiSezione.vue'),
})

// La voce «Lotti» del kebab articoli (2026-09-21): solo su merce gestita a
// magazzino — un lotto ha senso su cio' che movimenta. Su un articolo spento il
// DB rifiuterebbe la scrittura: si nasconde, non si spegne.
contribuisci(PUNTI_ESTENSIONE.ARTICOLO_AZIONI_RIGA, {
  chiave: 'manage-lotti',
  label: 'magazzino.lotti.gestisci',
  icon: MANAGE_ICONS.LOTTO_MAGAZZINO,
  visibile: (riga) => Boolean(riga.gestito_a_magazzino) && riga.attivo !== false,
  drawer: () => import('./components/ArticoloLottiDrawer.vue'),
  props: (riga) => ({
    articoloId: riga.id ?? null,
    articoloCodice: riga.codice ?? '',
    requiresLotto: riga.requires_lotto ?? true,
  }),
})
