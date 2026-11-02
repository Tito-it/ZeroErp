// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useEntityCapabilities` — il BB da cui SETTE
//        drawer di vendite leggono il blob capability. Scritto il 2026-09-23
//        con la conversione alla forma annidata
//        (brief-be-fe-capability-annidata): il blob sta SOTTO
//        `detail.capabilities` (api.md §«Il blob sta SOTTO `capabilities`»).
//
// 🔴 Il test che conta e' il 2: un dettaglio nella forma VECCHIA (blob fuso
//    nella testata) deve dare un drawer SPENTO, non acceso. Il BB non ha un
//    ponte verso la forma piatta, ed e' voluto: un ponte sarebbe il posto dove
//    la forma vecchia sopravvive in silenzio, e un campo omonimo della testata
//    (`can_x` come colonna) accenderebbe un pulsante che il database non ha
//    concesso.
//
// ⚠️ Cio' che NON copre: il cablaggio del singolo drawer (quale campo legge
//    fuori dal BB) — lo presidia `npm run guard:capability`, che conta anche
//    le letture piatte.
//
// Indice test:
//   1) legge flag, azioni e campi bloccati da `detail.capabilities`
//   2) la forma piatta NON viene letta: tutto spento (fail-closed)
//   3) detail null (create) o blob vuoto (capability layer rotto) -> spento
//   4) `editFlag` sceglie il flag di editabilita' (promo: `can_update`)
//   5) un'azione senza `label_key` non arriva al template
//   6) `capabilities` espone il blob per motivi e chiavi i18n
//   7) `azioneNegata`: flag spento + motivo -> entry disabled con il motivo
//   8) `azioneNegata`: flag acceso, o spento SENZA motivo -> nessuna entry
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useEntityCapabilities } from './useEntityCapabilities'

const BLOB = {
  available_actions: [{ key: 'conferma', label_key: 'vendite.azione_conferma' }],
  can_edit_testata: true,
  can_edit_righe: false,
  can_push_commessa: false,
  can_push_commessa_reason_key: 'vendite.push_commessa_reason.fattura_da_ordine',
  non_editable_fields: ['utility_id'],
}

describe('useEntityCapabilities', () => {
  it('1) legge flag, azioni e campi bloccati da detail.capabilities', () => {
    const caps = useEntityCapabilities(ref({ id: 7, capabilities: BLOB }))
    expect(caps.availableActions.value.map((a) => a.key)).toEqual(['conferma'])
    expect(caps.canEdit.value).toBe(true)
    expect(caps.flag('can_edit_righe')).toBe(false)
    expect(caps.isLocked('utility_id')).toBe(true)
    expect(caps.isLocked('descrizione')).toBe(false)
  })

  it('2) la forma piatta NON viene letta: tutto spento', () => {
    const caps = useEntityCapabilities(ref({ id: 7, ...BLOB }))
    expect(caps.availableActions.value).toEqual([])
    expect(caps.canEdit.value).toBe(false)
    expect(caps.nonEditableFields.value.size).toBe(0)
    expect(caps.isLocked('descrizione')).toBe(true)
  })

  it('3) detail null o blob vuoto -> spento', () => {
    for (const detail of [null, { id: 7, capabilities: {} }, { id: 7 }]) {
      const caps = useEntityCapabilities(ref(detail))
      expect(caps.capabilities.value).toEqual({})
      expect(caps.availableActions.value).toEqual([])
      expect(caps.canEdit.value).toBe(false)
    }
  })

  it('4) editFlag sceglie il flag di editabilita', () => {
    const detail = ref({ capabilities: { can_update: true, can_edit_testata: false } })
    expect(useEntityCapabilities(detail, { editFlag: 'can_update' }).canEdit.value).toBe(true)
    expect(useEntityCapabilities(detail).canEdit.value).toBe(false)
  })

  it('5) un\'azione senza label_key non arriva al template', () => {
    const caps = useEntityCapabilities(ref({
      capabilities: { available_actions: [{ key: 'a', label_key: 'k.a' }, { key: 'b' }, null] },
    }))
    expect(caps.availableActions.value.map((a) => a.key)).toEqual(['a'])
  })

  it('6) capabilities espone il blob, ed e reattivo', () => {
    const detail = ref({ capabilities: BLOB })
    const caps = useEntityCapabilities(detail)
    expect(caps.capabilities.value.can_push_commessa_reason_key)
      .toBe('vendite.push_commessa_reason.fattura_da_ordine')
    detail.value = { capabilities: { ...BLOB, can_edit_testata: false } }
    expect(caps.canEdit.value).toBe(false)
  })

  it('7) azioneNegata: flag spento + motivo -> entry disabled', () => {
    const caps = useEntityCapabilities(ref({ capabilities: BLOB }))
    const [azione, ...resto] = caps.azioneNegata('can_push_commessa', {
      key: 'push_commessa', label_key: 'vendite.ddt.azione_push_commessa', icon: 'pi pi-x',
    })
    expect(resto).toEqual([])
    expect(azione).toMatchObject({
      key: 'push_commessa',
      label_key: 'vendite.ddt.azione_push_commessa',
      target_state: null,
      enabled: false,
      reason: null,
      reason_key: 'vendite.push_commessa_reason.fattura_da_ordine',
    })
    // Il chiamante non puo' riaccenderla passando `enabled` nella forma.
    const [forzata] = caps.azioneNegata('can_push_commessa', { key: 'x', enabled: true })
    expect(forzata.enabled).toBe(false)
  })

  it('8) azioneNegata: flag acceso o senza motivo -> nessuna entry', () => {
    const acceso = useEntityCapabilities(ref({ capabilities: { ...BLOB, can_push_commessa: true } }))
    expect(acceso.azioneNegata('can_push_commessa', { key: 'push_commessa' })).toEqual([])
    const muto = useEntityCapabilities(ref({ capabilities: { can_push_commessa: false } }))
    expect(muto.azioneNegata('can_push_commessa', { key: 'push_commessa' })).toEqual([])
    expect(useEntityCapabilities(ref(null)).azioneNegata('can_push_commessa', {})).toEqual([])
  })
})
