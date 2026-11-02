// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL PRIMO TEST DI COMPONENTE DEL PROGETTO (2026-09-23) — la barra
//        azioni dei drawer, cioe' la superficie su cui arriva a video ogni
//        capability di documento: 19 drawer la montano.
//
// ⭐ PERCHE' PROPRIO QUESTA, E PERCHE' ORA. Fino a oggi il frontend provava
//    solo funzioni pure, e tre cantieri in una settimana — rate (17-09),
//    filtri di lista (23-09), barra del drawer di magazzino (23-09) — hanno
//    lasciato scoperto lo STESSO difetto: un pulsante che non compare o resta
//    grigio non rompe niente, non accende nessun lint, e a video sembra una
//    regola. I filtri ne hanno pagati due in un giorno solo.
//
// ⭐ E il test 4 di questo file e' il motivo per cui il primo componente e'
//    questo e non un altro: il 2026-08-27 il motivo di un pulsante spento non
//    compariva MAI, su tutte le liste e su tutti i drawer, perche' il tooltip
//    era appeso al `<Button disabled>` — che non emette eventi del mouse.
//    Il rimedio (il tooltip su un INVOLUCRO) e' vivo da allora e **non aveva
//    un presidio**: nessuna funzione pura lo puo' vedere, perche' e' una
//    proprieta' di DOVE sta un attributo nel DOM.
//
// ⚠️ Cio' che questo test NON vede, e va detto: come la barra e' DISEGNATA.
//    jsdom non calcola il CSS, quindi la variante compatta sotto i 1024px —
//    che e' una media query — qui non si distingue da quella desktop. Le due
//    liste di pulsanti si provano per CONTENUTO (chi finisce inline, chi nel
//    kebab), non per visibilita'.
//
// Indice test:
//   1) un'azione visibile diventa un pulsante, con la sua etichetta
//   2) `visible: false` non rende niente
//   3) un'azione spenta E' RESA, disabilitata (mai nascosta)
//   4) ⭐ il tooltip del motivo sta sull'INVOLUCRO, non sul Button spento
//   5) `hideWhenReadonly` sparisce nella catena readonly, il resto resta
//   6) `action` (permesso di processo): senza, il pulsante non c'e'
//   7) il permesso c'e' -> il pulsante torna
//   8) il click chiama il `command` dell'azione
//   9) un `command` non parte da un pulsante disabilitato
//  10) `kind` decide dove finisce: `state`/`manage` inline, `secondary` nel kebab
//  11) `infoKey`: la nota di stato compare anche SENZA nessuna azione
//  12) barra vuota e senza nota: non si rende proprio niente
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

import DrawerActionsBar from './DrawerActionsBar.vue'
import { READONLY_KEY } from '../composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import { monta } from '../../../test/montaggio'

// Scopo: un'azione come la costruisce un drawer (stampo: le azioni di stato
//        che escono da `mapAvailableActionsToDrawerActions`).
function azione(extra = {}) {
  return {
    key: 'conferma',
    kind: 'state',
    label: 'Conferma',
    icon: 'pi pi-check',
    severity: 'success',
    command: () => {},
    ...extra,
  }
}

// Scopo: i pulsanti resi, per etichetta — la lettura piu' vicina a «che cosa
//        vede chi guarda».
function etichette(wrapper) {
  return wrapper.findAll('button').map((b) => b.text()).filter(Boolean)
}

describe('DrawerActionsBar', () => {
  beforeEach(() => {
    // Pinia attiva PRIMA del montaggio: `useAuthStore()` la cerca all'import
    // del composable, non al primo uso.
    setActivePinia(createPinia())
  })

  it('1) un`azione visibile diventa un pulsante con la sua etichetta', () => {
    const w = monta(DrawerActionsBar, { actions: [azione()] })
    expect(etichette(w)).toContain('Conferma')
  })

  it('2) `visible: false` non rende niente', () => {
    const w = monta(DrawerActionsBar, { actions: [azione({ visible: false })] })
    expect(etichette(w)).not.toContain('Conferma')
  })

  it('3) un`azione spenta E` RESA, disabilitata — mai nascosta', () => {
    // ⭐ E' la regola di api.md §Capability: «permesso ⇒ nascondi, stato ⇒
    //    disabilita col motivo». Un pulsante che sparisce non spiega niente,
    //    e chi guarda non distingue «non adesso» da «mai».
    const w = monta(DrawerActionsBar, {
      actions: [azione({ disabled: true, tooltip: 'Il documento non ha righe.' })],
    })
    const b = w.findAll('button').find((x) => x.text() === 'Conferma')
    expect(b).toBeDefined()
    expect(b.attributes('disabled')).toBeDefined()
  })

  it('4) il tooltip del motivo sta sull`INVOLUCRO, non sul pulsante spento', () => {
    // 🔴 QUESTO E' IL TEST PER CUI IL PRIMO COMPONENTE E' QUESTO.
    //    Un `<button disabled>` non emette eventi del mouse: la direttiva
    //    tooltip di PrimeVue aggancia `mouseenter` sull'elemento su cui sta,
    //    quindi appesa al Button il motivo non compare MAI — e a pulsante
    //    spento e' esattamente quando serve, perche' porta cio' che il
    //    database manda con `enabled:false` + `reason`.
    //    ⚠️ Successo davvero, e per mesi: fino al 2026-08-27 il motivo era
    //    muto su TUTTE le liste e su tutti i drawer che usano il mapper.
    //    Nessuna funzione pura puo' vederlo: e' una proprieta' di DOVE sta un
    //    attributo nel DOM.
    const w = monta(DrawerActionsBar, {
      actions: [azione({ disabled: true, tooltip: 'Il documento non ha righe.' })],
    })
    const bottone = w.findAll('button').find((x) => x.text() === 'Conferma')
    const involucro = bottone.element.parentElement

    // L'involucro c'e', ed e' lui a portare il tooltip.
    expect(involucro.className).toContain('app-action-tooltip-wrap')
    // PrimeVue monta il tooltip sull'elemento: resta un `data-pd-tooltip`
    // oppure un `aria-describedby`/title a seconda della versione — quello che
    // il test fissa e' che il pulsante NON e' il nodo che lo porta.
    expect(bottone.element.getAttribute('data-pd-tooltip')).toBeNull()
  })

  it('5) `hideWhenReadonly` sparisce in sola lettura, il resto resta', () => {
    const w = monta(
      DrawerActionsBar,
      {
        actions: [
          azione({ key: 'salva', label: 'Salva', hideWhenReadonly: true }),
          azione({ key: 'esporta', label: 'Esporta' }),
        ],
      },
      { provide: { [READONLY_KEY]: ref(true) } },
    )
    const viste = etichette(w)
    expect(viste).not.toContain('Salva')
    expect(viste).toContain('Esporta')
  })

  it('6) senza il permesso di processo il pulsante non c`e`', () => {
    // ⭐ «Permesso ⇒ NASCONDI»: l'altra meta' della regola. Qui il pulsante
    //    sparisce davvero, perche' non e' «non adesso», e' «non tu».
    const w = monta(DrawerActionsBar, {
      actions: [azione({ label: 'Registra', action: 'registra_magazzino' })],
    })
    expect(etichette(w)).not.toContain('Registra')
  })

  it('7) col permesso il pulsante torna', () => {
    const auth = useAuthStore()
    // ⚠️ `azioniAbilitate` e' un COMPUTED su `user.azioni_abilitate`: si
    //    prepara l'utente, non il derivato — assegnare al computed non
    //    fallisce, semplicemente non ha effetto.
    auth.user = { azioni_abilitate: { registra_magazzino: true } }
    const w = monta(DrawerActionsBar, {
      actions: [azione({ label: 'Registra', action: 'registra_magazzino' })],
    })
    expect(etichette(w)).toContain('Registra')
  })

  it('8) il click chiama il `command` dell`azione', async () => {
    const command = vi.fn()
    const w = monta(DrawerActionsBar, { actions: [azione({ command })] })
    await w.findAll('button').find((x) => x.text() === 'Conferma').trigger('click')
    expect(command).toHaveBeenCalledTimes(1)
  })

  it('9) un pulsante disabilitato non fa partire il suo `command`', async () => {
    const command = vi.fn()
    const w = monta(DrawerActionsBar, { actions: [azione({ command, disabled: true })] })
    await w.findAll('button').find((x) => x.text() === 'Conferma').trigger('click')
    expect(command).not.toHaveBeenCalled()
  })

  it('10) il `kind` decide dove finisce: inline o nel kebab', () => {
    const w = monta(DrawerActionsBar, {
      actions: [
        azione({ key: 'conferma', label: 'Conferma', kind: 'state' }),
        azione({ key: 'export', label: 'Esporta', kind: 'secondary' }),
      ],
    })
    // Lo `state` e' un pulsante con la sua etichetta; il `secondary` vive nel
    // menu popup (che PrimeVue rende solo all'apertura), quindi inline non c'e'.
    const viste = etichette(w)
    expect(viste).toContain('Conferma')
    expect(viste).not.toContain('Esporta')
    // ...ma il kebab che lo contiene si', altrimenti sarebbe irraggiungibile.
    expect(w.find('.app-manage-btn').exists()).toBe(true)
  })

  it('11) la nota di stato compare anche SENZA nessuna azione', () => {
    // ⭐ «Una lista di azioni vuota e' indistinguibile da un errore di
    //    caricamento»: se da uno stato non si puo' fare nulla, la barra deve
    //    dirlo — ed e' un DATO (`stato_info_key`), non una scelta del
    //    componente.
    const w = monta(DrawerActionsBar, {
      actions: [],
      infoKey: 'magazzino.documenti_interni.stato_info.posted',
    })
    expect(w.text()).toContain('magazzino.documenti_interni.stato_info.posted')
  })

  it('12) senza azioni e senza nota non si rende niente', () => {
    const w = monta(DrawerActionsBar, { actions: [] })
    expect(w.find('.app-drawer-actions').exists()).toBe(false)
  })
})
