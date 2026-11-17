// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa la CHIAVE D'INGRESSO del tipo nel payload degli indirizzi
//        (`toPayloadArray`, il solo punto da cui i drawer soggetto, cliente,
//        fornitore e indirizzi inviano): `tipo_indirizzo_codice_interno`, nelle
//        due forme. Dal 2026-11-01 (regola C del naming) le madri del DB
//        rifiutano la vecchia `tipo_indirizzo_codice` con E_CAMPO_NON_AMMESSO,
//        senza alias: un form che la mandasse non creerebbe piu' nessun indirizzo.
// Note: si mockano i lookup: qui si prova il payload, non l'API.
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, nextTick } from 'vue'

vi.mock('../../core/composables/useLookup', async () => {
  const { ref } = await import('vue')
  return {
    useLookup: () => ({ items: ref([]), loading: ref(false), loaded: ref(true), load: async () => {} }),
  }
})

vi.mock('../api/anagrafiche', () => ({
  lookupStati: vi.fn(),
  lookupCodiciPostaliByComune: async () => ({ data: { data: { results: [] } } }),
}))

vi.mock('../../core/apiCore', () => ({
  lookupTipiIndirizzoNatura: vi.fn(),
  lookupTipiIndirizzoTipoRuolo: vi.fn(),
}))

const { useIndirizzoSoggettoForm } = await import('./useIndirizzoSoggettoForm')
const { lookupTipiIndirizzoTipoRuolo } = await import('../../core/apiCore')

const MATRICE = [
  { codice_interno: 'RES', descrizione: 'Residenza', obbligatorio: true },
  { codice_interno: 'FATT', descrizione: 'Fatturazione', obbligatorio: false },
]

describe('useIndirizzoSoggettoForm — chiave d\'ingresso del tipo', () => {
  it('ogni indirizzo inviato porta `tipo_indirizzo_codice_interno`, mai la chiave vecchia', () => {
    const s = useIndirizzoSoggettoForm()
    s.setMatrice(MATRICE)
    // RES con la via del catalogo (forma normalizzata).
    s.form.comune_id = 10
    s.switchTipo('FATT')
    // FATT in forma libera.
    s.form._isLibera = true
    s.form.indirizzo_libero = 'Hauptstrasse 5'
    s.form.stato_id = 2

    const payload = s.toPayloadArray()

    expect(payload.map((p) => p.tipo_indirizzo_codice_interno)).toEqual(['RES', 'FATT'])
    for (const p of payload) expect(p).not.toHaveProperty('tipo_indirizzo_codice')
  })
})

// Scopo: Il picker dei tipi (R-2 di brief-db-copia-indirizzo-soggetto) porta
//        anche i tipi NON ammessi, col motivo: nel form ne entrano solo gli
//        ammessi, e il primo obbligatorio si sceglie fra quelli. La riga
//        sintetica del «Cambia» non porta `ammesso` e vale ammessa.
describe('useIndirizzoSoggettoForm — solo i tipi ammessi dal picker', () => {
  it('un tipo spento non entra nella barra dei tipi e non si pre-seleziona', () => {
    const s = useIndirizzoSoggettoForm()
    s.setMatrice([
      { codice_interno: 'SEDELEG', descrizione: 'Sede legale', obbligatorio: true, ammesso: false,
        reason_key: 'anagrafiche.indirizzi.tipo_blocco.gia_presente', reason_valori: ['Sede legale'] },
      { codice_interno: 'FATT', descrizione: 'Fatturazione', obbligatorio: false, ammesso: true },
    ])
    expect(s.tipiStato.value.map((t) => t.codice_interno)).toEqual(['FATT'])
    expect(s.form.tipo_indirizzo_codice_interno).toBe('FATT')
  })

  it('la riga senza `ammesso` (il «Cambia») resta', () => {
    const s = useIndirizzoSoggettoForm()
    s.setMatrice([{ codice_interno: 'RES', descrizione: 'Residenza', obbligatorio: true }])
    expect(s.form.tipo_indirizzo_codice_interno).toBe('RES')
  })
})

// Scopo: Il picker del ruolo da assegnare porta il soggetto scelto (R-1 di
//        brief-db-fornitore-privato-indirizzi, 2026-11-17): la natura del
//        soggetto decide ammessi e obbligatori, quindi alla scelta si rilegge;
//        e una lettura vecchia (senza soggetto) arrivata dopo non vince.
describe('useIndirizzoSoggettoForm — il ruolo da assegnare segue il soggetto', () => {
  const risposta = (righe) => ({ data: { data: { results: righe } } })
  const SENZA = [{ codice_interno: 'SEDELEG', descrizione: 'Sede legale', obbligatorio: true, ammesso: true }]
  const COL_PRIVATO = [
    { codice_interno: 'SEDELEG', descrizione: 'Sede legale', obbligatorio: false, ammesso: false },
    { codice_interno: 'FATT', descrizione: 'Fatturazione', obbligatorio: true, ammesso: true },
  ]

  beforeEach(() => { lookupTipiIndirizzoTipoRuolo.mockReset() })

  it('il soggetto arriva al lookup, `null` finche\' non e\' scelto', async () => {
    lookupTipiIndirizzoTipoRuolo.mockResolvedValue(risposta([]))
    const s = useIndirizzoSoggettoForm()
    await s.loadMatriceRuolo('FO')
    await s.loadMatriceRuolo('FO', 'sogg-1')
    expect(lookupTipiIndirizzoTipoRuolo.mock.calls).toEqual([['FO', null], ['FO', 'sogg-1']])
  })

  it('scelto il soggetto, il picker si rilegge con lui', async () => {
    lookupTipiIndirizzoTipoRuolo.mockResolvedValue(risposta(COL_PRIVATO))
    const s = useIndirizzoSoggettoForm()
    const soggetto = ref(null)
    s.seguiSoggettoDelRuolo('FO', () => soggetto.value?.id)
    soggetto.value = { id: 'sogg-1' }
    await nextTick()
    await Promise.resolve()
    expect(lookupTipiIndirizzoTipoRuolo).toHaveBeenCalledWith('FO', 'sogg-1')
    expect(s.tipiStato.value.map((t) => t.codice_interno)).toEqual(['FATT'])
  })

  it('soggetto tolto (o riportato a null dal reset): nessuna lettura', async () => {
    lookupTipiIndirizzoTipoRuolo.mockResolvedValue(risposta(COL_PRIVATO))
    const s = useIndirizzoSoggettoForm()
    const soggetto = ref({ id: 'sogg-1' })
    s.seguiSoggettoDelRuolo('FO', () => soggetto.value?.id)
    soggetto.value = null
    await nextTick()
    expect(lookupTipiIndirizzoTipoRuolo).not.toHaveBeenCalled()
  })

  it('la lettura senza soggetto che arriva dopo non sovrascrive quella col soggetto', async () => {
    let rispondiVecchia
    lookupTipiIndirizzoTipoRuolo
      .mockImplementationOnce(() => new Promise((r) => { rispondiVecchia = r }))
      .mockResolvedValueOnce(risposta(COL_PRIVATO))
    const s = useIndirizzoSoggettoForm()
    const vecchia = s.loadMatriceRuolo('FO')
    await s.loadMatriceRuolo('FO', 'sogg-1')
    rispondiVecchia(risposta(SENZA))
    await vecchia
    expect(s.form.tipo_indirizzo_codice_interno).toBe('FATT')
  })

  it('una lettura partita prima del reset non ripopola la matrice svuotata', async () => {
    let rispondi
    lookupTipiIndirizzoTipoRuolo.mockImplementationOnce(() => new Promise((r) => { rispondi = r }))
    const s = useIndirizzoSoggettoForm()
    const inVolo = s.loadMatriceRuolo('FO')
    s.reset()
    rispondi(risposta(COL_PRIVATO))
    await inVolo
    expect(s.tipiStato.value).toEqual([])
    expect(s.form.tipo_indirizzo_codice_interno).toBeNull()
  })
})
