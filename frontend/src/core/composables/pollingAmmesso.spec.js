// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il pallino dei presidi e il badge delle code chiamano il loro
//        endpoint SOLO per chi ne passa la porta (`ammesso`, detto dalla
//        topbar prima della chiamata). Fino al 2026-10-02 provavano per
//        chiunque e si spegnevano al 403: ogni operatore non amministratore
//        lasciava a ogni accesso un falso «accesso negato» nel log di
//        sicurezza.
// Note: la porta la giudica `useRefreshPeriodico` (opzione `ammesso`): qui la
//       si prova attraverso i due consumatori. Le API sono finte; il timer e'
//       quello vero di `useRefreshPeriodico`, montato in un componente vuoto.
//
// Indice test:
//   1) non ammesso: nessuna chiamata, `disponibile` falso (per entrambi)
//   2) ammesso: la chiamata parte al montaggio (per entrambi)
//   3) ammesso dopo il montaggio (il profilo arriva dopo): la chiamata parte
//   4) la porta che si richiude (logout, cambio veste) ferma; riaperta riparte
//   5) un 403 spegne comunque: la rete per un permesso tolto a sessione aperta
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'

const getPresidiConteggi = vi.fn()
const getCodeConteggi = vi.fn()

vi.mock('../api/presidi', () => ({ getPresidiConteggi: (...a) => getPresidiConteggi(...a) }))
vi.mock('../api/tracciamento', () => ({ getCodeConteggi: (...a) => getCodeConteggi(...a) }))

const { usePresidiPolling } = await import('./usePresidiPolling')
const { useQueueCountsPolling } = await import('./useQueueCountsPolling')

// Scopo: monta il composable in un componente vuoto e ne restituisce il risultato.
function monta(useComposable, ammesso) {
  let esito
  const wrapper = mount(defineComponent({
    setup() {
      esito = useComposable({ ammesso })
      return () => h('div')
    },
  }))
  return { esito, wrapper }
}

const CASI = [
  ['pallino dei presidi', usePresidiPolling, getPresidiConteggi],
  ['badge delle code', useQueueCountsPolling, getCodeConteggi],
]

describe.each(CASI)('%s — chiamato solo per chi passa la porta', (_nome, useComposable, api) => {
  beforeEach(() => {
    getPresidiConteggi.mockReset().mockResolvedValue({ data: { data: {} } })
    getCodeConteggi.mockReset().mockResolvedValue({ data: { data: {} } })
  })

  it('non ammesso: nessuna chiamata', async () => {
    const { esito, wrapper } = monta(useComposable, () => false)
    await flushPromises()
    expect(api).not.toHaveBeenCalled()
    expect(esito.disponibile.value).toBe(false)
    wrapper.unmount()
  })

  it('ammesso: la chiamata parte al montaggio', async () => {
    const { esito, wrapper } = monta(useComposable, () => true)
    await flushPromises()
    expect(api).toHaveBeenCalledTimes(1)
    expect(esito.disponibile.value).toBe(true)
    wrapper.unmount()
  })

  it('ammesso dopo il montaggio: la chiamata parte allora', async () => {
    const ammesso = ref(false)
    const { wrapper } = monta(useComposable, () => ammesso.value)
    await flushPromises()
    expect(api).not.toHaveBeenCalled()
    ammesso.value = true
    await flushPromises()
    expect(api).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('la porta che si richiude ferma, e riaperta riparte', async () => {
    const ammesso = ref(true)
    const { esito, wrapper } = monta(useComposable, () => ammesso.value)
    await flushPromises()
    expect(api).toHaveBeenCalledTimes(1)
    ammesso.value = false
    await flushPromises()
    expect(esito.disponibile.value).toBe(false)
    esito.refresh()
    await flushPromises()
    expect(api).toHaveBeenCalledTimes(1)
    ammesso.value = true
    await flushPromises()
    expect(api).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })

  it('un 403 spegne comunque', async () => {
    api.mockRejectedValue({ response: { status: 403 } })
    const { esito, wrapper } = monta(useComposable, () => true)
    await flushPromises()
    expect(esito.disponibile.value).toBe(false)
    wrapper.unmount()
  })
})
