// Scopo: Composable per form indirizzo layer soggetto (identita').
// Estende useIndirizzoBase con: multi-tipo, matrice, auto-clone, modalita' libera.
// L'utente compila un indirizzo alla volta, con auto-clone per gli obbligatori mancanti.

import { ref, computed, watch } from 'vue'
import { useLookup } from './useLookup'
import { useIndirizzoBase } from './useIndirizzoBase'
import { lookupStati } from '../../anagrafiche/api/anagrafiche'

export function useIndirizzoSoggettoForm() {
  // Composable base: comune, stradario, civico, CAP, check duplicato
  const base = useIndirizzoBase()

  // Estendi il form reattivo di base con campi soggetto.
  // Vue 3 reactive() traccia le nuove proprieta' aggiunte dopo la creazione.
  const form = base.form
  form.tipo_indirizzo_codice = null
  form.indirizzo_libero = ''
  form.stato_id = null
  form.locality = ''

  // Modalita' libera (true = indirizzo estero/libero)
  const isLibera = ref(false)

  // === Multi-tipo ===
  const indirizziSalvati = ref({})
  const tipoAttivo = ref(null)
  const autoClone = ref(true)
  const tipiMatrice = ref([])

  const tipiStato = computed(() =>
    tipiMatrice.value.map(m => ({
      codice: m.codice,
      descrizione: m.descrizione,
      obbligatorio: m.obbligatorio,
      compilato: !!indirizziSalvati.value[m.codice],
      attivo: tipoAttivo.value === m.codice,
    }))
  )

  // Lookup stati per modalita' libera (lazy)
  const statiLookup = useLookup(() => lookupStati())

  watch(isLibera, (val) => {
    if (val && !statiLookup.loaded.value) statiLookup.load()
  })

  // --- Matrice ---
  function setMatrice(matrice) {
    tipiMatrice.value = matrice
    indirizziSalvati.value = {}
    const primo = matrice.find(m => m.obbligatorio) || matrice[0]
    if (primo) {
      tipoAttivo.value = primo.codice
      form.tipo_indirizzo_codice = primo.codice
    }
  }

  // --- Snapshot (base + campi soggetto) ---
  function _snapshot() {
    return {
      ...base.snapshot(),
      tipo_indirizzo_codice: form.tipo_indirizzo_codice,
      isLibera: isLibera.value,
      indirizzo_libero: form.indirizzo_libero,
      stato_id: form.stato_id,
      locality: form.locality,
    }
  }

  function _restore(snap) {
    base.restore(snap)
    form.tipo_indirizzo_codice = snap.tipo_indirizzo_codice ?? null
    isLibera.value = snap.isLibera ?? false
    form.indirizzo_libero = snap.indirizzo_libero || ''
    form.stato_id = snap.stato_id ?? null
    form.locality = snap.locality || ''
  }

  function _resetSoggettoFields() {
    form.tipo_indirizzo_codice = null
    isLibera.value = false
    form.indirizzo_libero = ''
    form.stato_id = null
    form.locality = ''
  }

  function _salvaSnapshot() {
    if (!tipoAttivo.value) return
    if (!form.comune_id && !(form.indirizzo_libero || '').trim()) return
    indirizziSalvati.value[tipoAttivo.value] = _snapshot()
  }

  function _caricaSnapshot(codice) {
    const snap = indirizziSalvati.value[codice]
    if (snap) {
      _restore(snap)
    } else {
      base.reset()
      _resetSoggettoFields()
      form.tipo_indirizzo_codice = codice
    }
  }

  function switchTipo(codice) {
    if (codice === tipoAttivo.value) return
    _salvaSnapshot()
    tipoAttivo.value = codice
    _caricaSnapshot(codice)
  }

  // --- Validazione ---
  function validate() {
    const errors = []
    if (!form.tipo_indirizzo_codice) errors.push('tipo_indirizzo_codice')

    if (isLibera.value) {
      if (!(form.indirizzo_libero || '').trim()) errors.push('indirizzo_libero')
      if (!form.stato_id) errors.push('stato_id')
    } else {
      errors.push(...base.validate())
    }
    return errors
  }

  const canSave = computed(() => validate().length === 0)

  const hasIndirizzi = computed(() => {
    if (form.comune_id || (form.indirizzo_libero || '').trim()) return true
    return Object.keys(indirizziSalvati.value).length > 0
  })

  // --- Payload ---
  function _buildPayload(snap, codice) {
    const payload = { tipo_indirizzo_codice: codice }

    if (snap.isLibera) {
      return {
        ...payload,
        indirizzo_libero: (snap.indirizzo_libero || '').trim(),
        stato_id: snap.stato_id,
        locality: (snap.locality || '').trim() || null,
      }
    }

    const civicoPart = {
      civico: snap.civico,
      estensione_civico: (snap.estensione_civico || '').trim() || null,
      palazzina: (snap.palazzina || '').trim() || null,
      scala: (snap.scala || '').trim() || null,
      piano: (snap.piano || '').trim() || null,
      interno: (snap.interno || '').trim() || null,
    }

    const obj = snap.via_obj
    if (obj?.stradario_id) {
      // Via esistente — usa stradario_id direttamente
      return { ...payload, stradario_id: obj.stradario_id, ...civicoPart }
    }
    // Via da stradario_generale — crea stradario locale
    return {
      ...payload,
      toponomastica_id: obj?.toponomastica_id,
      descrizione_via: obj?.denominazione || '',
      comune_id: snap.comune_id,
      codice_postale_id: snap.codice_postale_id,
      ...civicoPart,
    }
  }

  function toPayloadArray() {
    _salvaSnapshot()
    const result = []
    const salvati = { ...indirizziSalvati.value }

    for (const [codice, data] of Object.entries(salvati)) {
      result.push(_buildPayload(data, codice))
    }

    if (autoClone.value && result.length > 0) {
      const primoSalvato = Object.values(salvati)[0]
      for (const m of tipiMatrice.value) {
        if (m.obbligatorio && !salvati[m.codice]) {
          result.push(_buildPayload(primoSalvato, m.codice))
        }
      }
    }
    return result
  }

  // --- Reset completo ---
  function reset() {
    base.reset()
    _resetSoggettoFields()
    indirizziSalvati.value = {}
    tipoAttivo.value = null
    autoClone.value = true
    tipiMatrice.value = []
  }

  // --- Popola da dati esistenti ---
  function populate(data) {
    base.restore(data)
    form.tipo_indirizzo_codice = data.tipo_indirizzo_codice ?? null
    isLibera.value = !!data.indirizzo_libero
    form.indirizzo_libero = data.indirizzo_libero || ''
    form.stato_id = data.stato_id ?? null
    form.locality = data.locality || ''
  }

  return {
    form,
    isLibera,
    // Multi-tipo
    tipiStato,
    tipoAttivo,
    autoClone,
    hasIndirizzi,
    switchTipo,
    setMatrice,
    toPayloadArray,
    // Lookup
    statiLookup,
    capOptions: base.capOptions,
    loadingCap: base.loadingCap,
    indirizzoWarnings: base.indirizzoWarnings,
    existingDettaglioId: base.existingDettaglioId,
    // Singolo
    canSave,
    validate,
    reset,
    populate,
  }
}
