// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La RETE sotto il chrome delle conferme (2026-09-18). Nasce insieme
//        alla centralizzazione in `richiedi` e al rename `title` -> `header`:
//        cio' che fissa non e' l'estetica, e' che OGNI conferma arrivi a
//        PrimeVue con il titolo nella chiave giusta e con lo stesso chrome —
//        le due cose che a video si vedono e che un refactor puo' perdere
//        senza che niente fallisca (il difetto originale era esattamente
//        questo: `header:` scritto dal chiamante e ignorato in silenzio).
// Note: si mockano i due collaboratori esterni — `useConfirm` di PrimeVue
//        (vuole un'app viva) e `useI18n` (vuole un'istanza). Le costanti
//        NON sono mockate: sono la posta in gioco.
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

import { MANAGE_ICONS, STATUS_ICONS } from '../constants'

const require = vi.fn()

vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require }) }))
// `t` torna la chiave: cosi' si vede QUALE chiave e' stata chiesta.
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (chiave) => chiave }) }))

const { useConfirmAction } = await import('./useConfirmAction')

beforeEach(() => require.mockClear())

// Il chrome che ogni conferma deve portare, qualunque funzione l'abbia aperta.
// ⛔ `closeOnEscape: false` E' VOLUTO: e' il listener `document` di PrimeVue,
//    che si chiuderebbe insieme al Drawer sotto. ESC lo gestisce la radice
//    della ConfirmDialog in App.vue (`pt.root`) — chiude solo la conferma.
const CHROME_STANDARD = {
  icon: STATUS_ICONS.ERRORE,
  closeOnEscape: false,
  rejectClass: 'p-button-secondary',
  rejectLabel: 'common.cancel',
  rejectIcon: MANAGE_ICONS.BACK,
}

describe('useConfirmAction — il chrome sta in un punto solo', () => {
  it('⭐ confirmAction: `header` arriva a PrimeVue come `header`', () => {
    const onAccept = () => {}
    useConfirmAction().confirmAction({ header: 'azione.titolo', message: 'azione.msg', onAccept })
    expect(require).toHaveBeenCalledWith(
      expect.objectContaining({
        header: 'azione.titolo',
        message: 'azione.msg',
        accept: onAccept,
        acceptLabel: 'common.confirm',
        acceptIcon: MANAGE_ICONS.CONFIRM,
        acceptClass: '',
        ...CHROME_STANDARD,
      }),
    )
  })

  it('⛔ `title` NON e\' la chiave: non diventa `header`', () => {
    // E' il difetto del 2026-09-18 al contrario: il composable non deve
    // «capire» una chiave sbagliata — la respinge il guard statico, e qui si
    // fissa che non c'e' un alias silenzioso.
    useConfirmAction().confirmAction({ title: 'sbagliato', message: 'm', onAccept: () => {} })
    expect(require.mock.calls[0][0].header).toBeUndefined()
  })

  it('danger=true: coppia «Elimina» + cestino + bottone rosso, stesso chrome', () => {
    useConfirmAction().confirmAction({ header: 'h', message: 'm', danger: true, onAccept: () => {} })
    expect(require).toHaveBeenCalledWith(
      expect.objectContaining({
        acceptLabel: 'common.delete',
        acceptIcon: MANAGE_ICONS.DELETE,
        acceptClass: 'p-button-danger',
        ...CHROME_STANDARD,
      }),
    )
  })

  it('label/icona dell\'accept sono sovrascrivibili, il chrome no', () => {
    useConfirmAction().confirmAction({
      header: 'h', message: 'm', acceptLabel: 'x.invia', acceptIcon: MANAGE_ICONS.SEND, onAccept: () => {},
    })
    expect(require).toHaveBeenCalledWith(
      expect.objectContaining({ acceptLabel: 'x.invia', acceptIcon: MANAGE_ICONS.SEND, ...CHROME_STANDARD }),
    )
  })

  it('confirmDelete: titolo e messaggio standard, coppia distruttiva, stesso chrome', () => {
    useConfirmAction().confirmDelete('Mario Rossi', () => {})
    expect(require).toHaveBeenCalledWith(
      expect.objectContaining({
        header: 'confirm.delete_title',
        message: 'confirm.delete_message',
        acceptLabel: 'common.delete',
        acceptIcon: MANAGE_ICONS.DELETE,
        acceptClass: 'p-button-danger',
        ...CHROME_STANDARD,
      }),
    )
  })

  it('confirmSave: titolo standard, messaggio sovrascrivibile, stesso chrome', () => {
    useConfirmAction().confirmSave(() => {})
    expect(require.mock.calls[0][0]).toEqual(
      expect.objectContaining({ header: 'confirm.save_title', message: 'confirm.save_message', ...CHROME_STANDARD }),
    )
    useConfirmAction().confirmSave(() => {}, 'impatta tutti')
    expect(require.mock.calls[1][0].message).toBe('impatta tutti')
  })

  it('⚠️ `closable` NON passa da qui: PrimeVue 4 non la inoltra al Dialog', () => {
    // La X delle conferme si spegne sul tag <ConfirmDialog> in App.vue. Se un
    // giorno qualcuno la mettesse qui, non farebbe niente e sembrerebbe fatto.
    useConfirmAction().confirmAction({ header: 'h', message: 'm', onAccept: () => {} })
    expect(require.mock.calls[0][0]).not.toHaveProperty('closable')
  })
})
