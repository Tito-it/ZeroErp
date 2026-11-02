// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il cambio di cliente di un documento in bozza si salva subito, con
//        conferma: confermato si scrive il solo cliente e si ricarica;
//        annullato o fallito, il form torna al cliente salvato.
// ------------------------------------------------------------

import { effectScope, nextTick, ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const conferme = []
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (k) => k }) }))
vi.mock('../../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: (opts) => conferme.push(opts) }),
}))
vi.mock('../../../core/utils/ripristinaLookup', () => ({ ripristinaBillingAccount: vi.fn() }))

import { ripristinaBillingAccount } from '../../../core/utils/ripristinaLookup'
import { useCambioClienteDocumento } from './useCambioClienteDocumento'

function monta(opzioni = {}) {
  const form = ref({ billing_account_id: 1, istanza_utility_id: 10, billing_account_obj: { id: 1 } })
  const detail = ref({ billing_account_id: 1, istanza_utility_id: 10 })
  const salva = vi.fn().mockResolvedValue({ ok: true })
  const ricarica = vi.fn().mockResolvedValue()
  const scope = effectScope()
  scope.run(() => useCambioClienteDocumento({
    form, detail, attivo: () => true, salva, ricarica, ...opzioni,
  }))
  return { form, detail, salva, ricarica, scope }
}

async function scegli(form, ba, istanza) {
  form.value.billing_account_id = ba
  form.value.istanza_utility_id = istanza
  await nextTick()
}

describe('useCambioClienteDocumento', () => {
  beforeEach(() => { conferme.length = 0; vi.clearAllMocks() })

  it('confermato: scrive il solo cliente, scarta la scheda, ricarica', async () => {
    const scarta = vi.fn()
    const { form, salva, ricarica } = monta({
      scartaDipendenti: scarta, messaggio: 'vendite.cliente.cambio_messaggio_con_fornitura',
    })
    await scegli(form, 2, 20)
    expect(conferme).toHaveLength(1)
    expect(conferme[0].message).toBe('vendite.cliente.cambio_messaggio_con_fornitura')
    await conferme[0].onAccept()
    expect(salva).toHaveBeenCalledWith({ billing_account_id: 2, istanza_utility_id: 20 })
    expect(scarta).toHaveBeenCalledBefore(ricarica)
    expect(ricarica).toHaveBeenCalled()
  })

  it('annullato: il form torna al cliente salvato, e il lookup si ricostruisce', async () => {
    const { form, salva } = monta()
    await scegli(form, 2, 20)
    conferme[0].onReject()
    conferme[0].onReject() // reject e chiusura: la seconda non fa niente
    expect(form.value.billing_account_id).toBe(1)
    expect(form.value.istanza_utility_id).toBe(10)
    expect(ripristinaBillingAccount).toHaveBeenCalledTimes(1)
    expect(salva).not.toHaveBeenCalled()
  })

  it('salvataggio fallito: torna al cliente salvato, senza ricaricare', async () => {
    const { form, salva, ricarica } = monta()
    salva.mockResolvedValue(null)
    await scegli(form, 2, 20)
    await conferme[0].onAccept()
    expect(form.value.billing_account_id).toBe(1)
    expect(ricarica).not.toHaveBeenCalled()
  })

  it('un cliente tolto e non sostituito non chiede niente', async () => {
    const { form } = monta()
    await scegli(form, null, null)
    expect(conferme).toHaveLength(0)
  })

  it('DDT: tolto il BA, il destinatario rimasto non fa salvare niente', async () => {
    const campi = ['billing_account_id', 'destinatario_soggetto_ruolo_id']
    const { form, detail } = monta({ campi, colonne: campi })
    detail.value = { billing_account_id: 1, destinatario_soggetto_ruolo_id: 50 }
    form.value = { billing_account_id: 1, destinatario_soggetto_ruolo_id: 50 }
    await nextTick()
    form.value.billing_account_id = null
    await nextTick()
    expect(conferme).toHaveLength(0)
    // scelto il sostituto, si chiede
    form.value.billing_account_id = 2
    form.value.destinatario_soggetto_ruolo_id = 60
    await nextTick()
    expect(conferme).toHaveLength(1)
  })

  it('DDT senza BA: cambiare il destinatario si salva', async () => {
    const campi = ['billing_account_id', 'destinatario_soggetto_ruolo_id']
    const { form, detail } = monta({ campi, colonne: campi })
    detail.value = { billing_account_id: null, destinatario_soggetto_ruolo_id: 50 }
    form.value = { billing_account_id: null, destinatario_soggetto_ruolo_id: 50 }
    await nextTick()
    form.value.destinatario_soggetto_ruolo_id = 51
    await nextTick()
    expect(conferme).toHaveLength(1)
  })

  it('documento non modificabile: niente conferma', async () => {
    const { form } = monta({ attivo: () => false })
    await scegli(form, 2, 20)
    expect(conferme).toHaveLength(0)
  })

  it('un secondo cambio a dialog aperto non ne apre un altro; si scrive l\'ultimo', async () => {
    const { form, salva } = monta()
    await scegli(form, 2, 20)
    await scegli(form, 3, 30)
    expect(conferme).toHaveLength(1)
    await conferme[0].onAccept()
    expect(salva).toHaveBeenCalledWith({ billing_account_id: 3, istanza_utility_id: 30 })
  })

  it('senza messaggio esplicito il testo e\' quello degli indirizzi, anche con scartaDipendenti', async () => {
    const { form } = monta({ scartaDipendenti: vi.fn() })
    await scegli(form, 2, 20)
    expect(conferme[0].message).toBe('vendite.cliente.cambio_messaggio')
  })

  it('una ricarica che fallisce non lascia il BB bloccato', async () => {
    const { form, ricarica } = monta()
    ricarica.mockRejectedValueOnce(new Error('rete'))
    await scegli(form, 2, 20)
    await expect(conferme[0].onAccept()).rejects.toThrow('rete')
    await scegli(form, 3, 30)
    expect(conferme).toHaveLength(2)
  })

  it('il payload del drawer vince sul default (DDT col destinatario)', async () => {
    const { form, salva } = monta({ payload: () => ({ billing_account_id: null, destinatario_soggetto_ruolo_id: 5 }) })
    await scegli(form, 2, 20)
    await conferme[0].onAccept()
    expect(salva).toHaveBeenCalledWith({ billing_account_id: null, destinatario_soggetto_ruolo_id: 5 })
  })
})
