// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il BB che ricostruisce l'oggetto del lookup (cliente, fornitura) da
//        un id: scrive solo se il form punta ancora a quell'id, e non fallisce.
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../apiCore', () => ({
  getBillingAccountLookupById: vi.fn(),
  getIstanzaUtilityLookupById: vi.fn(),
}))

import { getBillingAccountLookupById, getIstanzaUtilityLookupById } from '../apiCore'
import { ripristinaBillingAccount, ripristinaIstanzaUtility } from './ripristinaLookup'

const BA = { id: 7, codice: 'BA-7', ragione_sociale_completa: 'Rossi Srl' }

describe('ripristinaBillingAccount', () => {
  beforeEach(() => vi.clearAllMocks())

  it('mette nel form l\'oggetto letto dal server, ragione sociale compresa', async () => {
    getBillingAccountLookupById.mockResolvedValue({ data: { data: BA } })
    const form = { billing_account_id: 7, billing_account_obj: null }
    await ripristinaBillingAccount(form, 7)
    expect(getBillingAccountLookupById).toHaveBeenCalledWith(7)
    expect(form.billing_account_obj).toEqual(BA)
  })

  it('una risposta lenta non sovrascrive un cliente scelto nel frattempo', async () => {
    let rispondi
    getBillingAccountLookupById.mockReturnValue(new Promise((r) => { rispondi = r }))
    const scelto = { id: 9, ragione_sociale_completa: 'Bianchi Spa' }
    const form = { billing_account_id: 7, billing_account_obj: null }
    const corsa = ripristinaBillingAccount(form, 7)
    form.billing_account_id = 9
    form.billing_account_obj = scelto
    rispondi({ data: { data: BA } })
    await corsa
    expect(form.billing_account_obj).toBe(scelto)
  })

  it('senza id non chiama il server', async () => {
    const form = { billing_account_id: null, billing_account_obj: null }
    await ripristinaBillingAccount(form, null)
    expect(getBillingAccountLookupById).not.toHaveBeenCalled()
    expect(form.billing_account_obj).toBeNull()
  })

  it('un errore della lettura non sale: il campo resta col solo id', async () => {
    getBillingAccountLookupById.mockRejectedValue(new Error('rete'))
    const form = { billing_account_id: 7, billing_account_obj: null }
    await expect(ripristinaBillingAccount(form, 7)).resolves.toBeUndefined()
    expect(form.billing_account_obj).toBeNull()
  })
})

describe('ripristinaIstanzaUtility', () => {
  beforeEach(() => vi.clearAllMocks())

  it('ricostruisce la fornitura del form', async () => {
    const iu = { id: 3, codice: 'IU-3' }
    getIstanzaUtilityLookupById.mockResolvedValue({ data: { data: iu } })
    const form = { istanza_utility_id: 3, istanza_utility_obj: null }
    await ripristinaIstanzaUtility(form, 3)
    expect(form.istanza_utility_obj).toEqual(iu)
  })
})
