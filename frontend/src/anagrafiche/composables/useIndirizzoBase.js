// Scopo: Composable base per form indirizzo (parte geografica + civico).
// Condiviso da: IndirizzoDrawer (standalone) e useIndirizzoSoggettoForm (soggetto).
// Gestisce: comune, via (unico oggetto da stradario o stradario_generale),
//           CAP, civico, check duplicato, validazione, payload.
// NON gestisce: multi-tipo, libera, matrice, auto-clone (delegati ai consumer).

import { reactive, ref, computed, watch } from 'vue'
import { useIndirizzoDuplicato } from './useIndirizzoDuplicato'
import { lookupCodiciPostaliByComune } from '../api/anagrafiche'

// Scopo: Estrae i campi civico normalizzati da un oggetto (form reattivo o snapshot).
// Condiviso da: buildIndirizzoPayload, IndirizzoDrawer (edit), useIndirizzoSoggettoForm.
export function buildCivicoPart(data) {
  return {
    civico: data.civico,
    estensione_civico: (data.estensione_civico || '').trim() || null,
    palazzina: (data.palazzina || '').trim() || null,
    scala: (data.scala || '').trim() || null,
    piano: (data.piano || '').trim() || null,
    interno: (data.interno || '').trim() || null,
  }
}

// Scopo: Costruisce payload indirizzo completo da un oggetto plain (form reattivo o snapshot).
// Condiviso da: useIndirizzoBase.buildPayload() e useIndirizzoSoggettoForm._buildPayload().
export function buildIndirizzoPayload(data) {
  const civicoPart = buildCivicoPart(data)

  const obj = data.via_obj
  if (obj?.stradario_id) {
    return { stradario_id: obj.stradario_id, ...civicoPart }
  }
  return {
    toponomastica_id: obj?.toponomastica_id,
    descrizione_via: obj?.denominazione || '',
    comune_id: data.comune_id,
    codice_postale_id: data.codice_postale_id,
    ...civicoPart,
  }
}

export function useIndirizzoBase() {
  const form = reactive({
    comune_id: null,
    // Oggetto comune per display nell'AutoComplete (necessario per restore dopo toggle)
    _comune_obj: null,
    // Oggetto via unificato: contiene dati da stradario O da stradario_generale.
    // Da stradario: { stradario_id, indirizzo_normalizzato, toponimo, denominazione, codice_postale_id }
    // Da stradario_generale: { stradario_generale_id, toponomastica_id, toponimo, denominazione, indirizzo_normalizzato }
    via_obj: null,
    via_nuova: false,
    codice_postale_id: null,
    civico: null,
    estensione_civico: '',
    palazzina: '',
    scala: '',
    piano: '',
    interno: '',
  })

  // CAP per comune selezionato (con race condition guard)
  const capOptions = ref([])
  const loadingCap = ref(false)
  let capVersion = 0
  let _restoring = false  // Sopprime reset CAP durante restore

  // Check duplicato indirizzo
  const { indirizzoWarnings, existingDettaglioId, checkDuplicato, resetWarnings } = useIndirizzoDuplicato()

  // --- Watch: CAP ---
  watch(() => form.comune_id, async (id) => {
    if (_restoring) return  // Non resettare durante restore
    capOptions.value = []
    form.codice_postale_id = null
    if (id) {
      const v = ++capVersion
      loadingCap.value = true
      try {
        const res = await lookupCodiciPostaliByComune(id)
        if (v !== capVersion) return
        capOptions.value = res.data.data.results
        if (capOptions.value.length === 1) {
          form.codice_postale_id = capOptions.value[0].id
        }
      } finally {
        if (v === capVersion) loadingCap.value = false
      }
    }
  })

  // --- Watch: via_obj / capOptions → auto-set CAP da stradario ---
  function _autoSetCap() {
    const capFromVia = form.via_obj?.codice_postale_id
    if (capFromVia && capOptions.value.some(c => c.id === capFromVia)) {
      form.codice_postale_id = capFromVia
    }
  }
  watch(() => form.via_obj, _autoSetCap)
  watch(capOptions, _autoSetCap)

  // --- Watch: check duplicato ---
  // Flusso A: via da stradario locale (stradario_id)
  // Flusso B: via da stradario_generale (stradario_generale_id + comune_id)
  // Scatta su cambio via, civico, dettagli civico, comune o CAP.
  watch([
    () => form.via_obj, () => form.civico, () => form.estensione_civico,
    () => form.palazzina, () => form.scala, () => form.piano, () => form.interno,
    () => form.comune_id, () => form.codice_postale_id,
  ], () => {
    if (_restoring) return
    const obj = form.via_obj
    const hasStradario = obj?.stradario_id
    const hasGenerale = obj?.stradario_generale_id && form.comune_id
    if (!hasStradario && !hasGenerale) { resetWarnings(); return }
    checkDuplicato({
      stradario_id: obj.stradario_id || null,
      stradario_generale_id: obj.stradario_generale_id || null,
      comune_id: form.comune_id || null,
      codice_postale_id: form.codice_postale_id || null,
      civico: form.civico || null,
      estensione_civico: (form.estensione_civico || '').trim() || null,
      palazzina: (form.palazzina || '').trim() || null,
      scala: (form.scala || '').trim() || null,
      piano: (form.piano || '').trim() || null,
      interno: (form.interno || '').trim() || null,
    })
  })

  // --- Watch: via_nuova toggle → resetta warning duplicato ---
  // Quando l'utente cambia il checkbox "crea nuovo", i warning non sono piu' validi.
  watch(() => form.via_nuova, () => { resetWarnings() })

  // Scopo: Validazione parte indirizzo.
  // CAP obbligatorio sempre (auto-set da stradario, fallback da comune).
  function validate() {
    const errors = []
    if (!form.comune_id) errors.push('comune_id')
    if (!form.via_obj) errors.push('via_obj')
    if (!form.codice_postale_id) errors.push('codice_postale_id')
    return errors
  }

  // Scopo: Indirizzo da stradario + civico inserito ma non trovato nel DB.
  // Condiviso da IndirizzoDrawer e IndirizziSoggettoDrawer (no duplicazione).
  // I consumer aggiungono condizioni locali (isCreate, isLibera).
  // Scopo: true se l'indirizzo (via + civico) non esiste ancora nel DB.
  // Flusso A: via da stradario locale. Flusso B: via da stradario generale + comune.
  const addressNotFound = computed(() => {
    if (form.via_nuova) return false  // "crea nuovo" attivo: non segnalare
    const hasVia = form.via_obj?.stradario_id || (form.via_obj?.stradario_generale_id && form.comune_id)
    return !!hasVia && !!form.civico && !existingDettaglioId.value
  })

  // Scopo: Costruisce payload indirizzo dal form reattivo corrente.
  // Delega a buildIndirizzoPayload (helper statico condiviso).
  function buildPayload() {
    return buildIndirizzoPayload(form)
  }

  // Scopo: Snapshot dei campi form per salvataggio/restore.
  function snapshot() {
    return {
      comune_id: form.comune_id,
      _comune_obj: form._comune_obj,
      via_obj: form.via_obj,
      via_nuova: form.via_nuova,
      codice_postale_id: form.codice_postale_id,
      civico: form.civico,
      estensione_civico: form.estensione_civico,
      palazzina: form.palazzina,
      scala: form.scala,
      piano: form.piano,
      interno: form.interno,
    }
  }

  // Scopo: Ripristina form da snapshot senza triggerare reset CAP.
  function restore(snap) {
    _restoring = true
    form.comune_id = snap.comune_id ?? null
    form._comune_obj = snap._comune_obj ?? null
    form.via_obj = snap.via_obj ?? null
    form.via_nuova = snap.via_nuova ?? false
    form.codice_postale_id = snap.codice_postale_id ?? null
    form.civico = snap.civico ?? null
    form.estensione_civico = (snap.estensione_civico || '').replace(/^\//, '')
    form.palazzina = snap.palazzina || ''
    form.scala = snap.scala || ''
    form.piano = snap.piano || ''
    form.interno = snap.interno || ''
    // Ricarica opzioni CAP per il comune ripristinato (senza resettare il valore)
    if (form.comune_id) {
      const v = ++capVersion
      loadingCap.value = true
      lookupCodiciPostaliByComune(form.comune_id).then(res => {
        if (v !== capVersion) return
        capOptions.value = res.data.data.results
      }).finally(() => {
        if (v === capVersion) loadingCap.value = false
        _restoring = false
      })
    } else {
      _restoring = false
    }
  }

  function reset() {
    form.comune_id = null
    form._comune_obj = null
    form.via_obj = null
    form.via_nuova = false
    form.codice_postale_id = null
    form.civico = null
    form.estensione_civico = ''
    form.palazzina = ''
    form.scala = ''
    form.piano = ''
    form.interno = ''
    capOptions.value = []
    resetWarnings()
  }

  // Scopo: Esegue una funzione sopprimendo i watcher (check duplicato, reset CAP).
  //        Usato da onStartReplace per popolare il form senza effetti collaterali.
  function withSuppressedChecks(fn) {
    _restoring = true
    try { fn() } finally { _restoring = false }
  }

  return {
    form,
    capOptions,
    loadingCap,
    indirizzoWarnings,
    existingDettaglioId,
    addressNotFound,
    resetWarnings,
    withSuppressedChecks,
    validate,
    buildPayload,
    snapshot,
    restore,
    reset,
  }
}
