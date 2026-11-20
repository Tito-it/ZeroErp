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
