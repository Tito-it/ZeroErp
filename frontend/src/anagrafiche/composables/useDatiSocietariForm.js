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
    // Enumerati. ⛔ Vuoti finche' non li sceglie l'operatore: a NULL il verbo
    //    DB prende il default di `config.parameters` con la cascata (l'override
    //    dell'emittente in sessione, brief-db-parametri-senza-override D-2-bis).
    //    Un valore scritto qui sarebbe una seconda copia del default, e il
    //    parametro dalla UI non agirebbe mai.
    socio_unico: null,
    liquidazione: null,
    // Fatturazione elettronica
    destinatario_fe: null,
    pec_fatturazione: '',
    codice_sdi: '',
    // ISO 'YYYY-MM-DD' o null (il DatePicker lo converte a video).
    // ⚠️ Il verbo DB riceve lo STATO INTERO: un campo che il form non tiene
    //    verrebbe azzerato al primo salvataggio in modifica (2026-10-10).
    data_costituzione: null
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
    form.socio_unico = null
    form.liquidazione = null
    form.destinatario_fe = null
    form.pec_fatturazione = ''
    form.codice_sdi = ''
    form.data_costituzione = null
  }

  // Scopo: Popola il form con dati esistenti (per edit mode).
  function populate(data) {
    form.forma_giuridica_id = data.forma_giuridica_id ?? null
    form.id_prov_iscri_rea = data.id_prov_iscri_rea ?? null
    form.iscrizione_rea = data.iscrizione_rea || ''
    form.capitale_sociale = data.capitale_sociale ?? null
    form.socio_unico = data.socio_unico ?? null
    form.liquidazione = data.liquidazione ?? null
    form.destinatario_fe = data.destinatario_fe ?? null
    form.pec_fatturazione = data.pec_fatturazione || ''
    form.codice_sdi = data.codice_sdi || ''
    form.data_costituzione = data.data_costituzione ?? null
  }

  // Scopo: Il corpo da mandare al backend: SOLO cio' che il form mostra.
  // ⭐ Il form tiene i valori dei campi nascosti (si torna indietro e si
  //    ritrovano), ma non li manda: un codice SDI scritto e poi lasciato per
  //    il canale P arriverebbe al guard del DB, che lo rifiuta sul campo
  //    `codice_sdi` — un campo che l'operatore non vede piu'. Stessa regola
  //    per REA e capitale quando la forma giuridica non li prevede.
  function toPayload() {
    return {
      ...form,
      id_prov_iscri_rea: showRea.value ? form.id_prov_iscri_rea : null,
      iscrizione_rea: showRea.value ? form.iscrizione_rea : '',
      capitale_sociale: showCapitaleSociale.value ? form.capitale_sociale : null,
      pec_fatturazione: form.destinatario_fe === 'P' ? form.pec_fatturazione : '',
      codice_sdi: form.destinatario_fe === 'C' ? form.codice_sdi : ''
    }
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
    populate,
    toPayload
  }
}
