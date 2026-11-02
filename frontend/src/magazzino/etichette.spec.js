// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il presidio delle etichette COSTRUITE DINAMICAMENTE del dominio
//        magazzino (`${prefisso}.${valore}`): per ogni valore di ogni
//        vocabolario, la chiave esiste nei locales VERI (it e en) — cioe'
//        l'etichetta non ricade sul codice.
// Note: ⛔ `check_i18n_keys` dichiara queste chiavi «punto cieco»: non puo'
//       vederle citate nel codice, quindi un refuso in una chiave — o un
//       valore aggiunto al vocabolario senza la sua riga — non fa rosso da
//       nessuna parte e mostra il CODICE a video. Qui si legge il JSON dei
//       locales, non una copia dei prefissi: se un prefisso cambia in
//       `etichette.js` e i locales no, il test lo vede.
//       Stessa forma di `pagamenti/etichette.spec.js`.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

import it_ from '../locales/it.json'
import en from '../locales/en.json'
import { ESITI_PIANO, SORGENTI_MOVIMENTO, STATI_DOCUMENTO_INTERNO } from './vocabolari'

const LOCALES = { it: it_, en }
// La lingua corrente del `useI18n` finto: si cambia fra un giro e l'altro.
let lingua = 'it'
// L'ultima chiave che `t` ha RISOLTO: `labelOrCode` chiama `t` solo se `te` ha
// detto che la chiave c'e', quindi «t non e' stato chiamato» = «e' uscito il
// codice».
let chiaveRisolta = null

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
      chiaveRisolta = chiave
      return testo.replace(/\{(\w+)\}/g, (m, k) => (k in params ? String(params[k]) : m))
    },
  }),
}))

const { useEtichetteMagazzino } = await import('./etichette')

// Scopo: prova `fn(valore)` su ogni valore del vocabolario, in entrambe le
//        lingue: una chiave deve essere stata RISOLTA (non il ripiego sul codice).
function ogniValoreRisolve(nome, valori, fn) {
  for (const l of Object.keys(LOCALES)) {
    lingua = l
    const e = useEtichetteMagazzino()
    for (const v of valori) {
      chiaveRisolta = null
      const etichetta = fn(e, v)
      expect(chiaveRisolta, `${nome}: «${v}» non ha una chiave in ${l} (a video uscirebbe «${etichetta}»)`)
        .not.toBeNull()
      expect(etichetta).not.toBe('')
    }
  }
}

describe('useEtichetteMagazzino — ogni vocabolario ha la sua etichetta in it e en', () => {
  it('stato del documento interno (specchio del CHECK)', () => {
    ogniValoreRisolve('statoDocumento', STATI_DOCUMENTO_INTERNO, (e, v) => e.statoDocumento(v))
  })

  it('esito del piano di inventario', () => {
    ogniValoreRisolve('esitoPiano', ESITI_PIANO, (e, v) => e.esitoPiano(v))
  })

  it('sorgente di un movimento', () => {
    ogniValoreRisolve('sorgenteMovimento', SORGENTI_MOVIMENTO, (e, v) => e.sorgenteMovimento(v))
  })

  it('le opzioni dei Select portano TUTTI i valori del vocabolario, etichettati', () => {
    lingua = 'it'
    const e = useEtichetteMagazzino()
    expect(e.opzioniStatoDocumento().map((o) => o.value)).toEqual([...STATI_DOCUMENTO_INTERNO])
    expect(e.opzioniEsitoPiano().map((o) => o.value)).toEqual([...ESITI_PIANO])
    expect(e.opzioniSorgenteMovimento().map((o) => o.value)).toEqual([...SORGENTI_MOVIMENTO])
    for (const o of e.opzioniStatoDocumento()) expect(o.label).not.toBe(o.value)
  })
})

describe('useEtichetteMagazzino — fail-visible', () => {
  it('un valore sconosciuto mostra il CODICE, mai la chiave grezza ne\' il vuoto', () => {
    lingua = 'it'
    const e = useEtichetteMagazzino()
    expect(e.statoDocumento('STATO_NUOVO')).toBe('STATO_NUOVO')
    expect(e.esitoPiano('ESITO_NUOVO')).toBe('ESITO_NUOVO')
  })
})
