// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useDatiSocietariForm().toPayload()`: al
//        backend va SOLO cio' che il form mostra. Il recapito del canale FE
//        non scelto, e REA/capitale quando la forma non li prevede, restano
//        nel form ma non partono: il guard del DB li rifiuterebbe su un campo
//        che l'operatore non vede.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { ref } from 'vue'

import { useDatiSocietariForm } from './useDatiSocietariForm'

const FORME = [
  { id: 1, rea_policy: 'REQUIRED', capitale_sociale_policy: 'REQUIRED' },
  { id: 2, rea_policy: 'NONE', capitale_sociale_policy: 'NONE' },
]

function compila(canale, formaId = 1) {
  const ds = useDatiSocietariForm({ formeGiuridiche: ref(FORME) })
  Object.assign(ds.form, {
    forma_giuridica_id: formaId,
    id_prov_iscri_rea: 7,
    iscrizione_rea: 'RM-123',
    capitale_sociale: 10000,
    destinatario_fe: canale,
    pec_fatturazione: 'fe@pec.it',
    codice_sdi: 'ABC1234',
  })
  return ds
}

describe('useDatiSocietariForm.toPayload', () => {
  it('canale P: manda la PEC, non il codice SDI', () => {
    const p = compila('P').toPayload()
    expect(p.pec_fatturazione).toBe('fe@pec.it')
    expect(p.codice_sdi).toBe('')
  })

  it('canale C: manda il codice SDI, non la PEC', () => {
    const p = compila('C').toPayload()
    expect(p.codice_sdi).toBe('ABC1234')
    expect(p.pec_fatturazione).toBe('')
  })

  it('nessun canale: nessun recapito', () => {
    const p = compila(null).toPayload()
    expect(p.codice_sdi).toBe('')
    expect(p.pec_fatturazione).toBe('')
  })

  it('il form tiene i valori nascosti: tornando al canale si ritrovano', () => {
    const ds = compila('P')
    ds.toPayload()
    expect(ds.form.codice_sdi).toBe('ABC1234')
  })

  it('REA e capitale partono solo se la forma li prevede', () => {
    const con = compila('P', 1).toPayload()
    expect(con).toMatchObject({ id_prov_iscri_rea: 7, iscrizione_rea: 'RM-123', capitale_sociale: 10000 })
    const senza = compila('P', 2).toPayload()
    expect(senza).toMatchObject({ id_prov_iscri_rea: null, iscrizione_rea: '', capitale_sociale: null })
  })
})

describe('useDatiSocietariForm — stato intero per il verbo DB', () => {
  it('la data di costituzione si legge, si tiene e riparte', () => {
    const ds = useDatiSocietariForm({ formeGiuridiche: ref(FORME) })
    ds.populate({ forma_giuridica_id: 1, data_costituzione: '2020-03-15' })
    expect(ds.toPayload().data_costituzione).toBe('2020-03-15')
    ds.reset()
    expect(ds.toPayload().data_costituzione).toBeNull()
  })
})

// ⭐ brief-db-parametri-senza-override FE-2: socio unico e liquidazione li
// propone il DB (default con l'override dell'emittente). Il form non li scrive:
// partono NULL finche' l'operatore non sceglie.
describe('useDatiSocietariForm — i default li propone il DB', () => {
  it('form nuovo e reset: socio unico e liquidazione partono NULL', () => {
    const ds = useDatiSocietariForm({ formeGiuridiche: ref(FORME) })
    expect(ds.toPayload()).toMatchObject({ socio_unico: null, liquidazione: null })
    ds.form.socio_unico = 'SM'
    ds.reset()
    expect(ds.toPayload()).toMatchObject({ socio_unico: null, liquidazione: null })
  })

  it('in modifica restano i valori del DB, e un dato assente resta NULL', () => {
    const ds = useDatiSocietariForm({ formeGiuridiche: ref(FORME) })
    ds.populate({ forma_giuridica_id: 1, socio_unico: 'SM', liquidazione: 'LS' })
    expect(ds.toPayload()).toMatchObject({ socio_unico: 'SM', liquidazione: 'LS' })
    ds.populate({ forma_giuridica_id: 1 })
    expect(ds.toPayload()).toMatchObject({ socio_unico: null, liquidazione: null })
  })
})
