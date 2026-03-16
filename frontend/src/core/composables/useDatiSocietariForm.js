// Scopo: Composable per form dati societari/camerali (PG/ENC).
// Gestisce forma giuridica, REA (provincia + iscrizione), capitale sociale,
// socio unico, liquidazione, destinatario FE (PEC/SDI).
// Visibilita' condizionale basata su rea_policy e capitale_sociale_policy
// della forma giuridica selezionata.

import { reactive, computed } from 'vue'

/**
 * @param {Object} options
 * @param {import('vue').Ref<Array>} options.formeGiuridiche - lista forme giuridiche
 *   con id, codice, descrizione, rea_policy, capitale_sociale_policy.
 *   Passata dal parent (pre-filtrata per tipo_soggetto_dettaglio_id).
 */
export function useDatiSocietariForm(options = {}) {
  const { formeGiuridiche = { value: [] } } = options

  const form = reactive({
    forma_giuridica_id: null,
    // REA
    id_prov_iscri_rea: null,
    iscrizione_rea: '',
    capitale_sociale: null,
    // Enumerati
    socio_unico: 'SU',
    liquidazione: 'LN',
    // Fatturazione elettronica
    destinatario_fe: null,
    pec_fatturazione: '',
    codice_sdi: ''
  })

  // Forma giuridica corrente selezionata
  const formaCorrente = computed(() =>
    formeGiuridiche.value.find(f => f.id === form.forma_giuridica_id) || null
  )

  // Policy REA
  const showRea = computed(() => {
    const p = formaCorrente.value?.rea_policy
    return p === 'REQUIRED' || p === 'OPTIONAL'
  })
  const requireRea = computed(() =>
    formaCorrente.value?.rea_policy === 'REQUIRED'
  )

  // Policy capitale sociale
  const showCapitaleSociale = computed(() => {
    const p = formaCorrente.value?.capitale_sociale_policy
    return p === 'REQUIRED' || p === 'OPTIONAL'
  })
  const requireCapitaleSociale = computed(() =>
    formaCorrente.value?.capitale_sociale_policy === 'REQUIRED'
  )

  // Scopo: Validazione campi in base alle policy della forma selezionata.
  function validate() {
    const errors = []
    if (!form.forma_giuridica_id) errors.push('forma_giuridica_id')
    if (requireRea.value) {
      if (!form.id_prov_iscri_rea) errors.push('id_prov_iscri_rea')
      if (!form.iscrizione_rea.trim()) errors.push('iscrizione_rea')
    }
    if (requireCapitaleSociale.value && form.capitale_sociale == null) {
      errors.push('capitale_sociale')
    }
    return errors
  }

  // Scopo: Reset form ai valori iniziali.
  function reset() {
    form.forma_giuridica_id = null
    form.id_prov_iscri_rea = null
    form.iscrizione_rea = ''
    form.capitale_sociale = null
    form.socio_unico = 'SU'
    form.liquidazione = 'LN'
    form.destinatario_fe = null
    form.pec_fatturazione = ''
    form.codice_sdi = ''
  }

  // Scopo: Popola il form con dati esistenti (per edit mode).
  function populate(data) {
    form.forma_giuridica_id = data.forma_giuridica_id ?? null
    form.id_prov_iscri_rea = data.id_prov_iscri_rea ?? null
    form.iscrizione_rea = data.iscrizione_rea || ''
    form.capitale_sociale = data.capitale_sociale ?? null
    form.socio_unico = data.socio_unico || 'SU'
    form.liquidazione = data.liquidazione || 'LN'
    form.destinatario_fe = data.destinatario_fe ?? null
    form.pec_fatturazione = data.pec_fatturazione || ''
    form.codice_sdi = data.codice_sdi || ''
  }

  return {
    form,
    formaCorrente,
    showRea,
    requireRea,
    showCapitaleSociale,
    requireCapitaleSociale,
    validate,
    reset,
    populate
  }
}
