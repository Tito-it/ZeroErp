// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I gruppi di voci (`children`) della sidebar di dominio: chi li vede
//        e come si raggiungono i figli a sidebar CHIUSA.
//
// ⭐ Il difetto che pinna (rilievo in-app di Tid, 2026-10-06, primo gruppo:
//    Strumenti → Diagnostica): a sidebar chiusa il gruppo era un'icona sola
//    che portava alla prima voce — le altre non si raggiungevano.
// ⚠️ Il posizionamento del popup accanto al rail e' geometria: jsdom non la
//    calcola, resta materia di collaudo a video.
//
// Indice test:
//   1) ⭐ sidebar chiusa: il gruppo apre tutte le sue voci, senza navigare
//   2) sidebar aperta: il gruppo si espande in linea coi figli
//   3) non super admin: il gruppo `adminOnly` non compare
//   4) sidebar chiusa: il gruppo porta il chevron, le voci semplici no
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

import SidebarDomain from './SidebarDomain.vue'
import { useAuthStore } from '../../stores/auth'
import { useNavigationStore } from '../../stores/navigation'
import { NAV_ICONS } from '../navigation'
import { monta } from '../../../test/montaggio'

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/strumenti/email', query: {} }),
  useRouter: () => ({ push }),
}))

const DIARI = ['processi-automatici', 'audit-log', 'error-log', 'email-log']

function montaSidebar({ chiusa, superAdmin }) {
  const auth = useAuthStore()
  auth.user = { is_super_admin: superAdmin }
  useNavigationStore().setDomain('strumenti')
  return monta(SidebarDomain, {}, {
    provide: { sidebarCollapsed: ref(chiusa) },
    global: { stubs: { teleport: true } },
  })
}

// Il gruppo si riconosce dalla sua icona (`NAV_ICONS.DIAGNOSTICA`).
function voceGruppo(wrapper) {
  return wrapper.findAll('.sidebar-item')
    .find(w => w.find('i').attributes('class') === NAV_ICONS.DIAGNOSTICA)
}

describe('SidebarDomain — gruppi di voci', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockClear()
  })

  it('1) ⭐ sidebar chiusa: il gruppo apre tutte le sue voci, senza navigare', async () => {
    const w = montaSidebar({ chiusa: true, superAdmin: true })
    await voceGruppo(w).trigger('click')
    await nextTick()

    expect(push).not.toHaveBeenCalled()
    const menu = w.findComponent({ name: 'Menu' })
    const voci = menu.props('model')[0].items
    expect(voci.map(v => v.key)).toEqual(DIARI)

    voci[2].command()
    expect(push).toHaveBeenCalledWith('/strumenti/diagnostica/error-log')
  })

  it('2) sidebar aperta: il gruppo si espande in linea coi figli', () => {
    const w = montaSidebar({ chiusa: false, superAdmin: true })
    expect(w.findAll('.sidebar-subitem')).toHaveLength(DIARI.length)
  })

  it('3) non super admin: il gruppo `adminOnly` non compare', () => {
    const w = montaSidebar({ chiusa: false, superAdmin: false })
    expect(voceGruppo(w)).toBeUndefined()
    expect(w.findAll('.sidebar-subitem')).toHaveLength(0)
  })

  it('4) sidebar chiusa: il gruppo porta il chevron, le voci semplici no', () => {
    const w = montaSidebar({ chiusa: true, superAdmin: true })
    expect(voceGruppo(w).find('.sidebar-item-gruppo').exists()).toBe(true)
    expect(w.findAll('.sidebar-item-gruppo')).toHaveLength(1)
  })
})
