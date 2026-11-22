// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `useDashboardConfig`, le due parti gemelle delle liste del giro 1a
//        di brief-db-revisione-ui (BE7): la base del preset cambiata e il
//        suo «Riallinea».
// Note: API e `useApiHandler` finti, come in `useListaConfig.spec.js`.
//
// Indice test:
//   1. `preset_base_cambiato` dal DB, passthrough (assente = falso)
//   2. «Riallinea» rimanda le chiavi della preferenza, senza toccarle
//   3. «Riallinea» senza chiavi scelte: DELETE, non un PUT vuoto
//   4. giro 1b: `preset_aggiornato_chiavi` dal DB, passthrough (assente =
//      elenco vuoto)
//   5. BE8 (giro 2): una chiave a null della card non si manda
//   6-7. FE1 (giro 3): il tetto delle card e' quello del DB, senza ripiego
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('./useApiHandler', () => ({
  useApiHandler: () => ({
    execute: async (chiamata) => {
      try {
        return (await chiamata()) ?? {}
      } catch {
        return null
      }
    },
    loading: { value: false },
  }),
}))

const api = vi.hoisted(() => ({
  getDashboardConfig: vi.fn(),
  getDashboardContatori: vi.fn(),
  putDashboardPreferenza: vi.fn(),
  deleteDashboardPreferenza: vi.fn(),
  ignoreDashboardPresetUpdate: vi.fn(),
}))
vi.mock('../api/ui-api', () => api)

const { useDashboardConfig } = await import('./useDashboardConfig')

function configDalServer(origine = {}, extra = {}) {
  return {
    widget: [{ codice: 'situazione', ordine: 1, visibile: true, etichetta: 'Situazione' }],
    dimensione_max: 8,
    widget_nuovi: 0,
    origine: { widget: 'sistema', dimensione_max: 'sistema', ...origine },
    ...extra,
  }
}

async function caricata(origine, extra) {
  api.getDashboardConfig.mockResolvedValue(configDalServer(origine, extra))
  api.getDashboardContatori.mockResolvedValue({ contatori: {} })
  const dash = useDashboardConfig('home')
  await dash.load()
  return dash
}

describe('useDashboardConfig — base del preset cambiata (BE7, giro 1a)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('1. `preset_base_cambiato` dal DB, passthrough (assente = falso)', async () => {
    expect((await caricata()).presetBaseCambiato.value).toBe(false)
    const dash = await caricata({ widget: 'preferenza' }, { preset_base_cambiato: true })
    expect(dash.presetBaseCambiato.value).toBe(true)
  })

  it('4. `preset_aggiornato_chiavi` dal DB, passthrough (assente = vuoto)', async () => {
    expect((await caricata()).presetAggiornatoChiavi.value).toEqual([])
    const dash = await caricata(
      { widget: 'preferenza' },
      { preset_aggiornato: true, preset_aggiornato_chiavi: ['widget'] },
    )
    expect(dash.presetAggiornatoChiavi.value).toEqual(['widget'])
  })

  it('2. «Riallinea» rimanda le chiavi della preferenza, senza toccarle', async () => {
    const dash = await caricata({ widget: 'preferenza' }, { preset_base_cambiato: true })
    await dash.riallineaPresetBase()
    // Il BE ci scrive la base di oggi: il FE non manda nessun id di preset.
    expect(api.putDashboardPreferenza).toHaveBeenCalledWith('home', {
      widget: [{ codice: 'situazione', ordine: 1, visibile: true }],
    })
  })

  it('3. «Riallinea» senza chiavi scelte: DELETE, non un PUT vuoto', async () => {
    const dash = await caricata({}, { preset_base_cambiato: true })
    await dash.riallineaPresetBase()
    expect(api.putDashboardPreferenza).not.toHaveBeenCalled()
    expect(api.deleteDashboardPreferenza).toHaveBeenCalledWith('home')
  })
})

describe('useDashboardConfig.save — voci senza chiavi a null (BE8, giro 2)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('5. una chiave a null della card non si manda', async () => {
    const dash = await caricata({ widget: 'preferenza' })
    dash.config.value.widget[0].visibile = null
    await dash.save()
    // Il guard di forma del DB rifiuta una voce con una chiave a null
    // (`E_UI_CONFIGURAZIONE_FORMA`): il FE la toglie (Tid, 2026-11-22).
    expect(api.putDashboardPreferenza).toHaveBeenCalledWith('home', {
      widget: [{ codice: 'situazione', ordine: 1 }],
    })
  })
})

describe('useDashboardConfig — il tetto delle card dal DB (FE1, giro 3)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('6. il tetto e\' quello della configurazione: nessun 8 di ripiego', async () => {
    const widget = [1, 2, 3].map((i) => ({ codice: `w${i}`, ordine: i, visibile: true }))
    const dash = await caricata({}, { widget, dimensione_max: 2 })
    expect(dash.dimensioneMax.value).toBe(2)
    expect(dash.widgetVisibili.value.map((w) => w.codice)).toEqual(['w1', 'w2'])
  })

  it('7. prima della configurazione: nessun tetto inventato', () => {
    const dash = useDashboardConfig('home')
    expect(dash.dimensioneMax.value).toBeNull()
    expect(dash.widgetVisibili.value).toEqual([])
  })
})
