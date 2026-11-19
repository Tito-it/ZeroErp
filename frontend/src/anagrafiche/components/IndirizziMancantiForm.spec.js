// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `IndirizziMancantiForm` — gli indirizzi compilati per il cambio di
//        natura sopravvivono alla rilettura dei motivi. Il `SoggettoDrawer`
//        rilegge i mancanti a ogni P.IVA o flag digitato e dopo un salvataggio
//        rifiutato: ogni lettura e' un array nuovo con gli stessi tipi. Fino al
//        2026-11-18 il form seguiva l'array, e `setMatrice` svuotava cio' che
//        l'operatore aveva scritto.
// Note: si monta il componente vero; finti solo i contorni — le API e il form
//       dell'indirizzo, da cui si legge il `form` condiviso per compilarlo.
//
// Indice test:
//   1) stessi tipi in un array nuovo: i due indirizzi compilati restano
//   2) tipi diversi: la matrice si rifà sui tipi nuovi
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'

vi.mock('../api/anagrafiche', () => ({
  lookupStati: vi.fn(async () => ({ data: { data: { results: [] } } })),
  lookupCodiciPostaliByComune: vi.fn(async () => ({ data: { data: { results: [] } } })),
  checkIndirizzoDuplicato: vi.fn(async () => ({ data: { data: {} } })),
}))
vi.mock('../../core/apiCore', () => ({
  lookupTipiIndirizzoNatura: vi.fn(),
  lookupTipiIndirizzoTipoRuolo: vi.fn(),
}))

const { monta } = await import('../../../test/montaggio')
const { default: IndirizziMancantiForm } = await import('./IndirizziMancantiForm.vue')

const FormFinto = defineComponent({
  name: 'IndirizzoSoggettoForm',
  props: { form: { type: Object, default: null } },
  emits: ['switch-tipo'],
  render: () => null,
})

// Il fornitore vuole la consegna, o in ripiego il domicilio fiscale.
const mancanti = () => [{
  soggetto_ruolo_id: 7, tipo_ruolo_id: 2, ruolo_descrizione: 'Fornitore',
  tipo_indirizzo_id: 4, tipo_indirizzo_codice_interno: 'SPED', tipo_indirizzo_descrizione: 'Consegna',
  ripiego_tipo_indirizzo_id: 5, ripiego_tipo_indirizzo_codice_interno: 'DOMFISC',
  ripiego_tipo_indirizzo_descrizione: 'Domicilio fiscale',
}]

function apri() {
  const w = monta(IndirizziMancantiForm, { titolo: 'Fornitore', mancanti: mancanti() }, {
    global: { stubs: { IndirizzoSoggettoForm: FormFinto } },
  })
  const finto = w.findComponent(FormFinto)
  // Compila il tipo attivo, poi passa a `prossimo` come farebbe la barra dei tipi.
  const compila = async (testo, prossimo) => {
    finto.props('form').indirizzo_libero = testo
    if (prossimo) {
      finto.vm.$emit('switch-tipo', prossimo)
      await nextTick()
    }
  }
  return { w, compila }
}

const tipiDelPayload = (w) => w.vm.toPayloadArray().map(p => p.tipo_indirizzo_codice_interno).sort()

describe('IndirizziMancantiForm — la rilettura dei motivi', () => {
  it('1) stessi tipi in un array nuovo: i due indirizzi compilati restano', async () => {
    const { w, compila } = apri()
    await compila('Via della consegna 1', 'DOMFISC')
    await compila('Via del domicilio 2')
    await w.setProps({ mancanti: mancanti() })
    expect(tipiDelPayload(w)).toEqual(['DOMFISC', 'SPED'])
  })

  it('2) tipi diversi: la matrice si rifà sui tipi nuovi', async () => {
    const { w, compila } = apri()
    await compila('Via della consegna 1', 'DOMFISC')
    await w.setProps({ mancanti: [{ ...mancanti()[0], ripiego_tipo_indirizzo_codice_interno: null }] })
    // Gli indirizzi compilati per i tipi di prima non partono.
    const tipi = tipiDelPayload(w)
    expect(tipi).not.toContain('DOMFISC')
  })
})
