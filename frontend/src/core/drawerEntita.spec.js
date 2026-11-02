// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il registro dei drawer per tipo di entita' e il vocabolario
//        dei punti di estensione: chi decide se un tipo e' una SORGENTE
//        (il vocabolario di core, non chi si iscrive) e il rifiuto di un
//        punto scritto male (un refuso sarebbe un contributo che non compare).
//
// Indice test:
//  1. una tappa e' apribile solo su un tipo sorgente iscritto e con id
//  2. un tipo fuori vocabolario e' un errore
//  3. un punto di estensione sconosciuto e' un errore
//  4. il precaricamento avvia il loader dei componenti e ne ingoia l'errore
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { DOCUMENTO_DRAWER_TIPI as T, drawerEntita, iscriviDrawerEntita, isTappaApribile } from './drawerEntita'
import { contribuisci, contributi, precaricaPunto, PUNTI_ESTENSIONE } from './estensioni'

describe('drawerEntita', () => {
  it('una tappa e\' apribile solo su un tipo sorgente iscritto e con id', () => {
    const load = async () => ({})
    iscriviDrawerEntita(T.FATTURA, { load, idProp: 'fatturaId' })
    iscriviDrawerEntita(T.COMMESSA_GESTIONE, { load, idProp: 'commessaId' })
    expect(drawerEntita(T.FATTURA)).toMatchObject({ idProp: 'fatturaId', hasMode: false, sorgente: true })
    expect(isTappaApribile({ tipoCodice: T.FATTURA, docId: 3 })).toBe(true)
    expect(isTappaApribile({ tipoCodice: T.FATTURA, docId: null })).toBe(false)
    // Non-sorgente: si apre per id, ma non e' una tappa del lineage.
    expect(isTappaApribile({ tipoCodice: T.COMMESSA_GESTIONE, docId: 3 })).toBe(false)
    // Nessuno l'ha iscritto: nessun drawer.
    expect(isTappaApribile({ tipoCodice: T.DDT_VENDITA, docId: 3 })).toBe(false)
  })

  it('un tipo fuori vocabolario e\' un errore', () => {
    expect(() => iscriviDrawerEntita('FATTURE', { load: async () => ({}), idProp: 'x' })).toThrow(/sconosciuto/)
  })
})

describe('estensioni', () => {
  it('un punto sconosciuto e\' un errore; uno noto raccoglie i contributi', () => {
    expect(() => contribuisci('articolo.drawer.sezione', { chiave: 'x' })).toThrow(/sconosciuto/)
    contribuisci(PUNTI_ESTENSIONE.FATTURA_DRAWER_SEZIONI, { chiave: 'prova' })
    expect(contributi(PUNTI_ESTENSIONE.FATTURA_DRAWER_SEZIONI).map(c => c.chiave)).toEqual(['prova'])
  })

  it('il precaricamento avvia il loader dei componenti e ne ingoia l\'errore', async () => {
    const buono = vi.fn(async () => ({}))
    const rotto = vi.fn(async () => { throw new Error('chunk') })
    contribuisci(PUNTI_ESTENSIONE.ARTICOLO_DRAWER_SEZIONI, { chiave: 'a', componente: buono })
    contribuisci(PUNTI_ESTENSIONE.ARTICOLO_DRAWER_SEZIONI, { chiave: 'b', componente: rotto })
    expect(() => precaricaPunto(PUNTI_ESTENSIONE.ARTICOLO_DRAWER_SEZIONI)).not.toThrow()
    await Promise.resolve()
    expect(buono).toHaveBeenCalledOnce()
    expect(rotto).toHaveBeenCalledOnce()
  })
})
