// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `inCorso` del BB `useBaFormDefaults`: vero finche' la risposta del
//        cliente non e' arrivata, perche' il drawer tenga spento il Salva. Un
//        Salva premuto prima spediva il form senza i dati del cliente
//        (2026-10-14: sul contratto la scheda di fornitura vuota).
//
// Indice test:
//  1. vero durante la richiesta, falso all'arrivo; i default si applicano
//  2. una richiesta fallita lo spegne (il Salva non resta bloccato)
//  3. cambio cliente rapido: la risposta stantia non lo spegne, l'ultima si'
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useBaFormDefaults } from './useBaFormDefaults'

// Una richiesta che si risolve quando lo dice il test.
function richiestaManuale() {
  let risolvi
  let rifiuta
  const promessa = new Promise((res, rej) => { risolvi = res; rifiuta = rej })
  return { promessa, risolvi, rifiuta }
}

function prepara(richieste) {
  const form = ref({ billing_account_id: null, valuta_id: null })
  const isEdit = ref(false)
  let n = 0
  const fetchDefaults = () => richieste[n++].promessa
  const { applicaDefaults, inCorso } = useBaFormDefaults({ form, isEdit, fetchDefaults })
  return { form, applicaDefaults, inCorso }
}

describe('useBaFormDefaults — inCorso', () => {
  // 1.
  it('vero durante la richiesta, falso quando la risposta arriva', async () => {
    const r = richiestaManuale()
    const { form, applicaDefaults, inCorso } = prepara([r])
    const fatto = applicaDefaults(10)
    expect(inCorso.value).toBe(true)
    r.risolvi({ data: { data: { valuta_id: 3 } } })
    await fatto
    expect(inCorso.value).toBe(false)
    expect(form.value.valuta_id).toBe(3)
  })

  // 2.
  it('una richiesta fallita lo spegne', async () => {
    const r = richiestaManuale()
    const { applicaDefaults, inCorso } = prepara([r])
    const fatto = applicaDefaults(10)
    r.rifiuta(new Error('rete'))
    await fatto
    expect(inCorso.value).toBe(false)
  })

  // 3.
  it('la risposta stantia non lo spegne, l\'ultima si\'', async () => {
    const vecchia = richiestaManuale()
    const nuova = richiestaManuale()
    const { form, applicaDefaults, inCorso } = prepara([vecchia, nuova])
    const primo = applicaDefaults(10)
    const secondo = applicaDefaults(20)
    vecchia.risolvi({ data: { data: { valuta_id: 1 } } })
    await primo
    expect(inCorso.value).toBe(true)
    expect(form.value.valuta_id).toBeNull()
    nuova.risolvi({ data: { data: { valuta_id: 2 } } })
    await secondo
    expect(inCorso.value).toBe(false)
    expect(form.value.valuta_id).toBe(2)
  })
})
