// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: cosa manda al genitore il Salva di `<ListaColonneModal>`. La
//        preferenza e' per chiave (`preferenzaPerChiave`): una chiave che
//        arriva al genitore diversa da com'era caricata diventa una scelta, e
//        congela quella dello standard. Le colonne si mandano quindi solo se
//        sono cambiate DAVVERO, con lo stesso confronto di «modifiche non
//        salvate».
//
// Indice test:
//   1. Salva senza toccare niente: niente colonne, righe per pagina «standard»
//   2. ⭐ colonna spenta e riaccesa: non e' una modifica, le colonne non partono
//   3. colonna spenta: le colonne partono
//   4. righe per pagina dalla preferenza: il campo parte con quella misura
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import ToggleSwitch from 'primevue/toggleswitch'
import ListaColonneModal from './ListaColonneModal.vue'
import { monta } from '../../../test/montaggio'

// Il guscio si finge: `AppDrawer` monta il contenuto a fine animazione, che
// jsdom non fa. Sotto esame resta la modale.
const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  emits: ['save', 'update:visible'],
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

function config(origine = {}) {
  return {
    colonne: [
      { codice: 'codice', ordine: 10 },
      { codice: 'descrizione', ordine: 20 },
    ],
    pagina_dimensione: 50,
    pagina_dimensione_standard: 25,
    origine: { colonne: 'sistema', pagina_dimensione: 'sistema', ...origine },
  }
}

function montaModale(cfg = config()) {
  return monta(ListaColonneModal, { visible: true, config: cfg, catalogo: { colonne: [] } }, {
    global: { stubs: { AppDrawer: AppDrawerFinto } },
  })
}

async function salva(w) {
  w.findComponent(AppDrawerFinto).vm.$emit('save')
  await nextTick()
  return w.emitted('apply').at(-1)[0]
}

async function toggla(w, idx, valore) {
  w.findAllComponents(ToggleSwitch)[idx].vm.$emit('update:modelValue', valore)
  await nextTick()
}

describe('ListaColonneModal — Salva', () => {
  it('1. senza toccare niente: niente colonne, righe per pagina standard', async () => {
    const w = montaModale()
    expect(await salva(w)).toEqual({ pagina_dimensione: null })
  })

  it('2. colonna spenta e riaccesa: le colonne non partono', async () => {
    const w = montaModale()
    await toggla(w, 1, false)
    await toggla(w, 1, true)
    expect(await salva(w)).not.toHaveProperty('colonne')
  })

  it('3. colonna spenta: le colonne partono', async () => {
    const w = montaModale()
    await toggla(w, 1, false)
    const payload = await salva(w)
    expect(payload.colonne.find((c) => c.codice === 'descrizione').visibile).toBe(false)
  })

  it('4. righe per pagina dalla preferenza: il campo parte con quella misura', async () => {
    const w = montaModale(config({ pagina_dimensione: 'preferenza' }))
    expect(await salva(w)).toEqual({ pagina_dimensione: 50 })
  })
})
