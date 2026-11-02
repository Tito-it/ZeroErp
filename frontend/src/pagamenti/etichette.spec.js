// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il presidio delle etichette COSTRUITE DINAMICAMENTE del dominio
//        incassi (`${prefisso}_${valore}`): per ogni valore di ogni
//        vocabolario, la chiave esiste nei locales VERI (it e en) — cioe'
//        l'etichetta non ricade sul codice.
// Note: ⛔ `check_i18n_keys` dichiara queste chiavi «punto cieco»: non puo'
//       vederle citate nel codice, quindi un refuso in una chiave — o un
//       valore aggiunto al vocabolario senza la sua riga — non fa rosso da
//       nessuna parte e mostra il CODICE a video (fail-visible, ma senza un
//       presidio che lo dica prima dell'operatore). Qui si legge il JSON dei
//       locales, non una copia dei prefissi: se un prefisso cambia in
//       `etichette.js` e i locales no, il test lo vede.
//       Il rilievo e' del 2026-09-18, alla rilettura critica di P-7: le due
//       chiavi nuove `motivo_nota_credito_*` non avevano nessun presidio.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

import it_ from '../locales/it.json'
import en from '../locales/en.json'
import { NATURA_DOC } from '../core/constants'
import {
  CHI_E_IN_CREDITO,
  DESTINAZIONI,
  MOTIVI_FUORI_CAPIENZA,
  ORIGINI_DISTINTA,
  ROTTA_PER_CODA,
  STATI_SISTEMAZIONE,
  TIPI_CANALE,
} from './vocabolari'

const LOCALES = { it: it_, en }
// La lingua corrente del `useI18n` finto: si cambia fra un giro e l'altro.
let lingua = 'it'
// L'ultima chiave che `t` ha RISOLTO: `labelOrCode` chiama `t` solo se `te` ha
// detto che la chiave c'e', quindi «t non e' stato chiamato» = «e' uscito il
// codice». ⚠️ E' questo il predicato, non «etichetta ≠ codice»: `tipo_psp` vale
// legittimamente «PSP» — un acronimo E' la sua etichetta.
let chiaveRisolta = null

// Scopo: risolve `a.b.c` nel JSON della lingua corrente; `undefined` se manca.
function risolvi(chiave) {
  return chiave.split('.').reduce(
    (o, k) => (o != null && typeof o === 'object' ? o[k] : undefined),
    LOCALES[lingua],
  )
}

// Il `useI18n` finto legge i locales VERI: `te` = «la chiave c'e'», `t` =
// il testo con i `{segnaposto}` sostituiti — abbastanza per le etichette.
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

const { useEtichettePagamenti } = await import('./etichette')

// Scopo: prova `fn(valore)` su ogni valore del vocabolario, in entrambe le
//        lingue: una chiave deve essere stata RISOLTA (non il ripiego sul codice).
function ogniValoreRisolve(nome, valori, fn) {
  for (const l of Object.keys(LOCALES)) {
    lingua = l
    const e = useEtichettePagamenti()
    for (const v of valori) {
      chiaveRisolta = null
      const etichetta = fn(e, v)
      expect(chiaveRisolta, `${nome}: «${v}» non ha una chiave in ${l} (a video uscirebbe «${etichetta}»)`)
        .not.toBeNull()
      expect(etichetta).not.toBe('')
    }
  }
}

describe('useEtichettePagamenti — ogni vocabolario ha la sua etichetta in it e en', () => {
  it('chi e\' in credito', () => {
    ogniValoreRisolve('credito', CHI_E_IN_CREDITO, (e, v) => e.credito(v))
  })

  it('tipo di canale', () => {
    ogniValoreRisolve('tipoCanale', TIPI_CANALE, (e, v) => e.tipoCanale(v))
  })

  it('destinazione di una sistemazione', () => {
    ogniValoreRisolve('destinazione', DESTINAZIONI, (e, v) => e.destinazione(v))
  })

  it('stato di una sistemazione', () => {
    ogniValoreRisolve('statoSistemazione', STATI_SISTEMAZIONE, (e, v) => e.statoSistemazione(v))
  })

  it('origine di una distinta', () => {
    ogniValoreRisolve('origineDistinta', ORIGINI_DISTINTA, (e, v) => e.origineDistinta(v))
  })

  it('le code (una per rotta)', () => {
    ogniValoreRisolve('coda', Object.keys(ROTTA_PER_CODA), (e, v) => e.coda(v))
  })

  // ⭐ P-7 (2026-09-18): i DUE prefissi del motivo — letto come fattura e
  //    letto sulla nota di credito — per entrambi i codici.
  it('motivo fuori capienza, letto come fattura', () => {
    ogniValoreRisolve('motivoFuoriCapienza', MOTIVI_FUORI_CAPIENZA, (e, v) => e.motivoFuoriCapienza(v))
  })

  it('motivo fuori capienza, letto sulla nota di credito', () => {
    ogniValoreRisolve(
      'motivoFuoriCapienza(NC)', MOTIVI_FUORI_CAPIENZA,
      (e, v) => e.motivoFuoriCapienza(v, NATURA_DOC.NOTA_CREDITO),
    )
  })
})

describe('useEtichettePagamenti — la natura cambia la frase, non il codice', () => {
  // ⛔ Se le due chiavi puntassero allo stesso testo, «per natura» sarebbe
  //    una promessa vuota: la sfumatura della nota di credito la dice SOLO
  //    l'etichetta (decisione del DB: il vocabolario resta a due codici).
  it('il motivo sulla nota di credito e\' una frase DIVERSA da quella della fattura', () => {
    for (const l of Object.keys(LOCALES)) {
      lingua = l
      const e = useEtichettePagamenti()
      for (const v of MOTIVI_FUORI_CAPIENZA) {
        expect(e.motivoFuoriCapienza(v, NATURA_DOC.NOTA_CREDITO)).not.toBe(e.motivoFuoriCapienza(v))
      }
    }
  })

  it('la nota di debito si legge come la fattura: non ha una frase sua', () => {
    lingua = 'it'
    const e = useEtichettePagamenti()
    for (const v of MOTIVI_FUORI_CAPIENZA) {
      expect(e.motivoFuoriCapienza(v, NATURA_DOC.NOTA_DEBITO)).toBe(e.motivoFuoriCapienza(v))
    }
  })

  it('il residuo negativo: «da rimborsare» sulla NC, «di troppo» sul resto, mai il numero col meno', () => {
    for (const l of Object.keys(LOCALES)) {
      lingua = l
      const e = useEtichettePagamenti()
      const nc = e.residuoNegativo(-20, NATURA_DOC.NOTA_CREDITO)
      const fatt = e.residuoNegativo(-20)
      expect(nc).not.toBe(fatt)
      // Nessuna delle due e' una chiave non risolta e nessuna porta il meno.
      for (const frase of [nc, fatt]) {
        expect(frase).not.toMatch(/^pagamenti\./)
        expect(frase).not.toMatch(/-\s?20/)
      }
    }
  })
})
