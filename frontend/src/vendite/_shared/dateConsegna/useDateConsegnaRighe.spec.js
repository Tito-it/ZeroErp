// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: l'azione «Aggiorna date di consegna» della barra del drawer
//        (brief-db-date-consegna-righe-in-blocco D-3, BF-3): quali colonne
//        propone, e quando il pulsante e' acceso, spento col motivo o assente.
//
// Indice test:
//  1) una colonna attiva: azione accesa, proposta la sola colonna attiva
//  2) nessuna colonna attiva, con un motivo: azione spenta col motivo
//  3) nessuna colonna attiva, senza motivo: l'azione non compare
//  4) readonly puro: l'azione non compare, anche con colonne attive
//  5) documento non ancora letto: l'azione non compare
//  6) il comando apre il dialog
//  7) documento senza righe: azione spenta col motivo «nessuna riga»
// ------------------------------------------------------------
import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (chiave) => chiave }) }))

const { useDateConsegnaRighe } = await import('./useDateConsegnaRighe')

function crea({ richiesta = false, confermata = false, motivo = null, readonly = false, presente = true, righe = 1 } = {}) {
  const ro = ref(readonly)
  const pr = ref(presente)
  const uso = useDateConsegnaRighe({
    colonne: [
      { colonna: 'data_consegna_richiesta_cliente', labelKey: 'r', attiva: () => richiesta },
      { colonna: 'data_consegna_confermata', labelKey: 'c', attiva: () => confermata, motivo: () => motivo },
    ],
    readonlyPuro: () => ro.value,
    presente: pr,
    righe: () => righe,
  })
  return uso
}

describe('useDateConsegnaRighe', () => {
  it('una colonna attiva: azione accesa, proposta la sola colonna attiva', () => {
    const uso = crea({ confermata: true, motivo: 'non conta' })
    expect(uso.colonneAttive.value).toEqual([{ colonna: 'data_consegna_confermata', label: 'c' }])
    expect(uso.azione.value).toHaveLength(1)
    expect(uso.azione.value[0].disabled).toBe(false)
    expect(uso.azione.value[0].tooltip).toBeUndefined()
  })

  it('nessuna colonna attiva, con un motivo: azione spenta col motivo', () => {
    const uso = crea({ motivo: 'In questo stato non si cambia' })
    expect(uso.azione.value[0].disabled).toBe(true)
    expect(uso.azione.value[0].tooltip).toBe('In questo stato non si cambia')
  })

  it('nessuna colonna attiva, senza motivo: l\'azione non compare', () => {
    expect(crea().azione.value).toEqual([])
  })

  it('readonly puro: l\'azione non compare', () => {
    expect(crea({ richiesta: true, readonly: true }).azione.value).toEqual([])
  })

  it('documento non ancora letto: l\'azione non compare', () => {
    expect(crea({ richiesta: true, presente: false }).azione.value).toEqual([])
  })

  it('il comando apre il dialog', () => {
    const uso = crea({ richiesta: true })
    uso.azione.value[0].command()
    expect(uso.dialogVisible.value).toBe(true)
  })

  it('documento senza righe: azione spenta col motivo «nessuna riga»', () => {
    const uso = crea({ richiesta: true, righe: 0 })
    expect(uso.azione.value[0].disabled).toBe(true)
    expect(uso.azione.value[0].tooltip).toBe('vendite.date_consegna.nessuna_riga')
  })
})
