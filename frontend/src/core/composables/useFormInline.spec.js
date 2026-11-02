// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa la macchina del master-detail inline delle righe
//        (`useFormInline`, estratta 2026-09-28 da tre copie): apertura
//        e chiusura del form, il click che apre solo se le righe si scrivono,
//        «Nuova riga» spenta a form aperto, la risincronizzazione dopo una
//        ricarica, e la chiusura al cambio di documento.
// Note: ⛔ Il caso che conta di piu' e' il 6: il form aperto su una riga del
//       documento A deve chiudersi quando il drawer passa al documento B.
//       Una delle tre copie non lo faceva, e «Salva» avrebbe scritto sul
//       padre nuovo senza nessun errore.
//
// Indice test:
//  1. stato iniziale: form chiuso, nessuna riga
//  2. nuova riga: 'create' senza riga; chiudi: tutto azzerato
//  3. apriRiga: 'edit' con la riga, solo se le righe si scrivono
//  4. azioneNuovaRiga: spenta a form aperto e dalla condizione del caller
//  5. risincronizza: riga fresca per id, solo in modifica; assente = resta
//  6. cambio di padre (e chiusura del drawer): il form si chiude
//  7. ⭐ cambio di riga col form aperto: passa da confermaCambio, e `poi` arriva solo dopo il sì
//  8. a form chiuso si apre subito, senza chiedere
//  9. ⭐ aprire il form lo porta in vista (nuova riga e modifica), dopo il render
// 10. chiudere, risincronizzare o cambiare padre NON scorre; senza ancora, niente
// 11. l'ancora accetta un componente (`$el`), e lo smontaggio la scioglie
// 12. ⛔ ogni contenitore della macchina lega l'ancora al suo form
// 13. ⭐ un form MULTI-RADICE (Fragment): si scorre al suo primo elemento vero
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'

// ⚠️ Le costanti VERE, non un mock: un mock dell'icona resterebbe verde anche
//    se `MANAGE_ICONS.ADD` cambiasse nome, e a video il pulsante uscirebbe
//    senza icona.
import { MANAGE_ICONS } from '../constants'
import { useFormInline } from './useFormInline'

describe('useFormInline', () => {
  it('1. parte col form chiuso', () => {
    const r = useFormInline()
    expect(r.formMode.value).toBeNull()
    expect(r.formAperto.value).toBe(false)
    expect(r.rigaInModifica.value).toBeNull()
  })

  it('2. nuova riga apre il form vuoto, chiudi azzera', () => {
    const r = useFormInline()
    r.apriRiga({ id: 1 })
    r.nuovaRiga()
    expect(r.formMode.value).toBe('create')
    expect(r.rigaInModifica.value).toBeNull()
    r.chiudiForm()
    expect(r.formAperto.value).toBe(false)
    expect(r.rigaInModifica.value).toBeNull()
  })

  it('3. il click apre la modifica solo se le righe si scrivono', () => {
    const scrivibile = ref(false)
    const r = useFormInline({ puoModificare: () => scrivibile.value })
    r.apriRiga({ id: 7 })
    expect(r.formAperto.value).toBe(false)
    scrivibile.value = true
    r.apriRiga({ id: 7 })
    expect(r.formMode.value).toBe('edit')
    expect(r.rigaInModifica.value).toEqual({ id: 7 })
    // Una riga assente non apre niente.
    r.chiudiForm()
    r.apriRiga(null)
    expect(r.formAperto.value).toBe(false)
  })

  it('4. «Nuova riga» sparisce a form aperto e segue la condizione del caller', () => {
    const modificabile = ref(true)
    const r = useFormInline()
    const azione = () => r.azioneNuovaRiga({ label: 'Nuova', visible: () => modificabile.value })
    expect(MANAGE_ICONS.ADD).toBeTruthy()
    expect(azione()).toMatchObject({
      key: 'new', kind: 'primary', label: 'Nuova', icon: MANAGE_ICONS.ADD,
      hideWhenReadonly: true, visible: true,
    })
    modificabile.value = false
    expect(azione().visible).toBe(false)
    modificabile.value = true
    r.nuovaRiga()
    expect(azione().visible).toBe(false)
    r.chiudiForm()
    azione().command()
    expect(r.formMode.value).toBe('create')
    // Il verbo del contenitore sostituisce il comando nudo.
    const verbo = () => {}
    expect(r.azioneNuovaRiga({ command: verbo }).command).toBe(verbo)
  })

  it('5. risincronizza rimette la riga fresca, solo in modifica', () => {
    const r = useFormInline()
    r.risincronizza([{ id: 1, prezzo: 2 }])
    expect(r.rigaInModifica.value).toBeNull()
    r.apriRiga({ id: 1, prezzo: 1 })
    r.risincronizza([{ id: 2 }, { id: 1, prezzo: 2 }])
    expect(r.rigaInModifica.value).toEqual({ id: 1, prezzo: 2 })
    // Riga non piu' nella pagina letta: il form resta com'e'.
    r.risincronizza([{ id: 2 }])
    expect(r.rigaInModifica.value).toEqual({ id: 1, prezzo: 2 })
    expect(r.formMode.value).toBe('edit')
  })

  it('6. il cambio di documento chiude il form', async () => {
    const visible = ref(true)
    const documentoId = ref(10)
    const r = useFormInline({ padre: () => (visible.value ? documentoId.value : null) })
    r.apriRiga({ id: 1 })
    documentoId.value = 11
    await nextTick()
    expect(r.formAperto.value).toBe(false)
    expect(r.rigaInModifica.value).toBeNull()
    // Anche la chiusura del drawer: alla riapertura il form e' chiuso.
    r.nuovaRiga()
    visible.value = false
    await nextTick()
    expect(r.formAperto.value).toBe(false)
  })

  it('7. cambio di riga col form aperto: prima si chiede, poi si apre', () => {
    // 🔴 D-8: il clic su un'altra riga sostituiva il form, e le modifiche alla
    //    riga precedente si perdevano senza domanda.
    let procedi = null
    const m = useFormInline({ confermaCambio: (p) => { procedi = p } })
    const riempite = []
    m.apriRiga({ id: 1 }, (r) => riempite.push(r.id))
    m.apriRiga({ id: 2 }, (r) => riempite.push(r.id))
    // La domanda e' aperta: il form e' ancora sulla riga 1, e non e' stato
    // riempito con la 2.
    expect(m.rigaInModifica.value.id).toBe(1)
    expect(riempite).toEqual([1])
    procedi()
    expect(m.rigaInModifica.value.id).toBe(2)
    expect(riempite).toEqual([1, 2])
  })

  it('8. a form chiuso si apre subito, senza chiedere', () => {
    let chiesto = false
    const m = useFormInline({ confermaCambio: (p) => { chiesto = true; p() } })
    m.apriRiga({ id: 1 })
    expect(chiesto).toBe(false)
    expect(m.formMode.value).toBe('edit')
  })

  // Un elemento finto: conta le chiamate a `scrollIntoView` (jsdom non la ha).
  function elementoFinto() {
    return { scrollIntoView: vi.fn() }
  }

  it('9. aprire il form lo porta in vista, dopo il render', async () => {
    // 🔴 2026-10-07: il form sta sotto l'elenco, e su un elenco lungo il clic
    //    lo apriva fuori vista: sembrava non succedere nulla.
    const r = useFormInline()
    const el = elementoFinto()
    r.ancoraForm(el)
    r.nuovaRiga()
    // Non subito: il form e' in un `v-if`, va prima montato.
    expect(el.scrollIntoView).not.toHaveBeenCalled()
    await nextTick()
    expect(el.scrollIntoView).toHaveBeenCalledTimes(1)
    expect(el.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' })
    r.apriRiga({ id: 1 })
    await nextTick()
    expect(el.scrollIntoView).toHaveBeenCalledTimes(2)
  })

  it('10. chiudere, risincronizzare o cambiare padre non scorre', async () => {
    // ⛔ Lo scorrimento segue un GESTO: la pagina che scende da sola mentre
    //    l'operatore guarda altro e' il difetto opposto.
    const padre = ref(1)
    const r = useFormInline({ padre: () => padre.value })
    const el = elementoFinto()
    r.ancoraForm(el)
    r.apriRiga({ id: 1 })
    await nextTick()
    el.scrollIntoView.mockClear()
    r.risincronizza([{ id: 1, nuova: true }])
    r.chiudiForm()
    padre.value = 2
    await nextTick()
    expect(el.scrollIntoView).not.toHaveBeenCalled()
    // Senza ancora legata l'apertura non fallisce: non scorre, e basta.
    const senza = useFormInline()
    senza.nuovaRiga()
    await nextTick()
    expect(senza.formAperto.value).toBe(true)
  })

  it("11. l'ancora accetta un componente, e lo smontaggio la scioglie", async () => {
    const r = useFormInline()
    const el = elementoFinto()
    r.ancoraForm({ $el: el })
    r.nuovaRiga()
    await nextTick()
    expect(el.scrollIntoView).toHaveBeenCalledTimes(1)
    // Vue chiama la ref-funzione con `null` allo smontaggio.
    r.ancoraForm(null)
    r.apriRiga({ id: 1 })
    await nextTick()
    expect(el.scrollIntoView).toHaveBeenCalledTimes(1)
  })

  it("12. ogni contenitore della macchina lega l'ancora al suo form", () => {
    // ⛔ Un contenitore che usa la macchina e non lega l'ancora apre il form
    //    fuori vista, senza nessun errore: lo trova solo chi lo guarda.
    // ⭐ Le macchine NON si elencano a mano: si ricavano dai sorgenti. E'
    //    macchina `useFormInline` e ogni composable `.js` che ne importa una
    //    (anche di seconda mano: `useStepFigliCollection` → `useEditableCollection`
    //    → `useFormInline`). Un BB nuovo costruito sopra entra da solo; con un
    //    elenco scritto qui, i suoi contenitori restavano fuori senza errore.
    const vue = import.meta.glob(['../../**/*.vue'], {
      query: '?raw', import: 'default', eager: true,
    })
    const js = import.meta.glob(['../../**/*.js', '!../../**/*.spec.js'], {
      query: '?raw', import: 'default', eager: true,
    })
    const importa = (testo, nome) =>
      new RegExp(`import\\s*\\{[^}]*\\b${nome}\\b[^}]*\\}\\s*from`).test(testo)
    const macchine = new Set(['useFormInline'])
    for (let cresciuto = true; cresciuto;) {
      cresciuto = false
      for (const testo of Object.values(js)) {
        if (![...macchine].some((m) => importa(testo, m))) continue
        for (const [, nome] of testo.matchAll(/export function (use\w+)/g)) {
          if (!macchine.has(nome)) { macchine.add(nome); cresciuto = true }
        }
      }
    }
    // Controllo di sanita': se la ricerca si rompe, l'elenco si svuota e il
    // test passerebbe a vuoto.
    for (const attesa of ['useEditableCollection', 'useSoggettoRuoloCollection', 'useStepFigliCollection']) {
      expect(macchine).toContain(attesa)
    }
    const USO = new RegExp(`\\b(${[...macchine].join('|')})\\(`)
    const contenitori = Object.entries(vue).filter(([, testo]) => USO.test(testo))
    expect(contenitori.length).toBeGreaterThan(15)
    // Legata = `:ref` sull'ancora (anche `x.ancoraForm`), chiamata da un `watch`
    // sul ref del form, o delegata a `CollectionEditorPanel`, che la lega lui.
    const LEGATA = /:ref="(\w+\.)?ancoraForm"|\bancoraForm\(|<CollectionEditorPanel\b/
    const senzaAncora = contenitori
      .filter(([, testo]) => !LEGATA.test(testo))
      .map(([file]) => file)
    expect(senzaAncora).toEqual([])
    const pannello = Object.entries(vue).find(([f]) => f.endsWith('/CollectionEditorPanel.vue'))
    expect(pannello?.[1]).toContain(':ref="coll.ancoraForm"')
  })

  it('13. un form multi-radice scorre al suo primo elemento vero', async () => {
    // 🔴 2026-10-07: `DistintaRigaForm` e `DocumentoInternoRigaForm` hanno piu'
    //    radici, e il `$el` di un Fragment e' l'ancora di TESTO vuota che lo
    //    apre: niente `scrollIntoView`, e lo scorrimento taceva.
    const contenitore = document.createElement('div')
    const ancoraTesto = document.createTextNode('')
    const primo = document.createElement('div')
    primo.scrollIntoView = vi.fn()
    contenitore.append(ancoraTesto, primo, document.createElement('div'))
    const r = useFormInline()
    r.ancoraForm({ $el: ancoraTesto })
    r.nuovaRiga()
    await nextTick()
    expect(primo.scrollIntoView).toHaveBeenCalledTimes(1)
  })
})
