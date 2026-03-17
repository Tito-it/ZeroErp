// Scopo: Composable per form contatto associabile a soggetto, ruolo o utility.
// Gestisce stato reattivo, validazione e reset.
// Lookup tipo_contatto e unita_organizzativa via lookup generico config.

import { reactive } from 'vue'
import { useLookup } from './useLookup'
import { lookupCodici } from '../apiCore'
import { isEmailValid } from '../utils/validators'

export function useContattoForm(options = {}) {
  const { requireEmail = false } = options

  const form = reactive({
    nominativo: '',
    email: '',
    telefono: '',
    cellulare: '',
    pec: '',
    tipo_contatto_id: null,
    unita_organizzativa_id: null,
    note: ''
  })

  // Lookup tipi contatto (config.tipi_contatti) — lazy, caricato al primo uso
  const tipiContatto = useLookup(
    () => lookupCodici('config.tipi_contatti')
  )

  // Lookup unita organizzative (config.unita_organizzative) — lazy
  const unitaOrganizzative = useLookup(
    () => lookupCodici('config.unita_organizzative')
  )

  // Scopo: Validazione campi contatto (presenza + formato email/pec).
  function validate() {
    const errors = []
    if (!form.nominativo.trim()) errors.push('nominativo')
    if (requireEmail && !form.email.trim()) errors.push('email')
    // Validazione formato email (solo se compilato)
    if (form.email.trim() && !isEmailValid(form.email)) errors.push('email_format')
    // Validazione formato PEC (stesso formato email, solo se compilato)
    if (form.pec.trim() && !isEmailValid(form.pec)) errors.push('pec_format')
    return errors
  }

  // Scopo: Reset form ai valori iniziali.
  function reset() {
    form.nominativo = ''
    form.email = ''
    form.telefono = ''
    form.cellulare = ''
    form.pec = ''
    form.tipo_contatto_id = null
    form.unita_organizzativa_id = null
    form.note = ''
  }

  // Scopo: Popola il form con dati esistenti (per edit mode).
  function populate(data) {
    form.nominativo = data.nominativo || ''
    form.email = data.email || ''
    form.telefono = data.telefono || ''
    form.cellulare = data.cellulare || ''
    form.pec = data.pec || ''
    form.tipo_contatto_id = data.tipo_contatto_id ?? null
    form.unita_organizzativa_id = data.unita_organizzativa_id ?? null
    form.note = data.note || ''
  }

  return {
    form,
    tipiContatto,
    unitaOrganizzative,
    validate,
    reset,
    populate
  }
}
