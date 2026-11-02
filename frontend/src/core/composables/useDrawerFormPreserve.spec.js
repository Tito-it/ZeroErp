// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa la fotografia del form di `useDrawerFormPreserve`: cosa conta
//        come modifica, quando la fotografia si azzera, e la segnalazione
//        delle modifiche non salvate alla content tab che ospita il drawer.
//
// Indice test:
//  1. modificato: un campo cambiato si', uno rimesso com'era no
//  2. modificato: una data riscelta uguale e un campo vuoto svuotato non sono modifiche
//  3. senza fotografia (creazione) non c'e' niente da confrontare
//  3b. a drawer chiuso fissa() non fa niente (caricamento arrivato tardi)
//  4. alla chiusura la fotografia si azzera: una modifica abbandonata su un
//     documento non finisce sul prossimo aperto
//  5. la tab e' sporca finche' il drawer aperto ha modifiche, e smette a
//     salvataggio o chiusura
//  6. due drawer nella stessa tab: il primo che salva non pulisce l'altro
//  7. chiudere con modifiche chiede conferma; senza modifiche chiude e basta
//  8. un form a ELENCO: riga cambiata sul posto, riga tolta, riga rimessa com'era
//  9. gestoreVisibile: X/ESC passano dallo stesso `chiudi` dell'Annulla
// 10. unisciFotografie: una domanda sola, a chi e' modificato; figlio ancora null
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { gestoreVisibile, unisciFotografie, useDrawerFormPreserve, valoriUguali } from './useDrawerFormPreserve'
import { useTabsStore } from '../../stores/tabs'

vi.mock('vue-router', () => ({ useRoute: () => ({ path: '/vendite/ordini' }) }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (k) => k }) }))
// La conferma: si registra la richiesta, e il test decide se accettarla.
const richieste = []
vi.mock('./useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: (opzioni) => richieste.push(opzioni) }),
}))
// Lo store tabs legge navigation e storage di sessione: qui servono solo le tab.
vi.mock('../navigation', () => ({ DOMAIN_MENUS: {}, resolveTabIcon: () => null }))
vi.mock('../storage', () => ({ session: { get: () => null, set: () => {}, remove: () => {} }, STORAGE_KEYS: {} }))

// Scopo: un drawer finto: form, visibilita' e il BB, dentro uno scope.
function drawer() {
  const form = ref({})
  const visibile = ref(false)
  const scope = effectScope()
  const bb = scope.run(() => useDrawerFormPreserve(form, { visibile: () => visibile.value }))
  // Come fa un drawer: apre, carica dal server passando da `preserva`.
  async function apri(datiServer) {
    visibile.value = true
    await nextTick()
    const applica = bb.preserva()
    form.value = { ...datiServer }
    applica()
    await nextTick()
  }
  async function chiudi() {
    visibile.value = false
    await nextTick()
  }
  return { form, visibile, scope, apri, chiudi, ...bb }
}

describe('useDrawerFormPreserve — modifiche non salvate', () => {
  beforeEach(() => {
    richieste.length = 0
    setActivePinia(createPinia())
    useTabsStore().tabs.push({ id: 't1', path: '/vendite/ordini', dirty: false })
  })

  it('modificato: un campo cambiato si\', uno rimesso com\'era no', async () => {
    const d = drawer()
    await d.apri({ note: 'a', valuta_id: 1 })
    expect(d.modificato.value).toBe(false)
    d.form.value.note = 'b'
    expect(d.modificato.value).toBe(true)
    d.form.value.note = 'a'
    expect(d.modificato.value).toBe(false)
  })

  it('modificato: una data riscelta uguale e un campo vuoto svuotato non sono modifiche', () => {
    expect(valoriUguali(new Date('2026-09-26'), new Date('2026-09-26'))).toBe(true)
    expect(valoriUguali(null, '')).toBe(true)
    expect(valoriUguali(undefined, null)).toBe(true)
    expect(valoriUguali([1, 2], [1, 2])).toBe(true)
    expect(valoriUguali(0, null)).toBe(false)
    expect(valoriUguali(false, null)).toBe(false)
  })

  it('senza fotografia (creazione) non c\'e\' niente da confrontare', () => {
    const d = drawer()
    d.form.value = { note: 'scritto' }
    expect(d.modificato.value).toBe(false)
    d.visibile.value = true
    d.fissa()
    d.form.value.note = 'altro'
    expect(d.modificato.value).toBe(true)
  })

  it('a drawer chiuso fissa() non fa niente: un caricamento arrivato tardi non torna in vita', async () => {
    const d = drawer()
    await d.apri({ note: 'A' })
    await d.chiudi()
    // La fetch del documento A risponde dopo la chiusura, e il drawer fissa.
    d.form.value = { note: 'A' }
    d.fissa()
    // Si apre la creazione: form vuoto, nessuna fotografia vecchia.
    d.visibile.value = true
    await nextTick()
    d.form.value = { note: '' }
    expect(d.modificato.value).toBe(false)
  })

  it('alla chiusura la fotografia si azzera: una modifica abbandonata non finisce sul prossimo documento', async () => {
    const d = drawer()
    await d.apri({ id: 1, note: 'ordine A' })
    d.form.value.note = 'modifica abbandonata'
    await d.chiudi()
    await d.apri({ id: 2, note: 'ordine B' })
    expect(d.form.value.note).toBe('ordine B')
    expect(d.modificato.value).toBe(false)
  })

  it('la tab e\' sporca finche\' il drawer aperto ha modifiche', async () => {
    const tab = useTabsStore().tabs[0]
    const d = drawer()
    await d.apri({ note: 'a' })
    expect(tab.dirty).toBe(false)
    d.form.value.note = 'b'
    await nextTick()
    expect(tab.dirty).toBe(true)
    // Salvataggio: il drawer ricarica dal server, la fotografia e' il salvato.
    const applica = d.preserva()
    d.form.value = { note: 'b' }
    applica()
    await nextTick()
    expect(tab.dirty).toBe(false)
    d.form.value.note = 'c'
    await nextTick()
    expect(tab.dirty).toBe(true)
    await d.chiudi()
    expect(tab.dirty).toBe(false)
  })

  it('due drawer nella stessa tab: il primo che salva non pulisce l\'altro', async () => {
    const tab = useTabsStore().tabs[0]
    const uno = drawer()
    const due = drawer()
    await uno.apri({ note: 'a' })
    await due.apri({ note: 'x' })
    uno.form.value.note = 'b'
    due.form.value.note = 'y'
    await nextTick()
    expect(tab.dirty).toBe(true)
    uno.fissa()
    await nextTick()
    expect(tab.dirty).toBe(true)
    due.scope.stop()
    expect(tab.dirty).toBe(false)
  })

  it('chiudere con modifiche chiede conferma; senza modifiche chiude e basta', async () => {
    const d = drawer()
    const chiudi = vi.fn()
    await d.apri({ note: 'a' })
    d.chiudiConConferma(chiudi)
    expect(chiudi).toHaveBeenCalledOnce()
    expect(richieste).toHaveLength(0)

    d.form.value.note = 'b'
    d.chiudiConConferma(chiudi)
    expect(chiudi).toHaveBeenCalledOnce()
    expect(richieste).toHaveLength(1)
    expect(richieste[0].header).toBe('common.modifiche_non_salvate.titolo')
    // «Chiudi senza salvare»: il drawer si chiude.
    richieste[0].onAccept()
    expect(chiudi).toHaveBeenCalledTimes(2)
  })

  it('un form a elenco: riga cambiata sul posto, riga tolta, riga rimessa com\'era', () => {
    const righe = ref([{ campo: 'a', visibile: true }, { campo: 'b', visibile: true }])
    const scope = effectScope()
    const bb = scope.run(() => useDrawerFormPreserve(righe))
    bb.fissa()
    expect(bb.modificato.value).toBe(false)
    righe.value[0].visibile = false
    expect(bb.modificato.value).toBe(true)
    righe.value[0].visibile = true
    expect(bb.modificato.value).toBe(false)
    righe.value.pop()
    expect(bb.modificato.value).toBe(true)
    scope.stop()
  })

  it('gestoreVisibile: X/ESC passano dallo stesso `chiudi` dell\'Annulla', () => {
    const emit = vi.fn()
    const chiudi = vi.fn()
    const su = gestoreVisibile(emit, chiudi)
    su(false)
    expect(chiudi).toHaveBeenCalledTimes(1)
    expect(emit).not.toHaveBeenCalled()
    su(true)
    expect(emit).toHaveBeenCalledWith('update:visible', true)
  })

  it('unisciFotografie: una domanda sola, a chi e\' modificato; figlio ancora null', async () => {
    const a = drawer()
    const b = drawer()
    await a.apri({ note: 'a' })
    await b.apri({ note: 'b' })
    let figlio = null
    const tutto = unisciFotografie(a, b, () => figlio)
    const chiudi = vi.fn()
    tutto.chiudiConConferma(chiudi)
    expect(tutto.modificato.value).toBe(false)
    expect(chiudi).toHaveBeenCalledTimes(1)
    b.form.value.note = 'cambiata'
    expect(tutto.modificato.value).toBe(true)
    tutto.chiudiConConferma(chiudi)
    expect(richieste).toHaveLength(1)
    expect(chiudi).toHaveBeenCalledTimes(1)
    // Un figlio che espone `modificato` gia' scartato (defineExpose).
    b.form.value.note = 'b'
    figlio = { modificato: true, chiudiConConferma: vi.fn() }
    const tutto2 = unisciFotografie(a, () => figlio)
    expect(tutto2.modificato.value).toBe(true)
    tutto2.chiudiConConferma(chiudi)
    expect(figlio.chiudiConConferma).toHaveBeenCalledWith(chiudi)
  })
})
