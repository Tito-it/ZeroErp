// Scopo: Composable per form conto bancario associabile a soggetto o ruolo.
// Gestisce stato reattivo, validazione, reset, populate e toPayload.
// IBAN e filiale salvati come _obj per restore autocomplete server-side.

import { reactive, ref } from 'vue'
import { toDateString } from '../utils/date'

const _USI = ['INCASSO', 'PAGAMENTO', 'RIMBORSO', 'GENERICO']

export function useContoBancarioForm() {
  const form = reactive({
    iban: '',
    iban_obj: null,          // oggetto dal registro (per restore autocomplete)
    bic_swift: '',
    bank_branch_id: null,
    bank_branch_obj: null,   // oggetto filiale (per restore autocomplete)
    intestatario_predefinito: '',
    uso: 'GENERICO',
    predefinito: false,
    valido_dal: null,
    valido_al: null,
    intestazione_dichiarata: '',
    verificato: false,
    bloccato: false
  })

  // ID conto bancario gia' esistente nel registro (set da autocomplete select)
  const contoRegistroId = ref(null)

  // Lista usi disponibili (per dropdown)
  const usiDisponibili = _USI

  // Scopo: Validazione campi obbligatori e formato.
  function validate() {
    const errors = []
    const iban = (form.iban || '').trim()
    if (!iban) {
      errors.push('iban')
    } else if (!/^[A-Z0-9]{15,34}$/.test(iban)) {
      errors.push('iban_format')
    }
    if (!form.bank_branch_id) errors.push('bank_branch_id')
    if (!form.uso) errors.push('uso')
    // ⚠️ L'ordine delle date NON si giudica qui: lo giudica il guard comune del
    // database (E_DATA_AL_MINORE_DAL, dal 2026-09-23), che arriva col campo
    // `valido_al` in `campiErrati` e con la soluzione nel toast.
    return errors
  }

  // Scopo: Reset form ai valori iniziali. ownerName pre-popola intestatario.
  function reset(ownerName = '') {
    form.iban = ''
    form.iban_obj = null
    form.bic_swift = ''
    form.bank_branch_id = null
    form.bank_branch_obj = null
    form.intestatario_predefinito = ownerName
    form.uso = 'GENERICO'
    form.predefinito = false
    form.valido_dal = new Date()
    form.valido_al = null
    form.intestazione_dichiarata = ''
    form.verificato = false
    form.bloccato = false
    contoRegistroId.value = null
  }

  // Scopo: Popola il form con dati API (per edit mode).
  function populate(data) {
    form.iban = data.iban || ''
    form.iban_obj = data.iban ? { id: data.conto_bancario_id, iban: data.iban } : null
    form.bic_swift = data.bic_swift || ''
    form.bank_branch_id = data.bank_branch_id ?? null
    form.bank_branch_obj = data.bank_branch_id
      ? { id: data.bank_branch_id, filiale_nome: data.filiale_nome || '' }
      : null
    form.intestatario_predefinito = data.intestatario_predefinito || ''
    form.uso = data.uso || 'GENERICO'
    form.predefinito = data.predefinito ?? false
    form.valido_dal = data.valido_dal ? new Date(data.valido_dal) : null
    form.valido_al = data.valido_al ? new Date(data.valido_al) : null
    form.intestazione_dichiarata = data.intestazione_dichiarata || ''
    form.verificato = data.verificato ?? false
    form.bloccato = data.bloccato ?? false
    contoRegistroId.value = data.conto_bancario_id ?? null
  }

  // Scopo: Costruisce payload per POST (create).
  function toCreatePayload() {
    const p = {
      uso: form.uso,
      predefinito: form.predefinito,
      intestazione_dichiarata: form.intestazione_dichiarata.trim() || null,
      verificato: form.verificato,
      bloccato: form.bloccato,
      valido_dal: toDateString(form.valido_dal),
      valido_al: toDateString(form.valido_al)
    }
    // Se l'IBAN esiste nel registro, usa conto_bancario_id diretto
    if (contoRegistroId.value) {
      p.conto_bancario_id = contoRegistroId.value
    } else {
      p.iban = form.iban.trim()
      p.bic_swift = form.bic_swift.trim() || null
      p.bank_branch_id = form.bank_branch_id
      p.intestatario_predefinito = form.intestatario_predefinito.trim() || null
    }
    return p
  }

  // Scopo: Costruisce payload per PATCH (update) — solo campi legame.
  function toUpdatePayload() {
    return {
      uso: form.uso,
      predefinito: form.predefinito,
      intestazione_dichiarata: form.intestazione_dichiarata.trim() || null,
      verificato: form.verificato,
      bloccato: form.bloccato,
      valido_dal: toDateString(form.valido_dal),
      valido_al: toDateString(form.valido_al)
    }
  }

  // Scopo: Callback quando l'utente seleziona un IBAN dall'autocomplete.
  //        Pre-popola BIC, filiale, intestatario dal registro.
  function onIbanSelect(item) {
    if (!item) return
    contoRegistroId.value = item.id
    form.iban = item.iban || ''
    form.iban_obj = item
    form.bic_swift = item.bic_swift || ''
    if (item.bank_branch_id) {
      form.bank_branch_id = item.bank_branch_id
      form.bank_branch_obj = {
        id: item.bank_branch_id,
        filiale_nome: item.filiale_nome || ''
      }
    }
    form.intestatario_predefinito = item.intestatario_predefinito || ''
  }

  // Scopo: Callback quando l'utente digita un IBAN libero (non da autocomplete).
  //        Resetta il riferimento al registro.
  function onIbanClear() {
    contoRegistroId.value = null
    form.iban_obj = null
  }

  // Scopo: Callback quando l'utente seleziona una filiale dall'autocomplete.
  function onBranchSelect(item) {
    if (!item) return
    form.bank_branch_id = item.id
    form.bank_branch_obj = item
    if (item.bic_swift && !form.bic_swift) {
      form.bic_swift = item.bic_swift
    }
  }

  return {
    form,
    contoRegistroId,
    usiDisponibili,
    validate,
    reset,
    populate,
    toCreatePayload,
    toUpdatePayload,
    onIbanSelect,
    onIbanClear,
    onBranchSelect
  }
}
