// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa le azioni di riga senza form della collection soggetto/ruolo
//        (`eseguiSuRiga`): la chiamata giusta per il contesto, la lista
//        ricaricata e `onSaved` solo quando la chiamata riesce. La usano
//        l'eliminazione e il «Rendi predefinito» dei contatti
//        (brief-db-revisione-anagrafiche §22.6).
//
// Indice test:
//  1. contesto 'ruolo': chiama apiMap.ruolo[azione](ownerId, id), ricarica, onSaved
//  2. chiamata fallita (execute → null): niente ricarica, niente onSaved
//  3. deleteItem passa dalla stessa sede, col messaggio di eliminazione
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'

const esito = { valore: { data: {} } }
const execute = vi.fn(async (fn, opts) => {
  await fn()
  execute.ultimeOpzioni = opts
  return esito.valore
})
vi.mock('../../core/composables/useApiHandler', () => ({
  useApiHandler: () => ({ execute, loading: { value: false }, campiErrati: { value: [] } }),
}))

// La fotografia del form (useDrawerFormPreserve) vive solo a form aperto e
// porta con se' store e conferma: qui il form resta chiuso, non serve.
vi.mock('../../core/composables/useDrawerFormPreserve', () => ({
  useDrawerFormPreserve: () => ({
    fissa: () => {}, chiudiConConferma: (poi) => poi?.(), modificato: { value: false },
  }),
}))

import { useSoggettoRuoloCollection } from './useSoggettoRuoloCollection'

function crea() {
  const api = {
    list: vi.fn(async () => ({ data: { data: { contatti_ruolo: [], contatti_soggetto: [] } } })),
    predefinito: vi.fn(async () => ({ data: { data: { is_default: true } } })),
    remove: vi.fn(async () => ({ data: { data: { deleted: true } } })),
  }
  const onSaved = vi.fn()
  const coll = useSoggettoRuoloCollection({
    visible: () => false,
    context: () => 'ruolo',
    ownerId: () => 7,
    apiMap: { soggetto: {}, ruolo: api },
    splitKeys: { propri: 'contatti_ruolo', ereditati: 'contatti_soggetto' },
    flatSort: () => 0,
    resetForm: () => {},
    validateForm: () => [],
    populateForm: () => {},
    buildCreatePayload: () => ({}),
    buildUpdatePayload: () => ({}),
    messages: { created: 'c', saved: 's', deleted: 'eliminato' },
    onSaved,
  })
  return { api, onSaved, coll }
}

describe('useSoggettoRuoloCollection — eseguiSuRiga', () => {
  it('1. chiama l\'azione del contesto con owner e id, poi ricarica e onSaved', async () => {
    esito.valore = { data: {} }
    const { api, onSaved, coll } = crea()
    await coll.eseguiSuRiga('predefinito', { id: 42 }, 'cambiato')
    expect(api.predefinito).toHaveBeenCalledWith(7, 42)
    expect(execute.ultimeOpzioni).toEqual({ successMessage: 'cambiato' })
    expect(api.list).toHaveBeenCalledTimes(1)
    expect(onSaved).toHaveBeenCalledTimes(1)
  })

  it('2. chiamata fallita: niente ricarica, niente onSaved', async () => {
    esito.valore = null
    const { api, onSaved, coll } = crea()
    expect(await coll.eseguiSuRiga('predefinito', { id: 42 }, 'cambiato')).toBeNull()
    expect(api.list).not.toHaveBeenCalled()
    expect(onSaved).not.toHaveBeenCalled()
  })

  it('3. deleteItem passa dalla stessa sede col messaggio di eliminazione', async () => {
    esito.valore = { data: {} }
    const { api, coll } = crea()
    await coll.deleteItem({ id: 9 })
    await vi.waitFor(() => expect(api.list).toHaveBeenCalledTimes(1))
    expect(api.remove).toHaveBeenCalledWith(7, 9)
    expect(execute.ultimeOpzioni).toEqual({ successMessage: 'eliminato' })
  })
})
