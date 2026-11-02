// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio di `useTabDaQuery`: il deep-link `?tab=` sotto KeepAlive, e
//        `ripartiDaIniziale`, per cui chi rientra senza query trova la
//        scheda iniziale invece di quella dell'ultima visita.
// ------------------------------------------------------------

/*
Indice test eseguiti:
1) senza opzione: al rientro resta la scheda scelta a mano
2) ripartiDaIniziale: al rientro si torna alla scheda iniziale
3) ripartiDaIniziale: il deep-link `?tab=` vince sull'iniziale. ⚠️ Sotto
   KeepAlive lo applica il watch PRIMA della riattivazione, e la query e' gia'
   pulita quando arriva `onActivated`: azzerare all'ingresso lo annullava
*/

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent, h, KeepAlive, nextTick, reactive, ref } from 'vue'
import { mount } from '@vue/test-utils'

const route = reactive({ name: 'vista', query: {} })
const router = { replace: vi.fn(({ query }) => { route.query = query }) }

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => router,
}))

const { useTabDaQuery } = await import('./useTabDaQuery')

const SCHEDE = Object.freeze({ A: 'a', B: 'b' })
// ⚠️ Ogni vista montata si smonta a fine test: viva, il suo watch sulla rotta
//    finta (condivisa) consumerebbe il `?tab=` del test dopo.
const montati = []

// Scopo: monta la vista dentro KeepAlive, con un interruttore che la porta
//        fuori e dentro come una navigazione (deactivated / activated).
function montaInCache(opzioni) {
  let attivo
  const Vista = defineComponent({
    name: 'VistaTab',
    setup() {
      attivo = useTabDaQuery({ nomeRotta: 'vista', ammessi: SCHEDE, iniziale: SCHEDE.A, ...opzioni })
      return () => h('div')
    },
  })
  const visibile = ref(true)
  montati.push(mount(defineComponent({
    setup: () => () => h(KeepAlive, null, [visibile.value ? h(Vista) : h('span')]),
  })))
  return {
    attivo: () => attivo,
    async esci() { visibile.value = false; await nextTick() },
    async entra() { visibile.value = true; await nextTick() },
  }
}

describe('useTabDaQuery', () => {
  beforeEach(() => {
    route.query = {}
    router.replace.mockClear()
  })

  afterEach(() => {
    montati.splice(0).forEach((w) => w.unmount())
  })

  it('1) senza opzione: al rientro resta la scheda scelta a mano', async () => {
    const v = montaInCache()
    v.attivo().value = SCHEDE.B
    await v.esci()
    await v.entra()
    expect(v.attivo().value).toBe(SCHEDE.B)
  })

  it('2) ripartiDaIniziale: al rientro si torna alla scheda iniziale', async () => {
    const v = montaInCache({ ripartiDaIniziale: true })
    v.attivo().value = SCHEDE.B
    await v.esci()
    await v.entra()
    expect(v.attivo().value).toBe(SCHEDE.A)
  })

  it('3) ripartiDaIniziale: il deep-link vince, e la pulizia della query non lo annulla', async () => {
    const v = montaInCache({ ripartiDaIniziale: true })
    await v.esci()
    route.query = { tab: SCHEDE.B }
    await v.entra()
    await nextTick()
    expect(router.replace).toHaveBeenCalled()
    expect(route.query.tab).toBeUndefined()
    expect(v.attivo().value).toBe(SCHEDE.B)
  })
})
