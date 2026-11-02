// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il SECONDO TEMPO PER RIGA di `useRigheDaRate` (D19-d,
//        2026-09-17): su un esito PARZIALE le riuscite escono dall'area, le
//        fallite restano col loro errore intero, la forzatura si conferma per
//        riga e il Salva successivo rimanda le SOLE rimaste con `forzata` dove
//        confermato. E' la parte che a video non fallisce mai rumorosamente:
//        una riga riuscita che resta in area verrebbe mandata DUE volte.
// Note: ⛔ I collaboratori sono mockati: `useApiHandler` (l'envelope e' provato
//        nel suo spec), `useNotify`, `useI18n`. I due BB di core che compone
//        (`useSelezioneLista`, `useSelezioneConValore`) NON sono mockati: e'
//        la composizione che si prova.
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { computed, nextTick, ref } from 'vue'

const notifiche = { success: vi.fn(), warn: vi.fn(), info: vi.fn(), error: vi.fn() }
const creaRigheDaRate = vi.fn()
// `execute` di `useApiHandler`: consegna il `data` interno, `null` su errore.
let rispostaProssima = null

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (chiave) => chiave }) }))
vi.mock('../../core/composables/useNotify', () => ({ useNotify: () => notifiche }))
vi.mock('../../core/composables/useApiHandler', () => ({
  useApiHandler: () => ({
    loading: ref(false),
    execute: async (fn) => { await fn(); return rispostaProssima },
  }),
}))
vi.mock('../api/pagamenti', () => ({ creaRigheDaRate: (...a) => creaRigheDaRate(...a) }))

const { useRigheDaRate } = await import('./useRigheDaRate')
const { CONFERMA_E_RIPETI } = await import('../../core/composables/useForzaturaConfermata')

const rata = (id, residuo, in_lavorazione = 0) => ({ scadenza_id: id, residuo, in_lavorazione })

function fabbrica(righe) {
  const righeVisibili = ref(righe)
  const m = useRigheDaRate({
    contabileId: () => 7,
    righeVisibili,
    abilitata: computed(() => true),
  })
  return { m, righeVisibili }
}

beforeEach(() => {
  Object.values(notifiche).forEach((f) => f.mockClear())
  creaRigheDaRate.mockClear()
  rispostaProssima = null
})

describe('useRigheDaRate — la selezione e la proposta', () => {
  it('⭐ selezionabile = spazio ≠ 0: la nota di credito (spazio negativo) SI sceglie, la rata esaurita no', () => {
    const { m } = fabbrica([rata(1, 100), rata(2, -20), rata(3, 100, 100)])
    const p = m.perLista.value
    expect(p.isSelezionabile(rata(1, 100))).toBe(true)
    expect(p.isSelezionabile(rata(2, -20))).toBe(true)
    expect(p.isSelezionabile(rata(3, 100, 100))).toBe(false)
    expect(p.motivoNonSelezionabile(rata(3, 100, 100))).toBe('pagamenti.rate.esaurita')
  })

  it('spuntare una rata semina il suo importo con lo spazio; l\'override resta; togliere azzera', async () => {
    const { m } = fabbrica([rata(1, 100, 30), rata(2, -20)])
    m.perLista.value.toggle(rata(1, 100, 30))
    await nextTick()
    expect(m.importoDi(1)).toBe(70)
    m.impostaImporto(1, 50)
    m.perLista.value.toggle(rata(2, -20))
    await nextTick()
    expect(m.importoDi(1)).toBe(50)
    expect(m.importoDi(2)).toBe(-20)
    m.rimuovi(rata(1, 100, 30))
    await nextTick()
    expect(m.importoDi(1)).toBeNull()
    expect(m.selezione.value.map((r) => r.scadenza_id)).toEqual([2])
  })

  it('il Salva resta spento senza rate, o con un importo svuotato', async () => {
    const { m } = fabbrica([rata(1, 100)])
    expect(m.canSave.value).toBe(false)
    m.perLista.value.toggle(rata(1, 100))
    await nextTick()
    expect(m.canSave.value).toBe(true)
    m.impostaImporto(1, null)
    expect(m.canSave.value).toBe(false)
  })
})

describe('useRigheDaRate — il secondo tempo per riga', () => {
  async function conDueRate() {
    const { m } = fabbrica([rata(1, 300), rata(2, 50)])
    m.perLista.value.toggle(rata(1, 300))
    m.perLista.value.toggle(rata(2, 50))
    await nextTick()
    m.fatti.value.data_pagamento = new Date(2026, 8, 17)
    m.fatti.value.riferimento_ente = '  RIF-1  '
    return m
  }

  it('il payload porta i fatti comuni e una riga per rata, senza forzatura al primo giro', async () => {
    const m = await conDueRate()
    rispostaProssima = { esito: 'COMPLETATO', richieste: 2, riuscite: 2, creati: [], falliti: [] }
    await m.salva()
    expect(creaRigheDaRate).toHaveBeenCalledWith(7, {
      data_pagamento: '2026-09-17',
      data_valuta: null,
      riferimento_ente: 'RIF-1',
      righe: [
        { scadenza_id: 1, importo: 300 },
        { scadenza_id: 2, importo: 50 },
      ],
    })
    expect(m.selezione.value).toEqual([])
    expect(notifiche.success).toHaveBeenCalledWith('pagamenti.rate.create')
  })

  it('🔴 PARZIALE: la riuscita esce, la fallita resta col suo errore, e il giro dopo rimanda SOLO lei con `forzata`', async () => {
    const m = await conDueRate()
    const errore = { code: 'E_CAPIENZA', message: 'pagato due volte', ui_action: CONFERMA_E_RIPETI }
    rispostaProssima = {
      esito: 'PARZIALE', richieste: 2, riuscite: 1, creati: [{ id: 99 }],
      falliti: [{ indice: 1, scadenza_id: 2, errore }],
    }
    await m.salva()
    expect(m.selezione.value.map((r) => r.scadenza_id)).toEqual([2])
    expect(m.errore(2)).toEqual(errore)
    expect(m.errore(1)).toBeNull()
    expect(m.confermabile(2)).toBe(true)
    expect(notifiche.warn).toHaveBeenCalledWith('pagamenti.rate.parziale')

    // Il motivo si scrive PRIMA o DOPO la conferma, e sopravvive a un
    // «Forza» spento e riacceso: e' un testo, non un flag.
    m.impostaMotivo(2, '  anticipo concordato ')
    m.forza(2)
    m.annullaForzatura(2)
    expect(m.motivoDi(2)).toBe('  anticipo concordato ')
    m.forza(2)
    expect(m.forzata(2)).toBe(true)
    rispostaProssima = { esito: 'COMPLETATO', richieste: 1, riuscite: 1, creati: [{ id: 100 }], falliti: [] }
    await m.salva()
    const secondo = creaRigheDaRate.mock.calls[1][1]
    expect(secondo.righe).toEqual([
      { scadenza_id: 2, importo: 50, forzata: true, motivo_forzatura: 'anticipo concordato' },
    ])
    expect(m.selezione.value).toEqual([])
    expect(m.forzata(2)).toBe(false)
    expect(m.motivoDi(2)).toBe('')
    expect(m.errore(2)).toBeNull()
  })

  it('un errore NON confermabile resta senza secondo tempo, e la forzatura si puo\' ritirare', async () => {
    const m = await conDueRate()
    rispostaProssima = {
      esito: 'PARZIALE', richieste: 2, riuscite: 1, creati: [],
      falliti: [{ indice: 0, scadenza_id: 1, errore: { code: 'E_X', message: 'no' } }],
    }
    await m.salva()
    expect(m.confermabile(1)).toBe(false)
    m.forza(1)
    expect(m.forzata(1)).toBe(true)
    m.annullaForzatura(1)
    expect(m.forzata(1)).toBe(false)
    // Forzata SENZA motivo: la riga viaggia con `forzata` e senza la chiave.
    m.forza(1)
    rispostaProssima = { esito: 'COMPLETATO', richieste: 1, riuscite: 1, creati: [], falliti: [] }
    await m.salva()
    expect(creaRigheDaRate.mock.calls[1][1].righe).toEqual([{ scadenza_id: 1, importo: 300, forzata: true }])
  })

  it('chiamata fallita (`execute` → null): l\'area resta com\'era, nessun toast di esito', async () => {
    const m = await conDueRate()
    rispostaProssima = null
    expect(await m.salva()).toBeNull()
    expect(m.selezione.value.map((r) => r.scadenza_id)).toEqual([1, 2])
    expect(notifiche.success).not.toHaveBeenCalled()
    expect(notifiche.warn).not.toHaveBeenCalled()
  })

  it('`azzera` riporta tutto allo stato di partenza, fatti comuni compresi', async () => {
    const m = await conDueRate()
    m.forza(1)
    m.impostaMotivo(1, 'x')
    m.azzera()
    expect(m.selezione.value).toEqual([])
    expect(m.importoDi(1)).toBeNull()
    expect(m.forzata(1)).toBe(false)
    expect(m.motivoDi(1)).toBe('')
    expect(m.fatti.value.riferimento_ente).toBe('')
  })
})
