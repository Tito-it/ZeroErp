// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
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
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'
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
})
