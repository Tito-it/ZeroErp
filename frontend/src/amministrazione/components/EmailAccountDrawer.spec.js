// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il drawer dell'account dopo il seed di primo impianto
//        (brief-db-seed-primo-impianto-non-si-riscrive §16.16): su un account
//        nato dal seed i campi in `campi_del_software` sono spenti col motivo e
//        non entrano nel PATCH. Oggi il DB manda l'elenco vuoto: il caso si
//        COSTRUISCE qui, perche' i dati di oggi non lo sanno produrre.
// Note: si monta il drawer vero; sono finti lo store (che tiene il dettaglio
//       in `currentAccount`, come quello vero) e il guscio `AppDrawer`.
//
// Indice test:
//   1) account di seed con campi del programma: segno, campo spento, motivo, fuori dal PATCH
//   2) la password segue la COLONNA `smtp_password_encrypted`
//   3) account dell'installazione: nessun segno, niente spento, PATCH intero
//   4) creazione dopo un account di seed: l'elenco di prima non resta
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

const store = {
  currentAccount: null,
  fetchDetail: vi.fn(),
  update: vi.fn(),
  create: vi.fn(),
}

vi.mock('../stores/emailAccounts', () => ({
  useEmailAccountsStore: () => store,
}))
vi.mock('../api/amministrazione', () => ({
  testEmailAccount: vi.fn(),
}))

const { monta } = await import('../../../test/montaggio')
const { default: EmailAccountDrawer } = await import('./EmailAccountDrawer.vue')

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  emits: ['save', 'update:visible'],
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

const BASE = {
  id: 1, codice: 'SISTEMA', descrizione: 'Account di sistema', smtp_host: 'smtp.x.it',
  smtp_port: 587, smtp_use_tls: true, smtp_use_ssl: false, smtp_username: 'u',
  email_from: 'a@x.it', email_reply_to: null, unita_organizzativa_id: null, attivo: true,
}
const DELL_INSTALLAZIONE = { ...BASE, nata_dal_seed: false, campi_del_software: [] }

// Il watch del drawer parte all'APERTURA: si monta chiuso e si apre.
async function apri(dettaglio, props = {}) {
  store.fetchDetail.mockImplementation(async () => { store.currentAccount = dettaglio })
  const w = monta(EmailAccountDrawer, { visible: false, mode: 'edit', accountId: dettaglio?.id, ...props }, {
    global: { stubs: { AppDrawer: AppDrawerFinto } },
  })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

async function salva(w) {
  await w.findComponent(AppDrawerFinto).vm.$emit('save')
  await flushPromises()
}

describe('EmailAccountDrawer — campi del programma su un account di seed', () => {
  beforeEach(() => {
    store.currentAccount = null
    store.fetchDetail.mockReset()
    store.update.mockReset().mockResolvedValue({ ...BASE })
    store.create.mockReset().mockResolvedValue({ ...BASE })
  })

  it('account di seed con campi del programma: segno, campo spento, motivo, fuori dal PATCH', async () => {
    const w = await apri({ ...BASE, nata_dal_seed: true, campi_del_software: ['descrizione', 'unita_organizzativa_id'] })
    expect(w.find('[data-testid="account-di-sistema"]').exists()).toBe(true)
    expect(w.find('[data-testid="motivo-descrizione"]').exists()).toBe(true)
    expect(w.find('[data-testid="account-descrizione"]').attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid="motivo-smtp_host"]').exists()).toBe(false)

    await salva(w)
    const [id, payload] = store.update.mock.calls[0]
    expect(id).toBe(1)
    // ⛔ Ne' il campo a video ne' quello che il form porta senza mostrarlo.
    expect(payload).not.toHaveProperty('descrizione')
    expect(payload).not.toHaveProperty('unita_organizzativa_id')
    expect(payload.smtp_host).toBe('smtp.x.it')
  })

  it('la password segue la COLONNA `smtp_password_encrypted`', async () => {
    const w = await apri({ ...BASE, nata_dal_seed: true, campi_del_software: ['smtp_password_encrypted'] })
    expect(w.find('[data-testid="motivo-smtp_password"]').exists()).toBe(true)
    await salva(w)
    expect(store.update.mock.calls[0][1]).not.toHaveProperty('smtp_password')
  })

  it("account dell'installazione: nessun segno, niente spento, PATCH intero", async () => {
    const w = await apri(DELL_INSTALLAZIONE)
    expect(w.find('[data-testid="account-di-sistema"]').exists()).toBe(false)
    expect(w.find('[data-testid="motivo-descrizione"]').exists()).toBe(false)
    expect(w.find('[data-testid="account-descrizione"]').attributes('disabled')).toBeUndefined()

    await salva(w)
    expect(store.update.mock.calls[0][1].descrizione).toBe('Account di sistema')
  })

  it("creazione dopo un account di seed: l'elenco di prima non resta", async () => {
    // Lo store tiene ancora il dettaglio dell'ultimo account aperto.
    store.currentAccount = { ...BASE, nata_dal_seed: true, campi_del_software: ['descrizione'] }
    const w = monta(EmailAccountDrawer, { visible: false, mode: 'create' }, {
      global: { stubs: { AppDrawer: AppDrawerFinto } },
    })
    await w.setProps({ visible: true })
    await flushPromises()
    expect(w.find('[data-testid="account-di-sistema"]').exists()).toBe(false)
    expect(w.find('[data-testid="motivo-descrizione"]').exists()).toBe(false)
    expect(w.find('[data-testid="account-descrizione"]').attributes('disabled')).toBeUndefined()
  })
})
