// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `IndirizziSoggettoDrawer` — «Aggiungi» compare solo se il picker del
//        DB (R-2 di brief-db-copia-indirizzo-soggetto) ammette almeno un tipo,
//        anche nel contesto ruolo. Fino al 2026-11-15 il ruolo non leggeva i
//        tipi all'apertura e il pulsante c'era sempre: con il picker letto,
//        un ruolo senza tipi ammessi apriva un form senza tipi.
// Note: si monta il drawer vero; finti solo i contorni — le API, il registro
//       delle azioni di riga (`useAzioneRiga`), il guscio `AppDrawer`, il form
//       dell'indirizzo, il kebab e il dialog della copia.
//
// Indice test:
//   1) ruolo, nessun tipo ammesso: niente «Aggiungi»
//   2) ruolo, un tipo ammesso: «Aggiungi» c'e', e i tipi vengono dal picker
//      della chiave del drawer (l'istanza)
//   3) soggetto, nessun tipo ammesso: niente «Aggiungi»
//   4) ruolo, «Cambia» di un indirizzo del ruolo: UNA `PUT`, niente DELETE +
//      POST. Fino al 2026-11-18 erano due richieste, e la DELETE dell'unico
//      obbligatorio, giudicata da sola, era rifiutata (giro 4 di
//      brief-db-fornitore-privato-indirizzi)
//   5) «Copia come…» sul servizio, di una riga del ruolo: la dialog dice da
//      dove e che la copia va sul SERVIZIO aperto (D-1 di
//      brief-db-copia-indirizzo-destinazione), coi tipi del picker di quella
//      chiave; la conferma chiama il verbo del ruolo con l'istanza del drawer
//   6) sul ruolo senza servizio: la destinazione e' il ruolo, istanza null
//   7) ruolo, riga del SOGGETTO della cascata: la conferma chiama il gemello
//      (dal soggetto al ruolo) con la chiave del drawer, non il verbo del soggetto
//   8) ruolo, il picker della chiave non ammette nessun tipo: «Copia come…»
//      spenta col motivo su ogni riga, insieme ad «Aggiungi» (D-4)
//   9) soggetto: il verbo del soggetto, e il motivo di riga dal registro
//  10) ruolo, il picker NON risponde: «Copia come…» resta accesa (una lettura
//      fallita non e' «nessun tipo ammesso»), e il clic rilegge il picker
// ------------------------------------------------------------

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'
import Button from 'primevue/button'

const api = vi.hoisted(() => ({
  listSoggettoIndirizzi: vi.fn(),
  listRuoloIndirizzi: vi.fn(),
  listSoggettoTipiIndirizzo: vi.fn(),
  listRuoloTipiIndirizzo: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {}, fullPath: '/anagrafiche/clienti' }),
}))
const scritture = vi.hoisted(() => ({
  createRuoloIndirizzo: vi.fn(),
  replaceRuoloIndirizzo: vi.fn(),
  deleteRuoloIndirizzo: vi.fn(),
}))
const copie = vi.hoisted(() => ({
  copiaSoggettoIndirizzo: vi.fn(),
  copiaRuoloIndirizzo: vi.fn(),
  copiaSoggettoIndirizzoSuRuolo: vi.fn(),
}))
const registro = vi.hoisted(() => ({ bloccata: vi.fn(() => false), motivo: vi.fn(() => undefined) }))
vi.mock('../api/anagrafiche', () => ({
  ...api,
  ...scritture,
  ...copie,
  createSoggettoIndirizzo: vi.fn(),
  replaceSoggettoIndirizzo: vi.fn(),
  lookupStati: vi.fn(async () => ({ data: { data: { results: [] } } })),
}))
vi.mock('../../core/composables/useAzioneRiga', () => ({
  useAzioneRiga: () => ({ ...registro, pronta: { value: true } }),
}))

const { monta } = await import('../../../test/montaggio')
const { default: IndirizziSoggettoDrawer } = await import('./IndirizziSoggettoDrawer.vue')

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  setup(_, { slots }) {
    return () => h('div', [slots.default?.(), slots.footer?.()])
  },
})
// I contorni che il caso 4 aziona: il kebab (le azioni della riga), il form
// (il `form` condiviso, da compilare) e il footer (il «Salva»).
const KebabFinto = defineComponent({
  name: 'RowActionsMenu', props: { row: Object, actions: Array }, render: () => null,
})
const FormFinto = defineComponent({
  name: 'IndirizzoSoggettoForm', props: { form: Object }, render: () => null,
})
const FooterFinto = defineComponent({ name: 'FormFooter', emits: ['save'], render: () => null })
const CopiaFinta = defineComponent({
  name: 'CopiaIndirizzoDialog',
  props: { visible: Boolean, tipi: Array, origine: Object, destinazione: String },
  emits: ['confirm'],
  render: () => null,
})

const risposta = (data) => ({ data: { data } })
const TIPO_SPENTO = {
  codice_interno: 'SEDELEG', descrizione: 'Sede legale', obbligatorio: false, ammesso: false,
  reason_key: 'anagrafiche.indirizzi.tipo_blocco.gia_presente', reason_valori: ['Sede legale'],
}
const TIPO_AMMESSO = { codice_interno: 'FATT', descrizione: 'Fatturazione', obbligatorio: false, ammesso: true }

async function apri(props) {
  const w = monta(IndirizziSoggettoDrawer, { visible: false, ...props }, {
    global: {
      stubs: {
        AppDrawer: AppDrawerFinto, IndirizzoSoggettoForm: FormFinto,
        RowActionsMenu: KebabFinto, CopiaIndirizzoDialog: CopiaFinta, FormFooter: FooterFinto,
      },
    },
  })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

const haAggiungi = (w) => w.findAllComponents(Button)
  .some(b => b.props('label') === 'anagrafiche.indirizzo_soggetto.aggiungi_indirizzo')

describe('IndirizziSoggettoDrawer — «Aggiungi» dal picker dei tipi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    registro.bloccata.mockReturnValue(false)
    registro.motivo.mockReturnValue(undefined)
    api.listRuoloIndirizzi.mockResolvedValue(risposta({ indirizzi_ruolo: [], indirizzi_soggetto: [] }))
    api.listSoggettoIndirizzi.mockResolvedValue(risposta({ results: [] }))
  })

  it('1) ruolo, nessun tipo ammesso: niente «Aggiungi»', async () => {
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_SPENTO] }))
    const w = await apri({ context: 'ruolo', soggettoId: 50 })
    expect(haAggiungi(w)).toBe(false)
  })

  it('2) ruolo, un tipo ammesso: «Aggiungi» c\'e\', dal picker della chiave del drawer', async () => {
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_SPENTO, TIPO_AMMESSO] }))
    const w = await apri({ context: 'ruolo', soggettoId: 50, istanzaUtilityId: 9 })
    expect(haAggiungi(w)).toBe(true)
    expect(api.listRuoloTipiIndirizzo).toHaveBeenCalledWith(50, { istanza_utility_id: 9 })
  })

  it('3) soggetto, nessun tipo ammesso: niente «Aggiungi»', async () => {
    api.listSoggettoTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_SPENTO] }))
    const w = await apri({ soggettoId: '019d-uuid' })
    expect(haAggiungi(w)).toBe(false)
  })

  it('4) ruolo, «Cambia» di un indirizzo del ruolo: una PUT, niente DELETE + POST', async () => {
    const riga = {
      id: 31, fonte: 'ruolo', tipo_indirizzo_codice_interno: 'FATT', tipo_indirizzo_descrizione: 'Fatturazione',
      indirizzo_libero: 'Via vecchia 1',
    }
    api.listRuoloIndirizzi.mockResolvedValue(risposta({ indirizzi_ruolo: [riga], indirizzi_soggetto: [] }))
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_AMMESSO] }))
    scritture.replaceRuoloIndirizzo.mockResolvedValue(risposta({ id: 32 }))
    const w = await apri({ context: 'ruolo', soggettoId: 50 })

    w.findComponent(KebabFinto).props('actions').find(a => a.key === 'cambia').command()
    await flushPromises()
    w.findComponent(FormFinto).props('form').indirizzo_libero = 'Via nuova 2'
    w.findComponent(FooterFinto).vm.$emit('save')
    await flushPromises()

    expect(scritture.replaceRuoloIndirizzo).toHaveBeenCalledTimes(1)
    const [ruolo, indirizzoId, payload] = scritture.replaceRuoloIndirizzo.mock.calls[0]
    expect([ruolo, indirizzoId, payload.tipo_indirizzo_codice_interno]).toEqual([50, 31, 'FATT'])
    expect(scritture.deleteRuoloIndirizzo).not.toHaveBeenCalled()
    expect(scritture.createRuoloIndirizzo).not.toHaveBeenCalled()
  })

  const RIGA_RUOLO = {
    id: 41, fonte: 'ruolo', tipo_indirizzo_codice_interno: 'SPED', tipo_indirizzo_descrizione: 'Spedizione',
    indirizzo_display: 'Via Roma 1, Milano',
  }
  const RIGA_SERVIZIO = {
    id: 42, fonte: 'istanza', istanza_utility_id: 9, utility_codice: 'GAS',
    tipo_indirizzo_codice_interno: 'FORN', tipo_indirizzo_descrizione: 'Fornitura',
  }
  const RIGA_SOGGETTO = {
    id: 7, fonte: 'soggetto', soggetto_id: '019d-uuid',
    tipo_indirizzo_codice_interno: 'SEDELEG', tipo_indirizzo_descrizione: 'Sede legale',
  }
  const azioneCopia = (w, riga) => w.findAllComponents(KebabFinto)
    .find(k => k.props('row').id === riga.id).props('actions').find(a => a.key === 'copia')

  async function copia(w, riga, codici) {
    azioneCopia(w, riga).command()
    await flushPromises()
    const dialog = w.findComponent(CopiaFinta)
    if (codici) {
      dialog.vm.$emit('confirm', codici)
      await flushPromises()
    }
    return dialog
  }

  it('5) copia di una riga del ruolo, dal servizio: la destinazione e\' il servizio aperto', async () => {
    api.listRuoloIndirizzi.mockResolvedValue(
      risposta({ indirizzi_ruolo: [RIGA_SERVIZIO, RIGA_RUOLO], indirizzi_soggetto: [] }),
    )
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_SPENTO, TIPO_AMMESSO] }))
    copie.copiaRuoloIndirizzo.mockResolvedValue(risposta({ ids: [90] }))
    const w = await apri({ context: 'ruolo', soggettoId: 50, istanzaUtilityId: 9 })

    const dialog = await copia(w, RIGA_RUOLO)
    expect(dialog.props('visible')).toBe(true)
    expect(dialog.props('origine')).toEqual({
      tipo: 'Spedizione', indirizzo: 'Via Roma 1, Milano', titolare: 'anagrafiche.indirizzi.copia.titolare_ruolo',
    })
    expect(dialog.props('destinazione')).toBe('anagrafiche.indirizzi.copia.titolare_servizio')
    // I tipi sono quelli del picker della chiave del drawer, non della riga.
    expect(dialog.props('tipi')).toEqual([TIPO_SPENTO, TIPO_AMMESSO])
    expect(api.listRuoloTipiIndirizzo).toHaveBeenLastCalledWith(50, { istanza_utility_id: 9 })

    dialog.vm.$emit('confirm', ['FATT'])
    await flushPromises()
    expect(copie.copiaRuoloIndirizzo).toHaveBeenCalledWith(50, 41, ['FATT'], 9)
    expect(copie.copiaSoggettoIndirizzo).not.toHaveBeenCalled()
  })

  it('6) copia sul ruolo senza servizio: la destinazione e\' il ruolo, istanza null', async () => {
    api.listRuoloIndirizzi.mockResolvedValue(risposta({ indirizzi_ruolo: [RIGA_RUOLO], indirizzi_soggetto: [] }))
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_AMMESSO] }))
    copie.copiaRuoloIndirizzo.mockResolvedValue(risposta({ ids: [91] }))
    const w = await apri({ context: 'ruolo', soggettoId: 50 })

    const dialog = await copia(w, RIGA_RUOLO, ['FATT'])
    expect(dialog.props('destinazione')).toBe('anagrafiche.indirizzi.copia.titolare_ruolo')
    expect(api.listRuoloTipiIndirizzo).toHaveBeenLastCalledWith(50, {})
    expect(copie.copiaRuoloIndirizzo).toHaveBeenCalledWith(50, 41, ['FATT'], null)
  })

  it('7) ruolo, riga del soggetto: il gemello dal soggetto al ruolo, sulla chiave del drawer', async () => {
    api.listRuoloIndirizzi.mockResolvedValue(
      risposta({ indirizzi_ruolo: [RIGA_RUOLO], indirizzi_soggetto: [RIGA_SOGGETTO] }),
    )
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_AMMESSO] }))
    copie.copiaSoggettoIndirizzoSuRuolo.mockResolvedValue(risposta({ ids: [92] }))
    const w = await apri({ context: 'ruolo', soggettoId: 50, istanzaUtilityId: 9 })

    const dialog = await copia(w, RIGA_SOGGETTO, ['FATT'])
    expect(dialog.props('origine').titolare).toBe('anagrafiche.indirizzi.copia.titolare_soggetto')
    // Nessuna riga del servizio in lista: il servizio si nomina senza codice.
    expect(dialog.props('destinazione')).toBe('anagrafiche.indirizzi.copia.titolare_servizio_generico')
    expect(api.listSoggettoTipiIndirizzo).not.toHaveBeenCalled()
    expect(copie.copiaSoggettoIndirizzoSuRuolo).toHaveBeenCalledWith(50, 7, ['FATT'], 9)
    expect(copie.copiaSoggettoIndirizzo).not.toHaveBeenCalled()
    expect(copie.copiaRuoloIndirizzo).not.toHaveBeenCalled()
  })

  it('8) ruolo, nessun tipo ammesso sulla chiave: «Copia come…» spenta su ogni riga, con «Aggiungi»', async () => {
    api.listRuoloIndirizzi.mockResolvedValue(
      risposta({ indirizzi_ruolo: [RIGA_RUOLO], indirizzi_soggetto: [RIGA_SOGGETTO] }),
    )
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_SPENTO] }))
    const w = await apri({ context: 'ruolo', soggettoId: 50 })

    for (const riga of [RIGA_RUOLO, RIGA_SOGGETTO]) {
      const azione = azioneCopia(w, riga)
      expect(azione.disabled).toBe(true)
      expect(azione.tooltip).toBe('anagrafiche.indirizzi.copia_blocco.nessun_tipo_proponibile')
    }
    expect(haAggiungi(w)).toBe(false)
    // Il registro delle azioni di riga non decide in contesto ruolo.
    expect(registro.bloccata).not.toHaveBeenCalled()
  })

  it('9) soggetto: il verbo del soggetto, e il motivo di riga dal registro', async () => {
    const riga = { ...RIGA_SOGGETTO, fonte: undefined }
    api.listSoggettoIndirizzi.mockResolvedValue(risposta({ results: [riga] }))
    api.listSoggettoTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_AMMESSO] }))
    copie.copiaSoggettoIndirizzo.mockResolvedValue(risposta({ ids: [93] }))
    // Il motivo si legge quando la riga si disegna: il registro parla prima.
    registro.bloccata.mockReturnValue(true)
    registro.motivo.mockReturnValue('motivo del registro')
    const w = await apri({ soggettoId: '019d-uuid' })
    const azione = azioneCopia(w, riga)
    expect([azione.disabled, azione.tooltip]).toEqual([true, 'motivo del registro'])

    const dialog = await copia(w, riga, ['FATT'])
    expect(dialog.props('destinazione')).toBe('anagrafiche.indirizzi.copia.titolare_soggetto')
    expect(copie.copiaSoggettoIndirizzo).toHaveBeenCalledWith('019d-uuid', 7, ['FATT'])
    expect(copie.copiaSoggettoIndirizzoSuRuolo).not.toHaveBeenCalled()
  })

  it('10) ruolo, il picker non risponde: «Copia come…» resta accesa e il clic lo rilegge', async () => {
    api.listRuoloIndirizzi.mockResolvedValue(risposta({ indirizzi_ruolo: [RIGA_RUOLO], indirizzi_soggetto: [] }))
    api.listRuoloTipiIndirizzo.mockRejectedValueOnce(new Error('rete'))
    const w = await apri({ context: 'ruolo', soggettoId: 50 })

    const azione = azioneCopia(w, RIGA_RUOLO)
    expect([azione.disabled, azione.tooltip]).toEqual([false, 'anagrafiche.indirizzi.copia.azione'])

    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_AMMESSO] }))
    const dialog = await copia(w, RIGA_RUOLO)
    expect(dialog.props('visible')).toBe(true)
    expect(dialog.props('tipi')).toEqual([TIPO_AMMESSO])
  })
})
