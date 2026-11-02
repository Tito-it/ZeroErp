// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
//   1) una voce del DB diventa un pulsante `kind: 'state'` (icona e colore dal verbo)
//   1b) la `severity` che il DB manda ancora NON conta: vale quella del verbo
//   2) `enabled: false` -> pulsante DISABILITATO, mai nascosto
//   3) il motivo diventa il tooltip, dalla `reason_key`
//   4) chiave i18n mancante -> si vede il CODICE, mai il path della chiave
//   5) `reasons[]` (piu' motivi) -> tooltip multi-riga
//   6) readonly -> nessuna azione di stato
//   7) nessun gate di permesso: la chiave `action` non nasce (permesso ⇒ nascondi, dal DB)
//   8) senza `key` la chiave si deriva dallo stato di destinazione
//   9) `onAction` riceve l'azione INTERA (il chiamante decide conferme/dialog)
//  10) un'azione senza `enabled` degrada ad ABILITATA (domini piu' vecchi)
//  11) un motivo SENZA `reason_key` usa il codice grezzo (trovato per mutazione)
//  12) i `valori` del motivo arrivano alla frase come segnaposto posizionali
//  13) un motivo senza `valori` si traduce SENZA parametri (come prima)
//  14) `testoMotivi` — la sede unica usata anche dal lotto: tutti i motivi
//  15) `testoMotivi` senza motivi leggibili -> '' (il chiamante ripiega)
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import { mapAvailableActionsToDrawerActions, testoMotivi } from './useDrawerActions'
import { MANAGE_ICONS } from '../constants'

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
    // Icona e colore li da' il verbo (dal 2026-09-27), non il DB.
    expect(a.icon).toBe(MANAGE_ICONS.ANNULLA)
    expect(a.severity).toBe('danger')
    expect(a.disabled).toBe(false)
    expect(a.tooltip).toBeUndefined()
  })

  it('1b) la severity del DB non conta: vale quella del verbo', () => {
    // ⭐ Il DB la manda ancora finche' il brief non la toglie: il pulsante non
    //    deve cambiare colore ne' prima ne' dopo.
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb({ key: 'conferma', severity: 'success' })], t, te: teCon(),
    })
    expect(a.severity).toBe('info')
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

  it('7) nessun gate di permesso: la chiave `action` non nasce', () => {
    // ⛔ Il permesso lo applica la capability del DB (permesso ⇒ nascondi):
    //    un `action` stampato qui sarebbe una seconda sede del permesso.
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb()], t, te: teCon(),
    })
    expect('action' in a).toBe(false)
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

  it('12) i `valori` del motivo arrivano alla frase come segnaposto `{0}`', () => {
    // Il conteggio dei prezzi non autorizzati viaggia nei `valori`
    // (script.fn_check_prezzi_autorizzati): senza, il tooltip direbbe «ci
    // sono prezzi in attesa» e non quanti. `t` qui rende chiave + parametri.
    const tp = vi.fn((k, p) => (p ? `${k}|${p.join(',')}` : k))
    const [a] = mapAvailableActionsToDrawerActions({
      availableActions: [voceDb({
        key: 'emetti', enabled: false,
        reason: 'PREZZO_PENDENTE', reason_key: 'common.azione_reason.prezzo_pendente',
        reasons: [
          { reason: 'PREZZO_PENDENTE', reason_key: 'common.azione_reason.prezzo_pendente', valori: ['2'] },
          { reason: 'PREZZO_RIFIUTATO', reason_key: 'common.azione_reason.prezzo_rifiutato', valori: ['1'] },
        ],
      })],
      t: tp, te: teCon(),
    })
    expect(a.tooltip).toBe(
      'common.azione_reason.prezzo_pendente|2\ncommon.azione_reason.prezzo_rifiutato|1',
    )
    expect(tp).toHaveBeenCalledWith('common.azione_reason.prezzo_pendente', ['2'])
  })

  it('13) un motivo senza `valori` si traduce senza parametri', () => {
    // I motivi che non portano valori (o li portano vuoti) restano la
    // chiamata di sempre `t(key)`: la modifica non tocca i testi esistenti.
    const tp = vi.fn((k) => k)
    mapAvailableActionsToDrawerActions({
      availableActions: [voceDb({
        enabled: false, reason: 'SENZA_RIGHE', reason_key: 'common.azione_reason.senza_righe',
        reasons: [{ reason: 'SENZA_RIGHE', reason_key: 'common.azione_reason.senza_righe', valori: [] }],
      })],
      t: tp, te: teCon(),
    })
    const chiamata = tp.mock.calls.find(([k]) => k === 'common.azione_reason.senza_righe')
    expect(chiamata).toEqual(['common.azione_reason.senza_righe'])
  })

  it('14) `testoMotivi` rende tutti i motivi, col ripiego sul motivo singolo', () => {
    // Estratta il 2026-09-24 (regola del 2): la usa anche `useLottoAzioni`
    // per l'avviso del kebab di lista, che aveva la sua copia senza `valori`.
    const tp = (k, p) => (p ? `${k}|${p.join(',')}` : k)
    expect(testoMotivi(tp, teCon(), {
      reasons: [
        { reason: 'A', reason_key: 'k.a', valori: ['3'] },
        { reason: 'B', reason_key: 'k.b' },
      ],
    })).toBe('k.a|3\nk.b')
    // Senza `reasons` vale il motivo dell'azione stessa; chiave assente dai
    // locales -> il codice, mai il path.
    expect(testoMotivi(tp, teCon(['k.x']), { reason: 'X', reason_key: 'k.x' })).toBe('X')
  })

  it('15) `testoMotivi` senza motivi leggibili torna stringa vuota', () => {
    // Il lotto ripiega su «azione non più disponibile» con `||`: una stringa
    // vuota deve restare falsy, non diventare un avviso senza testo.
    expect(testoMotivi(t, teCon(), { enabled: false, reason: null, reason_key: null })).toBe('')
    expect(testoMotivi(t, teCon(), undefined)).toBe('')
  })
})
