// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `mapAvailableActionsToDrawerActions` — il
//        punto in cui le transizioni che il DATABASE ammette diventano i
//        pulsanti di `DrawerActionsBar`. Scritto il 2026-09-23 (brief
//        magazzino 2-bis, punto 2 del piano sui presidi del frontend): il
//        file non aveva nessuna spec, e UNDICI drawer ci passano attraverso.
//
// ⭐ E' la leva piu' economica che il frontend abbia su questa famiglia: il
//    mapper e' una funzione PURA, quindi si prova oggi, senza montare niente
//    e senza dipendenze nuove. Provato lui, gli undici chiamanti ereditano la
//    parte che conta — quale pulsante nasce, se e' acceso, e che cosa dice
//    quando e' spento.
//
// ⚠️ Cio' che NON copre, ed e' dichiarato: il CABLAGGIO del singolo drawer
//    (quale campo del blob legge) e la resa a video. Il primo lo presidia
//    `npm run guard:capability`, la seconda vuole `@vue/test-utils` + `jsdom`
//    — decisione di Tid, non ancora presa quando questo file e' nato.
//
// Note: funzione pura (nessuna API, nessun DOM). `t` e' l'identita' sulla
//       chiave, `te` dice se la chiave «esiste»: cosi' le asserzioni parlano
//       di CHIAVI, non di traduzioni — che vivono nei locales e cambiano.
//
// Indice test:
//   1) una voce del DB diventa un pulsante `kind: 'state'`
//   2) `enabled: false` -> pulsante DISABILITATO, mai nascosto
//   3) il motivo diventa il tooltip, dalla `reason_key`
//   4) chiave i18n mancante -> si vede il CODICE, mai il path della chiave
//   5) `reasons[]` (piu' motivi) -> tooltip multi-riga
//   6) readonly -> nessuna azione di stato
//   7) `permission` -> stampata su OGNI azione, per il gate del BB
//   8) senza `key` la chiave si deriva dallo stato di destinazione
//   9) `onAction` riceve l'azione INTERA (il chiamante decide conferme/dialog)
//  10) un'azione senza `enabled` degrada ad ABILITATA (domini piu' vecchi)
//  11) un motivo SENZA `reason_key` usa il codice grezzo (trovato per mutazione)
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import { mapAvailableActionsToDrawerActions } from './useDrawerActions'

// `t` rende la chiave stessa: le asserzioni parlano di chiavi, non di frasi.
const t = (k) => k
// `te` finge un catalogo i18n: esiste tutto tranne cio' che si dichiara qui.
const teCon = (mancanti = []) => (k) => !mancanti.includes(k)

// Una voce come la emette `script.fn_available_actions_*`.
function voceDb(extra = {}) {
  return {
    key: 'annulla',
    target_state: 'CANCEL',
    label_key: 'magazzino.documenti_interni.azione.annulla',
    icon: 'pi pi-times',
    severity: 'danger',
    requires_confirm: true,
    enabled: true,
    reason: null,
    reason_key: null,
    manuale: true,
    ...extra,
  }
}

describe('mapAvailableActionsToDrawerActions', () => {
  it('1) una voce del database diventa un pulsante di stato', () => {
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb()], t, te: teCon(),
    })
    expect(a.kind).toBe('state')
    expect(a.key).toBe('annulla')
    expect(a.label).toBe('magazzino.documenti_interni.azione.annulla')
    expect(a.icon).toBe('pi pi-times')
    expect(a.severity).toBe('danger')
    expect(a.disabled).toBe(false)
    expect(a.tooltip).toBeUndefined()
  })

  it('2) `enabled: false` disabilita il pulsante, non lo nasconde', () => {
    // ⭐ E' la regola di api.md §Capability: «permesso ⇒ nascondi, stato ⇒
    //    disabilita col motivo». Un pulsante che sparisce non spiega niente.
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb({ enabled: false, reason: 'X', reason_key: 'k.x' })],
      t, te: teCon(),
    })
    expect(a.disabled).toBe(true)
    expect(a.visible).not.toBe(false)
  })

  it('3) il motivo diventa il tooltip, letto dalla `reason_key`', () => {
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb({
        enabled: false,
        reason: 'DOCUMENTO_SENZA_RIGHE',
        reason_key: 'magazzino.documenti_interni.registra_reason.senza_righe',
      })],
      t, te: teCon(),
    })
    expect(a.tooltip).toBe('magazzino.documenti_interni.registra_reason.senza_righe')
  })

  it('4) chiave i18n mancante: si vede il CODICE, mai il path della chiave', () => {
    // ⚠️ Fail-visible. Il path di una chiave a video non dice niente a chi
    //    legge; il codice macchina almeno si puo' cercare.
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb({
        enabled: false, reason: 'DOCUMENTO_SENZA_RIGHE', reason_key: 'chiave.che.non.ce',
      })],
      t, te: teCon(['chiave.che.non.ce']),
    })
    expect(a.tooltip).toBe('DOCUMENTO_SENZA_RIGHE')
  })

  it('5) piu` motivi: un tooltip per riga', () => {
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb({
        enabled: false,
        reasons: [
          { reason: 'UNO', reason_key: 'k.uno' },
          { reason: 'DUE', reason_key: 'k.due' },
        ],
      })],
      t, te: teCon(),
    })
    expect(a.tooltip).toBe('k.uno\nk.due')
  })

  it('6) in sola lettura non nasce nessuna azione di stato', () => {
    // ⚠️ Il chiamante passa il readonly PURO (permessi + contesto), non quello
    //    che include il lock di stato: un documento confermato ha il form
    //    bloccato e deve comunque poter mostrare «Riapri».
    expect(mapAvailableActionsToDrawerActions({
      availableActions: [voceDb()], t, te: teCon(), readonly: true,
    })).toEqual([])
    // e accetta anche un ref, che e' come i drawer lo hanno in mano
    expect(mapAvailableActionsToDrawerActions({
      availableActions: [voceDb()], t, te: teCon(), readonly: ref(true),
    })).toEqual([])
  })

  it('7) il permesso di processo si stampa su OGNI azione', () => {
    const azioni = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb(), voceDb({ key: 'conferma', target_state: 'CONFIRM' })],
      t, te: teCon(), permission: 'registra_magazzino',
    })
    expect(azioni.map((a) => a.action)).toEqual(['registra_magazzino', 'registra_magazzino'])
    // ⛔ Senza `permission` la chiave NON c'e': un `action: undefined` sarebbe
    //    un gate dichiarato e mai applicato.
    const senza = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb()], t, te: teCon(),
    })
    expect('action' in senza[0]).toBe(false)
  })

  it('8) senza `key` la chiave si deriva dallo stato di destinazione', () => {
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb({ key: undefined })], t, te: teCon(),
    })
    expect(a.key).toBe('state-CANCEL')
  })

  it('9) `onAction` riceve l`azione intera, non solo la sua chiave', () => {
    // ⭐ `requires_confirm` e `target_state` restano opachi al BB: il drawer
    //    li legge dall'azione e decide se aprire una conferma. E' cosi' che
    //    la matrice resta un DATO e non diventa un `if` nel frontend.
    const onAction = vi.fn()
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb()], t, te: teCon(), onAction,
    })
    a.command()
    expect(onAction).toHaveBeenCalledTimes(1)
    const ricevuta = onAction.mock.calls[0][0]
    expect(ricevuta.target_state).toBe('CANCEL')
    expect(ricevuta.requires_confirm).toBe(true)
  })

  it('10) un`azione senza `enabled` resta abilitata', () => {
    // ⚠️ Confronto stretto con `false`: i domini che non emettono `enabled`
    //    degradano ad abilitato, non a spento — o il giorno che nascono si
    //    presenterebbero con tutti i pulsanti grigi e nessun motivo.
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [{ key: 'emetti', target_state: 'EMESSO', label_key: 'k.emetti' }],
      t, te: teCon(),
    })
    expect(a.disabled).toBe(false)
    expect(a.tooltip).toBeUndefined()
  })

  it('11) un motivo senza `reason_key` usa il codice grezzo', () => {
    // 🔴 QUESTO TEST NASCE DA UNA MUTAZIONE, il 2026-09-23: svuotando il ramo
    //    «motivo senza chiave» del mapper i primi dieci test restavano tutti
    //    VERDI — coprivano solo il ramo con la `reason_key`. Un dominio che
    //    emette il motivo e non la chiave (o che la perde) avrebbe mostrato
    //    un tooltip VUOTO su un pulsante spento: il caso peggiore, perche' a
    //    video e' identico a un pulsante spento senza ragione.
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb({ enabled: false, reason: 'STATO_NON_AMMESSO', reason_key: null })],
      t, te: teCon(),
    })
    expect(a.tooltip).toBe('STATO_NON_AMMESSO')
  })
})
