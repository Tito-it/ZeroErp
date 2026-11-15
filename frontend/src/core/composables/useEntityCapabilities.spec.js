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
//   9) `azioneDaFlag`: acceso -> pulsante attivo; spento col motivo ->
//      disabilitato col motivo tradotto; chiave mancante -> la frase del DB
//  10) `azioneDaFlag`: spento SENZA motivo, o capability vuota -> niente
//  11) ⭐ `<flag>_reason_valori` riempie i segnaposti della frase, nel tooltip
//      di `azioneDaFlag` e nell'entry di `azioneNegata` (FE-G1); assente -> []
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

  // t/te finti: una sola chiave conosciuta.
  const NOTE = { 'vendite.ddt.genera_reso_reason.non_consegnato': 'Solo da una bolla consegnata.' }
  const i18n = { t: (k) => NOTE[k] ?? k, te: (k) => k in NOTE }
  const AZIONE = { key: 'genera-reso', kind: 'manage', label: 'Genera reso', command: () => {} }

  it('9) azioneDaFlag: acceso attivo, spento col motivo disabilitato', () => {
    const acceso = useEntityCapabilities(ref({ capabilities: { can_genera_reso: true } }))
    expect(acceso.azioneDaFlag('can_genera_reso', AZIONE, i18n)).toEqual([{ ...AZIONE, disabled: false }])

    const spento = useEntityCapabilities(ref({ capabilities: {
      can_genera_reso: false,
      can_genera_reso_reason: 'DDT_NON_CONSEGNATO',
      can_genera_reso_reason_key: 'vendite.ddt.genera_reso_reason.non_consegnato',
    } }))
    const [azione, ...resto] = spento.azioneDaFlag('can_genera_reso', AZIONE, i18n)
    expect(resto).toEqual([])
    expect(azione).toMatchObject({ key: 'genera-reso', disabled: true, tooltip: 'Solo da una bolla consegnata.' })
    // Il chiamante non puo' riaccenderlo passando `disabled` nella forma.
    const [forzata] = spento.azioneDaFlag('can_genera_reso', { ...AZIONE, disabled: false }, i18n)
    expect(forzata.disabled).toBe(true)

    const ignota = useEntityCapabilities(ref({ capabilities: {
      can_genera_reso: false, can_genera_reso_reason: 'Frase del DB', can_genera_reso_reason_key: 'chiave.assente',
    } }))
    expect(ignota.azioneDaFlag('can_genera_reso', AZIONE, i18n)[0].tooltip).toBe('Frase del DB')
  })

  it('10) azioneDaFlag: spento senza motivo, o capability vuota -> niente', () => {
    const muto = useEntityCapabilities(ref({ capabilities: { can_genera_reso: false } }))
    expect(muto.azioneDaFlag('can_genera_reso', AZIONE, i18n)).toEqual([])
    expect(useEntityCapabilities(ref(null)).azioneDaFlag('can_genera_reso', AZIONE, i18n)).toEqual([])
  })

  it('11) i valori del motivo riempiono la frase', () => {
    const FRASI = { 'vendite.ddt.genera_reso_reason.trasferimento': 'La bolla {0} e\' un trasferimento.' }
    const conParametri = {
      t: (k, p) => (FRASI[k] ?? k).replace(/\{(\d+)\}/g, (_, i) => p?.[i] ?? `{${i}}`),
      te: (k) => k in FRASI,
    }
    const caps = useEntityCapabilities(ref({ capabilities: {
      can_genera_reso: false,
      can_genera_reso_reason: 'DDT_TRASFERIMENTO',
      can_genera_reso_reason_key: 'vendite.ddt.genera_reso_reason.trasferimento',
      can_genera_reso_reason_valori: ['DDT0042'],
    } }))
    expect(caps.azioneDaFlag('can_genera_reso', AZIONE, conParametri)[0].tooltip)
      .toBe("La bolla DDT0042 e' un trasferimento.")
    const [negata] = caps.azioneNegata('can_genera_reso', { key: 'genera_reso' })
    expect(negata.valori).toEqual(['DDT0042'])
    expect(caps.motivoFlag('can_genera_reso')).toEqual({
      reason: 'DDT_TRASFERIMENTO',
      reason_key: 'vendite.ddt.genera_reso_reason.trasferimento',
      valori: ['DDT0042'],
    })
    // Senza la chiave dei valori: lista vuota, mai undefined.
    const senza = useEntityCapabilities(ref({ capabilities: { can_x: false, can_x_reason_key: 'k' } }))
    expect(senza.motivoFlag('can_x').valori).toEqual([])
    expect(senza.motivoFlag('can_y')).toBeNull()
  })
})
