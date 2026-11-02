// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il presidio delle azioni di riga di una riga contabile — una sede
//        per il drawer e per la coda (FE-4, D20): quale voce, da dove, spenta
//        con quale motivo, e con quale verbo sotto una distinta registrata.
// Note: ⛔ Le chiavi di `VERBO_TRANSIZIONE_RIGA` sono valori di una mappa, non
//       `t('…')`: `check_i18n_keys` non le vede. Qui si leggono i locales
//       VERI (it e en) con un `useI18n` finto, come in `etichette.spec.js`:
//       un refuso in una chiave mostrerebbe «Porta a …» al posto del verbo
//       senza nessun rosso.
//       I collaboratori sono mockati: conferma, handler API e client — qui si
//       prova la COSTRUZIONE delle voci, non il giro HTTP.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

import it_ from '../../locales/it.json'
import en from '../../locales/en.json'

const LOCALES = { it: it_, en }
let lingua = 'it'

// Scopo: risolve `a.b.c` nel JSON della lingua corrente; `undefined` se manca.
function risolvi(chiave) {
  return chiave.split('.').reduce(
    (o, k) => (o != null && typeof o === 'object' ? o[k] : undefined),
    LOCALES[lingua],
  )
}

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    te: (chiave) => typeof risolvi(chiave) === 'string',
    t: (chiave, params = {}) => {
      const testo = risolvi(chiave)
      if (typeof testo !== 'string') return chiave
      return testo.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m))
    },
  }),
}))
vi.mock('../../core/composables/useApiHandler', () => ({
  useApiHandler: () => ({ execute: vi.fn(async (fn) => fn()) }),
}))
vi.mock('../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: vi.fn() }),
}))
vi.mock('../api/pagamenti', () => ({
  cambiaStatoRiga: vi.fn(),
  eliminaRiga: vi.fn(),
}))

const {
  MODO_ABBINA, VERBO_TRANSIZIONE_RIGA, useAzioniRigaContabile,
} = await import('./useAzioniRigaContabile')

// Il catalogo e la matrice come li consegna il backend dopo D20-e (strada b).
const STATI = [
  { codice_interno: 'DA_ABBINARE', descrizione: 'Da abbinare', is_final: false },
  { codice_interno: 'ABBINATA', descrizione: 'Abbinata', is_final: false },
  { codice_interno: 'SOSPESA', descrizione: 'Sospesa', is_final: false },
  { codice_interno: 'SCARTATA', descrizione: 'Scartata', is_final: false },
  { codice_interno: 'POSTATA', descrizione: 'Registrata', is_final: true },
]
const MATRICE = {
  DA_ABBINARE: ['ABBINATA', 'SOSPESA', 'SCARTATA'],
  ABBINATA: ['SOSPESA'],
  SOSPESA: ['DA_ABBINARE', 'ABBINATA', 'SCARTATA'],
  SCARTATA: ['SOSPESA'],
  POSTATA: [],
}

// Scopo: una fabbrica con i default del caso «distinta aperta, non readonly».
function fabbrica(over = {}) {
  const onAbbina = vi.fn()
  const ricarica = vi.fn()
  const azioni = useAzioniRigaContabile({
    statiRiga: () => STATI,
    transizioniRiga: () => MATRICE,
    testataDi: () => ({ righeLavorabili: true, registrata: false }),
    readonly: () => false,
    onAbbina,
    ricarica,
    ...over,
  })
  return { ...azioni, onAbbina, ricarica }
}

const riga = (stato, extra = {}) => ({ id: 1, stato_codice: stato, importo: 10, ...extra })
const chiavi = (voci) => voci.map((v) => v.key)
const voce = (voci, key) => voci.find((v) => v.key === key)

describe('useAzioniRigaContabile — le voci vengono dalla matrice', () => {
  it('su una DA_ABBINARE: Abbina, Sospendi, Scarta — e ABBINATA non e\' un «porta a»', () => {
    lingua = 'it'
    const { buildRowActions } = fabbrica()
    const voci = buildRowActions(riga('DA_ABBINARE'))
    expect(chiavi(voci)).toEqual(['abbina', 'stato-SOSPESA', 'stato-SCARTATA'])
    expect(voce(voci, 'abbina').disabled).toBe(false)
    expect(voce(voci, 'stato-SOSPESA').label).toBe('Sospendi')
    expect(voce(voci, 'stato-SCARTATA').label).toBe('Scarta')
  })

  it('su una SOSPESA: Riporta da abbinare e Scarta, con Abbina acceso', () => {
    lingua = 'it'
    const { buildRowActions } = fabbrica()
    const voci = buildRowActions(riga('SOSPESA'))
    expect(chiavi(voci)).toEqual(['abbina', 'stato-DA_ABBINARE', 'stato-SCARTATA'])
    expect(voce(voci, 'stato-DA_ABBINARE').label).toBe('Riporta da abbinare')
  })

  it('da SCARTATA il verbo e\' «Riprendi» (la coppia vince sullo stato di arrivo) e Abbina e\' spento col motivo', () => {
    lingua = 'it'
    const { buildRowActions } = fabbrica()
    const voci = buildRowActions(riga('SCARTATA'))
    expect(voce(voci, 'stato-SOSPESA').label).toBe('Riprendi')
    const abbina = voce(voci, 'abbina')
    expect(abbina.disabled).toBe(true)
    expect(abbina.tooltip).toBe(risolvi('pagamenti.abbina.non_da_questo_stato'))
  })

  it('su una ABBINATA si RI-abbina (D20-e): Abbina acceso, resta solo la sospensione', () => {
    const { buildRowActions } = fabbrica()
    const voci = buildRowActions(riga('ABBINATA'))
    expect(chiavi(voci)).toEqual(['abbina', 'stato-SOSPESA'])
    expect(voce(voci, 'abbina').disabled).toBe(false)
  })

  it('«Elimina» c\'e\' solo dove il contenuto si lavora, spento dal database', () => {
    const { buildRowActions } = fabbrica({ conElimina: true })
    const bloccata = riga('ABBINATA', {
      can_eliminare: false,
      elimina_blocco_reason: 'DISTINTA_VALIDATA',
      elimina_blocco_reason_key: 'pagamenti.righe.elimina_reason.distinta_validata',
    })
    const elimina = voce(buildRowActions(bloccata), 'elimina')
    expect(elimina.disabled).toBe(true)
    expect(elimina.tooltip).toBe(risolvi('pagamenti.righe.elimina_reason.distinta_validata'))
    expect(voce(buildRowActions(riga('ABBINATA', { can_eliminare: true })), 'elimina').disabled).toBe(false)
  })
})

describe('useAzioniRigaContabile — i fatti della testata cambiano il verbo', () => {
  it('sotto una distinta REGISTRATA la sospesa si «abbina e registra», col cancello della registrazione', () => {
    lingua = 'it'
    const { buildRowActions, onAbbina } = fabbrica({
      testataDi: () => ({ righeLavorabili: true, registrata: true }),
    })
    const voci = buildRowActions(riga('SOSPESA'))
    const abbina = voce(voci, 'abbina')
    expect(abbina.label).toBe('Abbina e registra')
    expect(abbina.action).toBe('registra_distinta')
    expect(abbina.disabled).toBe(false)
    abbina.command()
    expect(onAbbina).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }), MODO_ABBINA.REGISTRA)
    // E sospese/scartate si lavorano ancora (D20-c): niente e' spento.
    expect(voce(voci, 'stato-SCARTATA').disabled).toBe(false)
  })

  it('sotto una distinta le cui righe NON si lavorano (annullata) tutto e\' spento col motivo', () => {
    lingua = 'it'
    const { buildRowActions } = fabbrica({
      testataDi: () => ({ righeLavorabili: false, registrata: false }),
      conElimina: true,
    })
    const voci = buildRowActions(riga('SOSPESA'))
    for (const v of voci.filter((x) => x.key !== 'elimina')) {
      expect(v.disabled).toBe(true)
      expect(v.tooltip).toBe(risolvi('pagamenti.distinte.foglio_annullato'))
    }
    expect(voce(voci, 'abbina').label).toBe(risolvi('pagamenti.abbina.azione'))
  })

  // ⭐ La regola e' la BANDIERA del catalogo, non «finale e non registrata»:
  //    una testata che dice «lavorabile» non spegne niente anche se non e'
  //    registrata (la BOZZA), e la chiave del cestino dell'annullata — che
  //    arriva dalla check del DB — esiste nei locales (R-1).
  it('con righeLavorabili true niente e\' spento dal foglio, registrata o no', () => {
    const { buildRowActions } = fabbrica({
      testataDi: () => ({ righeLavorabili: true, registrata: false }),
    })
    const voci = buildRowActions(riga('SOSPESA'))
    expect(voci.every((v) => v.tooltip !== risolvi('pagamenti.distinte.foglio_annullato'))).toBe(true)
    expect(voce(voci, 'stato-SCARTATA').disabled).toBe(false)
  })

  it('il cestino dell\'annullata dice il motivo della check del database', () => {
    lingua = 'it'
    const { buildRowActions } = fabbrica({
      testataDi: () => ({ righeLavorabili: false, registrata: false }),
      conElimina: true,
    })
    const elimina = voce(buildRowActions(riga('DA_ABBINARE', {
      can_eliminare: false,
      elimina_blocco_reason: 'DISTINTA_ANNULLATA',
      elimina_blocco_reason_key: 'pagamenti.righe.elimina_reason.distinta_annullata',
    })), 'elimina')
    expect(elimina.disabled).toBe(true)
    expect(elimina.tooltip).toBe(risolvi('pagamenti.righe.elimina_reason.distinta_annullata'))
  })

  it('una riga gia\' registrata (stato finale a catalogo) e\' spenta col suo motivo', () => {
    lingua = 'it'
    const { buildRowActions } = fabbrica()
    const voci = buildRowActions(riga('POSTATA'))
    expect(voce(voci, 'abbina').disabled).toBe(true)
    expect(voce(voci, 'abbina').tooltip).toBe(risolvi('pagamenti.righe.gia_registrata'))
  })

  it('in sola lettura non c\'e\' nessuna voce: e\' un permesso, si nasconde', () => {
    const { buildRowActions } = fabbrica({ readonly: () => true })
    expect(buildRowActions(riga('DA_ABBINARE'))).toEqual([])
  })
})

describe('useAzioniRigaContabile — le chiavi dei verbi esistono nei locales veri', () => {
  for (const l of Object.keys(LOCALES)) {
    it(`ogni verbo di VERBO_TRANSIZIONE_RIGA risolve in ${l}`, () => {
      lingua = l
      for (const [coppia, chiave] of Object.entries(VERBO_TRANSIZIONE_RIGA)) {
        expect(typeof risolvi(chiave), `${coppia} → ${chiave} manca in ${l}`).toBe('string')
      }
    })
  }
})
