// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto dei filtri per le superfici SENZA store-lista — la
//        sede unica «chiave, `rif` e default sulla stessa riga», il segno e
//        «Pulisci filtri».
// Note: i casi sono quelli che, sbagliati, NON danno errore: un segno spento su
//       una superficie che filtra, un numero blu dove andava grigio, un
//       «Pulisci» che riporta il valore sbagliato.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { computed, ref } from 'vue'

import { useContrattoFiltriLocali } from './useContrattoFiltriLocali'
import { SEGNO_DEFAULT, SEGNO_MODIFICATO, SEGNO_VUOTO } from '../utils/segnoFiltri'

describe('useContrattoFiltriLocali', () => {
  it('il DEFAULT e- quello DICHIARATO, non il valore corrente del `rif`', () => {
    // Il caso vero: un `ref` di uno store `userScoped` sopravvive al
    // componente, quindi al secondo montaggio porta gia' il filtro di prima.
    const ritardo = ref(30)
    const { risolviFiltriDefault, segno } = useContrattoFiltriLocali({
      ritardo_giorni: { rif: ritardo, default: null },
    })
    expect(risolviFiltriDefault()).toEqual({ ritardo_giorni: null })
    // 30 non e' il default: il numero si vede BLU, non grigio.
    expect(segno.value).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 1, modificato: true })
  })

  it('un default VALORIZZATO nasce GRIGIO, e al primo cambio diventa blu', () => {
    const ampiezza = ref('RILEVANTI')
    const { segno } = useContrattoFiltriLocali({
      ampiezza: { rif: ampiezza, default: 'RILEVANTI' },
    })
    expect(segno.value).toEqual({ stato: SEGNO_DEFAULT, conteggio: 1, modificato: false })
    ampiezza.value = 'TUTTI'
    expect(segno.value).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 1, modificato: true })
  })

  it('conta TUTTI i filtri con valore, default compresi (D4)', () => {
    const a = ref(null)
    const b = ref('X')
    const { segno } = useContrattoFiltriLocali({
      a: { rif: a, default: null },
      b: { rif: b, default: 'X' },
    })
    expect(segno.value).toEqual({ stato: SEGNO_DEFAULT, conteggio: 1, modificato: false })
    a.value = 'Y'
    expect(segno.value).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 2, modificato: true })
  })

  it('nessun filtro con valore = nessun segno', () => {
    const { segno } = useContrattoFiltriLocali({
      a: { rif: ref(null), default: null },
      b: { rif: ref(''), default: null },
    })
    expect(segno.value).toEqual({ stato: SEGNO_VUOTO, conteggio: 0, modificato: false })
  })

  it('«Pulisci» riporta i filtri al default e chiama `onAzzera` UNA volta', () => {
    const ritardo = ref(null)
    const area = ref(null)
    let n = 0
    const { azzeraFiltri } = useContrattoFiltriLocali(
      { ritardo: { rif: ritardo, default: null }, area: { rif: area, default: null } },
      { onAzzera: () => { n += 1; return 'ricaricata' } },
    )
    ritardo.value = 30
    area.value = 'ENERGIA'
    expect(azzeraFiltri()).toBe('ricaricata')
    expect(ritardo.value).toBe(null)
    expect(area.value).toBe(null)
    expect(n).toBe(1)
  })

  it('«Pulisci» su un default valorizzato torna al suo valore, non a null', () => {
    const livello = ref('C')
    const { azzeraFiltri, segno } = useContrattoFiltriLocali({
      livello: { rif: livello, default: 'C' },
    })
    livello.value = 'W'
    expect(segno.value.stato).toBe(SEGNO_MODIFICATO)
    azzeraFiltri()
    expect(livello.value).toBe('C')
    expect(segno.value.stato).toBe(SEGNO_DEFAULT)
  })

  it('senza `onAzzera` non esplode: certe superfici ricaricano da un watch', () => {
    const v = ref('A')
    const { azzeraFiltri } = useContrattoFiltriLocali({ v: { rif: v, default: 'A' } })
    v.value = 'B'
    expect(() => azzeraFiltri()).not.toThrow()
    expect(v.value).toBe('A')
  })

  // ⛔ Il caso del giornale lotto: «mostra tutto» ALLARGA. Contare la variabile
  //    del widget direbbe «1 filtro attivo» proprio quando non ne filtra nessuno.
  it('accetta un `computed` SCRIVIBILE: il filtro vero puo- essere l-opposto del widget', () => {
    const mostraTutto = ref(false)
    const soloProblemi = computed({
      get: () => (mostraTutto.value ? null : true),
      set: (v) => { mostraTutto.value = v == null },
    })
    const { segno, azzeraFiltri } = useContrattoFiltriLocali({
      solo_problemi: { rif: soloProblemi, default: true },
    })
    expect(segno.value).toEqual({ stato: SEGNO_DEFAULT, conteggio: 1, modificato: false })
    mostraTutto.value = true
    expect(segno.value).toEqual({ stato: SEGNO_VUOTO, conteggio: 0, modificato: true })
    azzeraFiltri()
    expect(mostraTutto.value).toBe(false)
  })

  // ⚠️ Stessa ragione di `useContrattoFiltriLista`: il default e' il metro, e un
  //    metro che si muove con la cosa misurata non misura piu' niente.
  it('una `Date` di default e- STACCATA: mutare il filtro vivo non la sposta', () => {
    const oggi = new Date('2026-09-23T00:00:00')
    const validoAl = ref(new Date(oggi.getTime()))
    const { risolviFiltriDefault, segno } = useContrattoFiltriLocali({
      valido_al: { rif: validoAl, default: oggi },
    })
    expect(risolviFiltriDefault().valido_al).not.toBe(oggi)
    expect(segno.value.stato).toBe(SEGNO_DEFAULT)
    validoAl.value.setFullYear(2030)
    expect(risolviFiltriDefault().valido_al.getFullYear()).toBe(2026)
  })

  it('un default ad ARRAY e- staccato, e «Pulisci» ne riconsegna una copia', () => {
    const DEFAULT = ['APERTA']
    const stati = ref(['APERTA'])
    const { risolviFiltriDefault, azzeraFiltri } = useContrattoFiltriLocali({
      stati: { rif: stati, default: DEFAULT },
    })
    stati.value = ['CHIUSA', 'ANNULLATA']
    azzeraFiltri()
    expect(stati.value).toEqual(['APERTA'])
    stati.value.push('CHIUSA')
    expect(risolviFiltriDefault().stati).toEqual(['APERTA'])
    expect(DEFAULT).toEqual(['APERTA'])
  })

  it('una voce senza `rif` lo GRIDA in console invece di contare il vuoto', () => {
    const spia = vi.spyOn(console, 'error').mockImplementation(() => {})
    useContrattoFiltriLocali({ stato: { default: null } })
    expect(spia).toHaveBeenCalledOnce()
    expect(spia.mock.calls[0][0]).toContain('stato')
    spia.mockRestore()
  })

  // ⭐ «oggi» non e' un valore, e' una domanda: il drawer BoM nasce sul giorno
  //    corrente, e un metro fotografato una volta sola sballerebbe a cavallo
  //    della mezzanotte. Spegnendo la risoluzione a ogni giro questo test va
  //    rosso in tre punti.
  it('un default a FUNZIONE si risolve ogni volta, non si fotografa', () => {
    let giorno = '2026-09-23'
    const validoAl = ref(giorno)
    const { segno, azzeraFiltri, risolviFiltriDefault } = useContrattoFiltriLocali({
      valido_al: { rif: validoAl, default: () => giorno },
    })
    expect(risolviFiltriDefault()).toEqual({ valido_al: '2026-09-23' })
    expect(segno.value.stato).toBe(SEGNO_DEFAULT)

    // Passa la mezzanotte: il metro si sposta, il filtro no.
    giorno = '2026-09-24'
    expect(risolviFiltriDefault()).toEqual({ valido_al: '2026-09-24' })
    // ⚠️ Il segno si ricalcola quando cambia un FILTRO, non quando cambia il
    //    giorno: finche' l'operatore non tocca niente a video non cambia niente,
    //    ed e' giusto cosi'. Al primo tocco legge il metro nuovo.
    validoAl.value = '2026-09-22'
    expect(segno.value.stato).toBe(SEGNO_MODIFICATO)

    // «Pulisci» atterra sul giorno di OGGI, non su quello della nascita.
    azzeraFiltri()
    expect(validoAl.value).toBe('2026-09-24')
    expect(segno.value.stato).toBe(SEGNO_DEFAULT)
  })

  it('senza filtri dichiarati non ha chiavi, e azzerare non rompe', () => {
    const { chiaviFiltro, segno, azzeraFiltri } = useContrattoFiltriLocali({})
    expect([...chiaviFiltro]).toEqual([])
    expect(segno.value.stato).toBe(SEGNO_VUOTO)
    expect(() => azzeraFiltri()).not.toThrow()
  })

  // ⛔ Il gemello di `filtriNeutri` sugli store-lista: l'ampiezza «TUTTI» dei
  //    task del lotto non filtra niente (`AMPIEZZE_TASK.TUTTI === null`).
  it('un `neutro` dichiarato non conta, e non spegne `modificato`', () => {
    const ampiezza = ref('RILEVANTI')
    const { segno } = useContrattoFiltriLocali({
      ampiezza: { rif: ampiezza, default: 'RILEVANTI', neutro: 'TUTTI' },
    })
    expect(segno.value).toEqual({ stato: SEGNO_DEFAULT, conteggio: 1, modificato: false })
    ampiezza.value = 'ERRORI'
    expect(segno.value).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 1, modificato: true })
    // «TUTTI»: non restringe piu' niente, quindi nessun segno — ma `modificato`
    // resta vero, ed e' cio' che tiene vivo «Pulisci filtri».
    ampiezza.value = 'TUTTI'
    expect(segno.value).toEqual({ stato: SEGNO_VUOTO, conteggio: 0, modificato: true })
  })

  // ⛔ Il neutro e' un METRO come il default, e si stacca allo stesso modo: con
  //    `Object.freeze` di primo livello un neutro ad array resterebbe LO STESSO
  //    array del letterale del chiamante. Simmetrico al gemello sugli
  //    store-lista, dove il neutro passa gia' da `clonaFiltri`.
  it('un `neutro` ad ARRAY e- staccato dal letterale e congelato', () => {
    const NEUTRO = []
    const stati = ref(['APERTA'])
    const { filtriNeutri } = useContrattoFiltriLocali({
      stati: { rif: stati, default: ['APERTA'], neutro: NEUTRO },
    })
    expect(filtriNeutri.stati).not.toBe(NEUTRO)
    expect(Object.isFrozen(filtriNeutri)).toBe(true)
    expect(() => { filtriNeutri.stati.push('CHIUSA') }).toThrow()
  })
})
