// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: l'azione «apri documento» (`buildApriDocumentoAction`): dal
//        2026-10-20 l'area e' il codice della SORGENTE, e un documento che non
//        e' un'area del cruscotto (la fattura d'origine di una riga di
//        commessa) si apre dal registro dei drawer — brief-db-grammatica-
//        unica-documenti §13.6.
//
// Indice test:
//   1) area del cruscotto: vince la sua voce (la commessa apre la GESTIONE)
//   2) sorgente fuori dal cruscotto ma iscritta (FATTURA): si apre quella
//   3) area nulla (il DB dice «non apribile»): azione nascosta
//   4) codice che nessun dominio sa aprire, o id mancante: azione nascosta
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { DOCUMENTO_DRAWER_TIPI as T } from '../core/drawerEntita'
import { buildApriDocumentoAction } from './dashboardAree'
import './iscrizioni'

const azione = (area, documentoId = 7) => {
  const onApri = vi.fn()
  const a = buildApriDocumentoAction({ area, documentoId, label: 'Apri', onApri })
  return { a, onApri }
}

describe('buildApriDocumentoAction', () => {
  it('area del cruscotto: vince la sua voce (la commessa apre la GESTIONE)', () => {
    const { a, onApri } = azione(T.COMMESSA)
    expect(a.visible).toBe(true)
    a.command()
    expect(onApri).toHaveBeenCalledWith(T.COMMESSA_GESTIONE, 7)
  })

  it('sorgente fuori dal cruscotto ma iscritta (FATTURA): si apre quella', () => {
    const { a, onApri } = azione(T.FATTURA)
    expect(a.visible).toBe(true)
    a.command()
    expect(onApri).toHaveBeenCalledWith(T.FATTURA, 7)
  })

  it('area nulla (il DB dice «non apribile»): azione nascosta', () => {
    expect(azione(null).a.visible).toBe(false)
  })

  it('codice che nessun dominio sa aprire, o id mancante: azione nascosta', () => {
    expect(azione('ATTIVITA_CONSUMI').a.visible).toBe(false)
    expect(azione(T.ORDINE_VENDITA, null).a.visible).toBe(false)
  })
})
