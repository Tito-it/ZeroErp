// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useAzioneRiga` (FE-1, brief-modello-documento-
//        vendita §15.11.2): le colonne si leggono dal REGISTRO, non dal nome
//        dell'azione; il motivo si traduce con ripiego sul codice; senza
//        registro, o con un'azione non iscritta, il pulsante e' spento.
// Note: `vue-i18n` e `useGlobalLookup` finti: qui si prova la lettura, non la
//        fetch.
//
// Indice test:
//   1) le colonne vengono dal registro (nomi qualunque, non derivati dal codice)
//   2) motivo assente -> azione ammessa, `motivo` undefined
//   3) chiave non tradotta -> il codice del motivo, mai il vuoto
//   4) registro in volo -> spenta col motivo «Caricamento...» (fail-closed)
//   5) azione non iscritta (registro letto) -> spenta, non pronta, e lo dice
//   6) registro non letto (fetch fallita) -> spenta, e non «Caricamento...»
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'

const dizionario = {
  'motivi.gia_uscito': 'Il documento è già fuori dal giro',
  'common.loading': 'Caricamento...',
  'common.azione_riga_non_registrata': 'Non attiva nel registro',
  'common.azione_riga_registro_non_letto': 'Registro non letto',
}
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    te: (chiave) => chiave in dizionario,
    t: (chiave) => dizionario[chiave] ?? chiave,
  }),
}))
vi.mock('../apiCore', () => ({ lookupAzioniRiga: vi.fn() }))

const registro = ref([])
const caricato = ref(true)
const errore = ref(null)
vi.mock('./useGlobalLookup', () => ({
  useGlobalLookup: () => ({
    items: registro, loaded: caricato, error: errore, load: vi.fn(() => Promise.resolve()),
  }),
}))

const { useAzioneRiga } = await import('./useAzioneRiga')

const VOCE = {
  codice_interno: 'AZIONE_X',
  colonna_motivo: 'blocco_x',
  colonna_motivo_chiave: 'blocco_x_chiave',
}

describe('useAzioneRiga', () => {
  beforeEach(() => {
    registro.value = [VOCE]
    caricato.value = true
    errore.value = null
  })

  it('1) le colonne vengono dal registro', () => {
    const a = useAzioneRiga('AZIONE_X')
    const riga = { blocco_x: 'GIA_USCITO', blocco_x_chiave: 'motivi.gia_uscito' }
    expect(a.pronta.value).toBe(true)
    expect(a.bloccata(riga)).toBe(true)
    expect(a.motivo(riga)).toBe('Il documento è già fuori dal giro')
  })

  it('2) senza motivo l\'azione e\' ammessa', () => {
    const a = useAzioneRiga('AZIONE_X')
    const riga = { blocco_x: null, blocco_x_chiave: null }
    expect(a.bloccata(riga)).toBe(false)
    expect(a.motivo(riga)).toBeUndefined()
  })

  it('3) chiave non tradotta -> il codice del motivo', () => {
    const a = useAzioneRiga('AZIONE_X')
    expect(a.motivo({ blocco_x: 'NUOVO_MOTIVO', blocco_x_chiave: 'motivi.nuovo' })).toBe('NUOVO_MOTIVO')
  })

  it('4) registro in volo -> spenta col motivo (fail-closed)', () => {
    registro.value = []
    caricato.value = false
    const a = useAzioneRiga('AZIONE_X')
    expect(a.pronta.value).toBe(false)
    expect(a.bloccata({ blocco_x: null })).toBe(true)
    expect(a.motivo({ blocco_x: null })).toBe('Caricamento...')
  })

  it('5) azione non iscritta -> spenta, e lo dice', () => {
    const a = useAzioneRiga('AZIONE_Y')
    expect(a.pronta.value).toBe(false)
    expect(a.bloccata({ blocco_x: null })).toBe(true)
    expect(a.motivo({ blocco_x: null })).toBe('Non attiva nel registro')
  })

  // ⛔ La fetch fallita non riprova da sola: «Caricamento...» resterebbe per
  //    sempre, e direbbe una cosa falsa.
  it('6) registro non letto -> spenta, e non «Caricamento...»', () => {
    registro.value = []
    caricato.value = false
    errore.value = new Error('rete')
    const a = useAzioneRiga('AZIONE_X')
    expect(a.bloccata({ blocco_x: null })).toBe(true)
    expect(a.motivo({ blocco_x: null })).toBe('Registro non letto')
  })
})
