// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: i testi del BB `RigheEccezioniDrawer` esistono per ogni documento che
//        lo monta (contratto, offerta) e in ogni lingua.
// Note: ⭐ PERCHE' QUESTO TEST. Il BB legge i testi che nominano il documento
//       con una chiave COSTRUITA (`${i18nDocumento}.${chiave}`, funzione `td`):
//       `scripts/check_i18n_keys.py` la conta fra i punti ciechi, e una chiave
//       mancante sull'offerta si vedrebbe solo a video, come la chiave stessa
//       al posto del testo. Qui si leggono dal sorgente le chiavi passate a
//       `td(...)` e a `tv(...)` (il vocabolario, in `vendite.contratti`) e si
//       cercano nei due file di lingua.
//
// Indice test:
//  1. ogni chiave di `td` esiste nei namespace di contratto e offerta, it ed en
//  2. ogni chiave letterale di `tv` esiste in `vendite.contratti`, it ed en
//  3. i due involucri montano il BB col loro namespace
//  4. ogni erogazione e ogni fonte ha la sua etichetta (chiave costruita dal
//     valore che arriva dal DB: `tipo_erogazione_<v>`, `fonte_quantita_value_<v>`)
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import it_ from '../../../locales/it.json'
import en from '../../../locales/en.json'
import sorgenteBB from './RigheEccezioniDrawer.vue?raw'
import sorgenteContratto from '../../components/ContrattoRigheDrawer.vue?raw'
import sorgenteOfferta from '../../offerte/components/OffertaRigheDrawer.vue?raw'
import { FONTE_QUANTITA_ATTESA, TIPO_ECCEZIONE, TIPO_EROGAZIONE } from '../../constants'

const LINGUE = { it: it_, en }
const NAMESPACE_DOCUMENTO = ['vendite.contratti', 'vendite.offerte']

// Le chiavi LETTERALI passate a una funzione di testo nel sorgente del BB.
function chiaviDi(funzione) {
  const re = new RegExp(`\\b${funzione}\\('([a-z_.]+)'`, 'g')
  return [...new Set([...sorgenteBB.matchAll(re)].map((m) => m[1]))]
}

function leggi(dizionario, percorso) {
  return percorso.split('.').reduce((o, k) => (o == null ? undefined : o[k]), dizionario)
}

describe('RigheEccezioniDrawer — testi', () => {
  it('ogni chiave che nomina il documento esiste per contratto e offerta', () => {
    const chiavi = chiaviDi('td')
    expect(chiavi.length).toBeGreaterThan(5)
    const mancanti = []
    for (const [lingua, diz] of Object.entries(LINGUE)) {
      for (const ns of NAMESPACE_DOCUMENTO) {
        for (const k of chiavi) {
          if (typeof leggi(diz, `${ns}.${k}`) !== 'string') mancanti.push(`${lingua}:${ns}.${k}`)
        }
      }
    }
    expect(mancanti).toEqual([])
  })

  it('ogni chiave letterale del vocabolario esiste in vendite.contratti', () => {
    const chiavi = chiaviDi('tv')
    expect(chiavi.length).toBeGreaterThan(10)
    const mancanti = []
    for (const [lingua, diz] of Object.entries(LINGUE)) {
      for (const k of chiavi) {
        if (typeof leggi(diz, `vendite.contratti.${k}`) !== 'string') mancanti.push(`${lingua}:${k}`)
      }
    }
    expect(mancanti).toEqual([])
  })

  it('i due involucri montano il BB col loro namespace e la loro lista', () => {
    expect(sorgenteContratto).toContain('i18n-documento="vendite.contratti"')
    expect(sorgenteContratto).toContain('lista-codice="vendite.contratto_righe"')
    expect(sorgenteOfferta).toContain('i18n-documento="vendite.offerte"')
    expect(sorgenteOfferta).toContain('lista-codice="vendite.offerta_righe"')
  })

  // Le tendine mostrano i valori che il DB dichiara per l'articolo: l'etichetta
  // e' costruita dal valore, e una mancante si vedrebbe solo a video.
  it('ogni erogazione e ogni fonte ha la sua etichetta', () => {
    const chiavi = [
      ...Object.values(TIPO_EROGAZIONE).map((v) => `tipo_erogazione_${v.toLowerCase()}`),
      ...Object.values(FONTE_QUANTITA_ATTESA).map((v) => `fonte_quantita_value_${v.toLowerCase()}`),
    ]
    const mancanti = []
    for (const [lingua, diz] of Object.entries(LINGUE)) {
      for (const k of chiavi) {
        if (typeof leggi(diz, `vendite.contratti.${k}`) !== 'string') mancanti.push(`${lingua}:${k}`)
      }
    }
    expect(mancanti).toEqual([])
  })

  // Il Tag del tipo di riga e quello dell'origine sono costruiti dal valore
  // (`tipo_eccezione_${…}`, `origine_${…}`); il tag della fonte senza
  // quantita' sulla riga idem. ADESIONE (G-0-ter) e DURATA (G-9) ne sono
  // l'esempio: entrate col DB, senza etichetta sarebbero un buco a video.
  it('ogni tipo di riga, origine e fonte a valle ha la sua etichetta', () => {
    const chiavi = [
      ...Object.values(TIPO_ECCEZIONE)
        .filter((v) => v !== TIPO_ECCEZIONE.DA_LISTINO)
        .map((v) => `tipo_eccezione_${v}`),
      ...Object.values(TIPO_ECCEZIONE).map((v) => `origine_${v.toLowerCase()}`),
      ...Object.values(FONTE_QUANTITA_ATTESA)
        .filter((v) => v !== FONTE_QUANTITA_ATTESA.FISSA)
        .map((v) => `fonte_quantita_tag_${v.toLowerCase()}`),
    ]
    const mancanti = []
    for (const [lingua, diz] of Object.entries(LINGUE)) {
      for (const k of chiavi) {
        if (typeof leggi(diz, `vendite.contratti.${k}`) !== 'string') mancanti.push(`${lingua}:${k}`)
      }
    }
    expect(mancanti).toEqual([])
  })
})
