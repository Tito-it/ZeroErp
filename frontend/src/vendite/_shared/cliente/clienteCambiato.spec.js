// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il confronto del cliente del form con quello salvato.
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'
import { clienteCambiato } from './clienteCambiato'

describe('clienteCambiato', () => {
  it('stesso BA: non cambiato, anche se uno e\' numero e l\'altro stringa', () => {
    expect(clienteCambiato({ billing_account_id: 7 }, { billing_account_id: 7 })).toBe(false)
    expect(clienteCambiato({ billing_account_id: 7 }, { billing_account_id: '7' })).toBe(false)
    expect(clienteCambiato({ billing_account_id: ' 7 ' }, { billing_account_id: 7 })).toBe(false)
  })

  it('BA diverso: cambiato', () => {
    expect(clienteCambiato({ billing_account_id: 9 }, { billing_account_id: 7 })).toBe(true)
  })

  it('senza dettaglio (creazione) non c\'e\' niente da cui differire', () => {
    expect(clienteCambiato({ billing_account_id: 9 }, null)).toBe(false)
  })

  it('vuoto e null sono la stessa cosa', () => {
    expect(clienteCambiato({ billing_account_id: '' }, { billing_account_id: null })).toBe(false)
  })

  it('il DDT guarda anche il destinatario senza BA', () => {
    const campi = ['billing_account_id', 'destinatario_soggetto_ruolo_id']
    expect(clienteCambiato(
      { billing_account_id: null, destinatario_soggetto_ruolo_id: 5 },
      { billing_account_id: null, destinatario_soggetto_ruolo_id: 4 },
      campi,
    )).toBe(true)
  })
})
