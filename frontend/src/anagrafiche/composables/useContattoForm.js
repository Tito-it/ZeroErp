// Scopo: Composable per form contatto associabile a soggetto, ruolo o utility.
// Gestisce stato reattivo, validazione e reset.
// Lookup tipo_contatto e unita_organizzativa via lookup generico config.
//
// Espone classify/isEmpty/isFilled — mirror della regola backend in
// apps/anagrafiche/services/contatti_service.py::classify_contatto_payload
// (Fase 5 refactor). Defense-in-depth UX: il backend resta la verita'.
//
// KEEP IN SYNC: TRACKED_FIELDS e REQUIRED_FIELDS sono duplicate in
// backend/apps/anagrafiche/services/contatti_service.py
// (_TRACKED_FIELDS, _REQUIRED_FIELDS). Se cambi qui aggiorna anche la'.

import { reactive } from 'vue'
import { useLookup } from '../../core/composables/useLookup'
import { isEmailValid } from '../../core/utils/validators'
import { fetchLookupCodici } from '../../core/composables/useLookupCodici'

// Campi che indicano "l'utente ha iniziato a compilare il contatto".
const TRACKED_FIELDS = ['nominativo', 'email', 'telefono', 'cellulare', 'pec', 'tipo_contatto_id']

// Campi obbligatori per considerare il contatto "valido" e creabile.
// Allineati con NOT NULL DB su anagrafiche.contatti.
const REQUIRED_FIELDS = ['nominativo', 'tipo_contatto_id']

// Mapping nome campo backend → chiave i18n usata da ContattoForm per
// mostrare l'errore. Centralizzato qui per non duplicare in validate().
const REQUIRED_I18N_KEY = {
  nominativo: 'nominativo',
  tipo_contatto_id: 'tipo_contatto',
}

// Helper: un valore e' "valorizzato" semanticamente.
function _isFilled(value) {
  if (value == null) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (typeof value === 'number') return value > 0  // tipo_contatto_id: 0 = non valido
  return Boolean(value)
}

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

  // Scopo: Ritorna 'EMPTY' | 'PARTIAL' | 'VALID' (mirror backend).
  // Usato per decidere se inviare il blocco contatto nel payload e per
  // disabilitare il pulsante Salva nel caller.
  function classify() {
    const anyFilled = TRACKED_FIELDS.some(f => _isFilled(form[f]))
    if (!anyFilled) return 'EMPTY'
    const allRequired = REQUIRED_FIELDS.every(f => _isFilled(form[f]))
    return allRequired ? 'VALID' : 'PARTIAL'
  }

  // Scopo: True se nessun campo e' valorizzato.
  function isEmpty() { return classify() === 'EMPTY' }

  // Scopo: True se almeno un campo e' valorizzato (compilato o in corso).
  function isFilled() { return !isEmpty() }

  // Lookup tipi contatto (config.tipi_contatti) — caricato al mount
  const tipiContatto = useLookup(
    fetchLookupCodici('config.tipi_contatti'),
    { immediate: true }
  )

  // Lookup unita organizzative (config.unita_organizzative) — lazy
  const unitaOrganizzative = useLookup(
    fetchLookupCodici('config.unita_organizzative')
  )

  // Scopo: Validazione campi contatto (presenza obbligatori + formato email/pec).
  // Riusa REQUIRED_FIELDS + _isFilled per coerenza con classify().
  function validate() {
    const errors = []
    for (const f of REQUIRED_FIELDS) {
      if (!_isFilled(form[f])) errors.push(REQUIRED_I18N_KEY[f] || f)
    }
    if (requireEmail && !_isFilled(form.email)) errors.push('email')
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
    populate,
    classify,
    isEmpty,
    isFilled,
  }
}
