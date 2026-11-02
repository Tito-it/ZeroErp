// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il badge delle scadenze listino (2026-10-31):
//        - non scambia un ERRORE per «nessuna scadenza»: fino a quel giorno un
//          `catch {}` azzerava il conteggio e il widget spariva, lo stesso
//          aspetto del caso buono;
//        - conta dalla lista listini col filtro della regola del DB
//          (`in_scadenza`), e al clic chiede di filtrare (D-1): niente piu'
//          endpoint suo, giorni passati dal client e popover con la tabella;
//        - conta con GLI STESSI filtri della lista che lo monta (`filtri`): il
//          clic accende `in_scadenza` sopra di loro, e numero e righe devono
//          coincidere. Una lettura alla nascita, una a ogni cambio di filtri,
//          nessuna per un oggetto nuovo con gli stessi valori; la risposta
//          superata si scarta.
//
// ⚠️ Si finge solo il client HTTP (`listListini`), il contorno: il widget
//    e' quello vero.
//
// Indice test:
//   1) lettura buona con scadenze: il badge col totale, chiesto col filtro e una riga
//   1b) ⭐ il clic emette `filtra`
//   2) lettura buona senza scadenze: niente widget
//   3) ⭐ errore del server: il widget dice «non verificabili», non sparisce
//   4) 403: l'utente non vede le scadenze, niente widget e niente avviso
//   5) ⭐ conta coi filtri della lista, UNA lettura alla nascita
//   6) ⭐ filtri cambiati → si rilegge; stessi valori in un oggetto nuovo → no
//   7) ⭐ la risposta superata non scrive (guard di sequenza)
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

vi.mock('../api/listini', () => ({ listListini: vi.fn() }))

import { listListini } from '../api/listini'
import AlertScadenzeWidget from './AlertScadenzeWidget.vue'
import { monta } from '../../../test/montaggio'

const MESSAGGI = {
  vendite: { listini: { alert_scadenze_non_verificabili: 'Non verificabili', alert_scadenze_filtra: 'Filtra' } },
}

// La busta paginata della lista: `count` e' il TOTALE, `results` la pagina.
const risposta = (totale) => ({ data: { data: { results: totale ? [{ id: 1 }] : [], count: totale } } })
const errore = (status) => Object.assign(new Error('http'), { response: { status } })

describe('AlertScadenzeWidget', () => {
  beforeEach(() => { listListini.mockReset() })

  it('1) lettura buona con scadenze: il badge col conteggio', async () => {
    listListini.mockResolvedValue(risposta(2))
    const w = monta(AlertScadenzeWidget, {}, { messages: MESSAGGI })
    await flushPromises()
    expect(w.find('.alert-scadenze-badge').text()).toBe('2')
    expect(listListini).toHaveBeenCalledWith({ in_scadenza: true, limit: 1, offset: 0 })
  })

  it('1b) il clic emette `filtra`', async () => {
    listListini.mockResolvedValue(risposta(3))
    const w = monta(AlertScadenzeWidget, {}, { messages: MESSAGGI })
    await flushPromises()
    await w.find('.alert-scadenze-widget button').trigger('click')
    expect(w.emitted('filtra')).toHaveLength(1)
  })

  it('2) lettura buona senza scadenze: niente widget', async () => {
    listListini.mockResolvedValue(risposta(0))
    const w = monta(AlertScadenzeWidget, {}, { messages: MESSAGGI })
    await flushPromises()
    expect(w.find('.alert-scadenze-widget').exists()).toBe(false)
  })

  it('3) errore del server: il widget dice «non verificabili», non sparisce', async () => {
    listListini.mockRejectedValue(errore(500))
    const w = monta(AlertScadenzeWidget, {}, { messages: MESSAGGI })
    await flushPromises()
    const btn = w.find('.alert-scadenze-widget button')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('aria-label')).toBe('Non verificabili')
    // Il clic riprova: alla lettura buona compare il conteggio.
    listListini.mockResolvedValue(risposta(1))
    await btn.trigger('click')
    await flushPromises()
    expect(w.find('.alert-scadenze-badge').text()).toBe('1')
  })

  it('4) 403: l\'utente non vede le scadenze, niente widget e niente avviso', async () => {
    listListini.mockRejectedValue(errore(403))
    const w = monta(AlertScadenzeWidget, {}, { messages: MESSAGGI })
    await flushPromises()
    expect(w.find('.alert-scadenze-widget').exists()).toBe(false)
  })

  it('5) conta coi filtri della lista, UNA lettura alla nascita', async () => {
    listListini.mockResolvedValue(risposta(2))
    const filtri = { search: 'abc', utility_id: 3, attivo: true }
    monta(AlertScadenzeWidget, { filtri }, { messages: MESSAGGI })
    await flushPromises()
    expect(listListini).toHaveBeenCalledTimes(1)
    expect(listListini).toHaveBeenCalledWith({ ...filtri, in_scadenza: true, limit: 1, offset: 0 })
  })

  it('6) filtri cambiati → si rilegge; stessi valori in un oggetto nuovo → no', async () => {
    listListini.mockResolvedValue(risposta(2))
    const w = monta(AlertScadenzeWidget, { filtri: { attivo: true } }, { messages: MESSAGGI })
    await flushPromises()
    expect(listListini).toHaveBeenCalledTimes(1)
    // Un oggetto nuovo, gli stessi valori: non e' un filtro cambiato.
    await w.setProps({ filtri: { attivo: true } })
    await flushPromises()
    expect(listListini).toHaveBeenCalledTimes(1)
    listListini.mockResolvedValue(risposta(1))
    await w.setProps({ filtri: { attivo: true, tipologia_id: 7 } })
    await flushPromises()
    expect(listListini).toHaveBeenCalledTimes(2)
    expect(listListini).toHaveBeenLastCalledWith(
      { attivo: true, tipologia_id: 7, in_scadenza: true, limit: 1, offset: 0 },
    )
    expect(w.find('.alert-scadenze-badge').text()).toBe('1')
  })

  it('7) la risposta superata non scrive (guard di sequenza)', async () => {
    let rispondiVecchia
    listListini.mockImplementationOnce(() => new Promise((ok) => { rispondiVecchia = ok }))
    const w = monta(AlertScadenzeWidget, { filtri: { attivo: true } }, { messages: MESSAGGI })
    // Filtri cambiati mentre la prima e' in volo: la seconda risponde subito.
    listListini.mockResolvedValueOnce(risposta(4))
    await w.setProps({ filtri: { attivo: false } })
    await flushPromises()
    expect(w.find('.alert-scadenze-badge').text()).toBe('4')
    // La prima arriva tardi, con un numero di un altro contesto: si scarta.
    rispondiVecchia(risposta(9))
    await flushPromises()
    expect(w.find('.alert-scadenze-badge').text()).toBe('4')
  })
})
