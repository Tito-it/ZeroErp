// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio del numero sulle azioni (`ActionBadge` + `haBadge` /
//        `etichettaConBadge` di useActionBar): lo zero e il vuoto non si dicono;
//        e la barra delle liste lo MOSTRA — il caso che l'ha fatto nascere:
//        «Personalizza colonne» con le colonne nuove, il cui numero stava
//        nell'etichetta di un pulsante a sola icona e non si vedeva.
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import ActionBadge from './ActionBadge.vue'
import PageActionsBar from './PageActionsBar.vue'
import { etichettaConBadge, haBadge } from '../composables/useActionBar'
import { monta } from '../../../test/montaggio'

describe('ActionBadge', () => {
  it('haBadge: lo zero non si mostra, come null/undefined/vuoto', () => {
    expect(haBadge({ badge: 0 })).toBe(false)
    expect(haBadge({ badge: '0' })).toBe(false)
    expect(haBadge({ badge: 8 })).toBe(true)
    expect(haBadge({ badge: null })).toBe(false)
    expect(haBadge({ badge: '' })).toBe(false)
    expect(haBadge({})).toBe(false)
  })

  it('etichettaConBadge: il numero nella voce di menu', () => {
    expect(etichettaConBadge({ label: 'Personalizza colonne', badge: 8 })).toBe('Personalizza colonne (8)')
    expect(etichettaConBadge({ label: 'Ricarica' })).toBe('Ricarica')
    expect(etichettaConBadge({ label: 'Gestisci righe', badge: 0 })).toBe('Gestisci righe')
  })

  it('il pallino porta il numero; il punto no; vuoto non c\'e\'', () => {
    expect(monta(ActionBadge, { valore: 8 }).find('.app-action-badge').text()).toBe('8')
    const punto = monta(ActionBadge, { valore: 1, punto: true }).find('.app-action-badge--punto')
    expect(punto.exists()).toBe(true)
    expect(punto.text()).toBe('')
    expect(monta(ActionBadge, { valore: null }).find('.app-action-badge').exists()).toBe(false)
    expect(monta(ActionBadge, { valore: 0 }).find('.app-action-badge').exists()).toBe(false)
  })

  it('la barra delle liste mostra il numero sull\'icona dell\'azione', () => {
    const w = monta(PageActionsBar, {
      actions: [
        { key: 'personalizza-colonne', kind: 'utility', label: 'Personalizza', icon: 'pi pi-cog', badge: 8, command: () => {} },
        { key: 'reload', kind: 'utility', label: 'Ricarica', icon: 'pi pi-refresh', command: () => {} },
      ],
    })
    const numeri = w.findAll('.app-page-actions-desktop .app-action-badge:not(.app-action-badge--punto)')
    expect(numeri.map((n) => n.text())).toEqual(['8'])
  })
})
