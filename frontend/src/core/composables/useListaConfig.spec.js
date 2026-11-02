// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il salvataggio della preferenza di lista PER CHIAVE (2026-11-01).
//        Prima si salvava la configurazione risolta intera: chi personalizzava
//        le colonne congelava anche misura di pagina, ordine e filtri del preset.
//
// Indice test:
//   1. toccate le sole colonne: il PUT porta solo le colonne
//   2. le chiavi gia' della preferenza si rimandano, con quella toccata
//   3. ⭐ nessuna chiave scelta: DELETE, non un PUT vuoto
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
  getListaConfig: vi.fn(),
  getListaCatalogo: vi.fn(),
  putListaPreferenza: vi.fn(),
  deleteListaPreferenza: vi.fn(),
  ignorePresetUpdate: vi.fn(),
}))
vi.mock('../api/ui-api', () => api)

const { useListaConfig } = await import('./useListaConfig')

function configDalServer(origine = {}) {
  return {
    colonne: [{ codice: 'codice', ordine: 1, visibile: true, etichetta: 'Codice' }],
    ordinamento: [{ col: 'codice', dir: 'asc' }],
    filtri: {},
    pagina_dimensione: 10,
    pagina_dimensione_standard: 10,
    colonne_nuove: 0,
    origine: {
      colonne: 'sistema', ordinamento: 'sistema', filtri: 'sistema', pagina_dimensione: 'sistema',
      ...origine,
    },
  }
}

async function caricata(origine) {
  api.getListaConfig.mockResolvedValue(configDalServer(origine))
  api.getListaCatalogo.mockResolvedValue({ colonne: [] })
  const lista = useListaConfig('vendite.listini')
  await lista.load()
  return lista
}

describe('useListaConfig.save — per chiave', () => {
  beforeEach(() => vi.clearAllMocks())

  it('1. toccate le sole colonne: il PUT porta solo le colonne', async () => {
    const lista = await caricata()
    lista.applyChange((c) => { c.colonne[0].visibile = false })
    await lista.save()
    expect(api.putListaPreferenza).toHaveBeenCalledWith('vendite.listini', {
      colonne: [{ codice: 'codice', ordine: 1, visibile: false }],
    })
  })

  it('2. le chiavi della preferenza si rimandano, con quella toccata', async () => {
    const lista = await caricata({ colonne: 'preferenza' })
    lista.applyChange((c) => { c.pagina_dimensione = 50 })
    await lista.save()
    expect(api.putListaPreferenza).toHaveBeenCalledWith('vendite.listini', {
      colonne: [{ codice: 'codice', ordine: 1, visibile: true }],
      pagina_dimensione: 50,
    })
  })

  it('3. nessuna chiave scelta: DELETE, non un PUT vuoto', async () => {
    const lista = await caricata({ pagina_dimensione: 'preferenza' })
    lista.applyChange((c) => { c.pagina_dimensione = null })
    await lista.save()
    expect(api.putListaPreferenza).not.toHaveBeenCalled()
    expect(api.deleteListaPreferenza).toHaveBeenCalledWith('vendite.listini')
  })
})
