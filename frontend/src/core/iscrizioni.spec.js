// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Carica TUTTE le `<dominio>/iscrizioni.js`, come fa `main.js`
//        all'avvio. Un'iscrizione che lancia (chiave doppia, punto o tipo
//        scritto male) blocca il mount dell'intera app: pagina bianca per
//        tutti i domini, e la build non se ne accorge perche' non esegue il
//        codice. Qui se ne accorge la CI.
//        Fissa anche le voci che i registri avevano prima del passaggio alle
//        iscrizioni (2026-09-26): una voce persa per strada e' un pulsante
//        che non compare, senza errore.
//
// Indice test:
//  1. le iscrizioni si caricano senza errori
//  2. ogni tipo del vocabolario drawer ha un drawer iscritto
//  3. le attivita' e i completamenti dei flussi pratica sono iscritti
//  4. ogni punto di estensione con un contributo lo riceve
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { DOCUMENTO_DRAWER_TIPI, drawerEntita } from './drawerEntita'
import { contributi, PUNTI_ESTENSIONE } from './estensioni'
import { getUiActivity } from '../pratiche/uiActivityRegistry'
import { getCompletionDialog } from '../pratiche/flussoCompletionRegistry'
import { getDomainCompletion } from '../pratiche/flussoDomainCompletionRegistry'

// Il client HTTP vero legge `localStorage`, che in ambiente node non c'e':
// le iscrizioni non chiamano mai il backend al caricamento.
vi.mock('./api', () => ({ default: {} }))

describe('iscrizioni dei domini', () => {
  it('si caricano senza errori', async () => {
    const moduli = import.meta.glob('../*/iscrizioni.js')
    expect(Object.keys(moduli).length).toBeGreaterThan(0)
    for (const carica of Object.values(moduli)) await carica()
  })

  it('ogni tipo del vocabolario drawer ha un drawer iscritto', () => {
    for (const tipo of Object.values(DOCUMENTO_DRAWER_TIPI)) {
      expect(drawerEntita(tipo), tipo).not.toBeNull()
    }
  })

  it('le attivita\' e i completamenti dei flussi pratica sono iscritti', () => {
    for (const k of ['APRI_PREVENTIVO', 'SMISTAMENTO', 'CONFERMA_ORDINE', 'INVIO_COMMESSA']) {
      expect(getUiActivity(k), k).toBeTruthy()
    }
    expect(getCompletionDialog('APPROVAZIONE_CLIENTE')).toBeTruthy()
    expect(getDomainCompletion('SMISTAMENTO')).toBeTruthy()
  })

  it('ogni punto di estensione con un contributo lo riceve', () => {
    const attesi = {
      [PUNTI_ESTENSIONE.ARTICOLO_DRAWER_SEZIONI]: ['lotti'],
      [PUNTI_ESTENSIONE.ARTICOLO_AZIONI_RIGA]: ['manage-lotti'],
      [PUNTI_ESTENSIONE.CLIENTE_AZIONI_RIGA]: ['contratti'],
      [PUNTI_ESTENSIONE.SOGGETTO_ANTEPRIMA_BADGE]: ['accessi-web'],
      [PUNTI_ESTENSIONE.FATTURA_DRAWER_SEZIONI]: ['saldo'],
    }
    for (const [punto, chiavi] of Object.entries(attesi)) {
      expect(contributi(punto).map(c => c.chiave), punto).toEqual(chiavi)
    }
  })
})
