// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il contratto di `MatriceOverride` — scritto il 2026-10-31 PRIMA di
//        poggiarlo sulla base `MatriceCatalogo` (B1-bis del brief-db-liste-
//        datatable-grezze-secondo-giro): un refactor su un file senza
//        copertura si fa alla cieca. Fotografa il comportamento che il
//        pannello permessi dell'operatore usa oggi.
//
// Indice test:
//   1) ⭐ tutte le voci, anche quelle senza override (la regola del pattern)
//   2) lo stato dice override o ereditato, dalla PRESENZA della chiave
//   3) l'avviso di riga: stato in giallo e il motivo nel tooltip
//   4) ⭐ «torna all'ereditato» emette la chiave, solo sulle righe con override
//   5) readonly esplicito: niente ripristino
//   6) readonly dalla catena del drawer, e `readonly: false` esplicito la vince
//   7) la ricerca filtra la vista
//   8) nessuna voce: il testo vuoto
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { ref } from 'vue'

import MatriceOverride from './MatriceOverride.vue'
import { READONLY_KEY } from '../composables/useReadonlyMode'
import { monta } from '../../../test/montaggio'

const MESSAGGI = {
  matrice_override: {
    stato_override: 'Override',
    stato_ereditato: 'Ereditato',
  },
  common: { empty_list: 'Nessuna voce' },
}

const VOCI = [
  { id: 1, nome: 'Vendite' },
  { id: 2, nome: 'Acquisti' },
  { id: 3, nome: 'Magazzino' },
]

function matrice(props = {}, opts = {}) {
  return monta(MatriceOverride, {
    voci: VOCI,
    chiave: (v) => v.id,
    overrides: { 2: { livello: 'LETTURA' } },
    labelVoce: 'Area',
    ...props,
  }, {
    messages: MESSAGGI,
    slots: {
      voce: '<template #voce="{ voce }">{{ voce.nome }}</template>',
      ereditato: '<template #ereditato="{ voce }">eredita-{{ voce.id }}</template>',
      override: '<template #override="{ valore, haOverride }">{{ haOverride ? valore.livello : "-" }}</template>',
    },
    ...opts,
  })
}

const righe = (w) => w.findAll('tbody tr')
const pulsantiReset = (w) => w.findAll('tbody button')

describe('MatriceOverride', () => {
  it('1) tutte le voci, anche quelle senza override', () => {
    const w = matrice()
    expect(righe(w)).toHaveLength(3)
    expect(righe(w).map(r => r.findAll('td')[0].text())).toEqual(['Vendite', 'Acquisti', 'Magazzino'])
    expect(righe(w)[0].findAll('td')[1].text()).toBe('eredita-1')
  })

  it('2) lo stato dice override o ereditato, dalla PRESENZA della chiave', () => {
    const w = matrice()
    expect(righe(w)[0].text()).toContain('Ereditato')
    expect(righe(w)[1].findAll('td')[2].text()).toBe('LETTURA')
    expect(righe(w)[1].findAll('td')[3].text()).toContain('Override')
  })

  it('3) l\'avviso di riga: stato in giallo e il motivo nel tooltip', () => {
    const w = matrice({ avviso: (v) => (v.id === 2 ? 'oltre il tetto' : null) })
    const stato = righe(w)[1].findAll('td')[3]
    expect(stato.find('.p-tag-warn').exists()).toBe(true)
    expect(stato.find('.app-matrice-override-avviso').exists()).toBe(true)
    expect(righe(w)[0].find('.app-matrice-override-avviso').exists()).toBe(false)
  })

  it('4) «torna all\'ereditato» emette la chiave, solo sulle righe con override', async () => {
    const w = matrice()
    expect(pulsantiReset(w)).toHaveLength(1)
    await pulsantiReset(w)[0].trigger('click')
    expect(w.emitted('reset')).toEqual([[2]])
  })

  it('5) readonly esplicito: niente ripristino', () => {
    const w = matrice({ readonly: true })
    expect(pulsantiReset(w)).toHaveLength(0)
  })

  it('6) readonly dalla catena del drawer, e `readonly: false` esplicito la vince', () => {
    const ereditato = matrice({}, { provide: { [READONLY_KEY]: ref(true) } })
    expect(pulsantiReset(ereditato)).toHaveLength(0)
    const forzato = matrice({ readonly: false }, { provide: { [READONLY_KEY]: ref(true) } })
    expect(pulsantiReset(forzato)).toHaveLength(1)
  })

  it('7) la ricerca filtra la vista', async () => {
    const w = matrice({ ricerca: true })
    await w.find('input').setValue('magaz')
    expect(righe(w)).toHaveLength(1)
    expect(righe(w)[0].text()).toContain('Magazzino')
  })

  it('8) nessuna voce: il testo vuoto', () => {
    const w = matrice({ voci: [] })
    expect(w.text()).toContain('Nessuna voce')
  })
})
