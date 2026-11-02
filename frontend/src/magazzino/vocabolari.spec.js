// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il presidio delle DUE FAMIGLIE del documento interno (`FAMIGLIE`):
//        ogni famiglia dichiara TUTTO cio' che i componenti unici (lista,
//        dialog, drawer, form di riga) leggono — e le chiavi i18n costruite
//        dalla radice della famiglia esistono nei locales VERI, in it e en.
// Note: ⭐ E' il presidio di Q-1 (una implementazione, due configurazioni): il
//       giorno in cui nasce la terza famiglia, o una proprieta' nuova, il
//       rosso arriva da qui e non da un `undefined` nel render.
//       ⛔ Le chiavi `${f.i18n}.<foglia>` sono un punto cieco di
//       `check_i18n_keys` (costruite dinamicamente): senza questo spec, una
//       famiglia senza la sua riga nei locales mostrerebbe la CHIAVE a video.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'

import it_ from '../locales/it.json'
import en from '../locales/en.json'
import { TAB_ENTITIES } from '../core/constants'
import { FAMIGLIA, FAMIGLIE, SORGENTI_MOVIMENTO, STATI_DOCUMENTO_INTERNO } from './vocabolari'

const LOCALES = { it: it_, en }

// Le proprieta' che i componenti LEGGONO da una famiglia. Aggiungerne una qui
// vuol dire che un componente ha cominciato a leggerla.
const PROPRIETA = [
  'codice', 'singolare', 'rotta', 'listaCodice', 'listaRigheCodice', 'i18n',
  'campoQta', 'qtaZeroAmmessa', 'qtaMin', 'conMotivo', 'conDescrizione',
  'haPiano', 'tabEntity', 'filtroMovimenti', 'sorgente',
]

// Le foglie i18n costruite da `${f.i18n}.` nei componenti (lista, dialog,
// drawer). Una foglia nuova nel codice si aggiunge qui.
const FOGLIE_I18N = [
  'titolo_singolare', 'nuovo', 'search_placeholder', 'aperto', 'eliminato',
  'conferma_elimina', 'nessuna_riga',
]

function risolvi(locale, chiave) {
  return chiave.split('.').reduce(
    (o, k) => (o != null && typeof o === 'object' ? o[k] : undefined),
    locale,
  )
}

describe('FAMIGLIE — ogni famiglia dichiara tutto cio\' che i componenti leggono', () => {
  it('le famiglie sono quelle di FAMIGLIA, e il codice e\' la chiave', () => {
    expect(Object.keys(FAMIGLIE).sort()).toEqual(Object.values(FAMIGLIA).sort())
    for (const [codice, f] of Object.entries(FAMIGLIE)) expect(f.codice).toBe(codice)
  })

  it.each(Object.values(FAMIGLIE))('$codice: tutte le proprieta\', nessuna undefined', (f) => {
    for (const p of PROPRIETA) {
      expect(f[p], `FAMIGLIE.${f.codice}.${p}`).not.toBeUndefined()
    }
    expect(Object.isFrozen(f)).toBe(true)
  })

  it.each(Object.values(FAMIGLIE))('$codice: i valori che il backend pretende', (f) => {
    // La quantita' ha il nome FISICO della colonna (types.py del backend).
    expect(['qta_contata', 'qta_delta']).toContain(f.campoQta)
    // Il segmento di URL e il codice di lista sono coerenti con la famiglia.
    expect(f.listaCodice).toBe(`magazzino.${f.codice}`)
    expect(f.rotta).toBe(`magazzino-${f.codice}`)
    expect(f.i18n).toBe(`magazzino.${f.codice}`)
    // La chiave cross-tab viene dall'enum, mai un literal.
    expect(Object.values(TAB_ENTITIES)).toContain(f.tabEntity)
    // La sorgente dei movimenti e' una di quelle dichiarate.
    expect(SORGENTI_MOVIMENTO).toContain(f.sorgente)
    // Il filtro del registro ha la forma `<singolare>_id`.
    expect(f.filtroMovimenti).toBe(`${f.singolare}_id`)
  })

  it('le due famiglie differiscono dove il DB le distingue, e SOLO li\'', () => {
    const inv = FAMIGLIE[FAMIGLIA.INVENTARI]
    const rett = FAMIGLIE[FAMIGLIA.RETTIFICHE]
    expect(inv.haPiano).toBe(true)
    expect(rett.haPiano).toBe(false)
    expect(inv.conMotivo).toBe(false)
    expect(rett.conMotivo).toBe(true)
    expect(inv.conDescrizione).toBe(true)
    expect(rett.conDescrizione).toBe(false)
    expect(inv.campoQta).not.toBe(rett.campoQta)
    // La regola della quantita' segue il CHECK: contata >= 0, delta <> 0.
    expect(inv.qtaZeroAmmessa).toBe(true)
    expect(inv.qtaMin).toBe(0)
    expect(rett.qtaZeroAmmessa).toBe(false)
    expect(rett.qtaMin).toBeNull()
  })
})

describe('FAMIGLIE — le chiavi i18n costruite dalla radice esistono in it e en', () => {
  for (const [lang, locale] of Object.entries(LOCALES)) {
    it.each(Object.values(FAMIGLIE))(`$codice (${lang})`, (f) => {
      for (const foglia of FOGLIE_I18N) {
        const chiave = `${f.i18n}.${foglia}`
        expect(typeof risolvi(locale, chiave), `${chiave} manca in ${lang}`).toBe('string')
      }
      // Le due foglie del form di riga costruite dal nome della quantita'.
      for (const prefisso of ['campo', 'aiuto']) {
        const chiave = `magazzino.documenti_interni.riga.${prefisso}_${f.campoQta}`
        expect(typeof risolvi(locale, chiave), `${chiave} manca in ${lang}`).toBe('string')
      }
    })
  }
})

describe('STATI_DOCUMENTO_INTERNO — lo specchio del CHECK', () => {
  // Lo stesso vocabolario che il backend pinna su `chk_mag_inventari_stato`
  // (`STATI_DOCUMENTO_INTERNO` in magazzino_service.py): se uno dei due si
  // muove, il lettore umano trova qui l'altra meta'.
  it('sono i quattro stati della matrice, nell\'ordine del ciclo di vita', () => {
    expect([...STATI_DOCUMENTO_INTERNO]).toEqual(['DRAFT', 'CONFIRM', 'POSTED', 'CANCEL'])
  })
})
