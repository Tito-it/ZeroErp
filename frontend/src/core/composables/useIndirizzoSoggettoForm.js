// Scopo: Composable per form indirizzo layer soggetto (identita').
// Supporta modalita' normalizzata (comune + stradario + civico)
// e modalita' libera (indirizzo_libero + stato + locality) per indirizzi esteri.
// Il tipo indirizzo e' filtrato dalla matrice DB.

import { reactive, ref, computed, watch } from 'vue'
import { useLookup } from './useLookup'
import { lookupCodiciPostaliByComune, listToponomastica, lookupStati } from '../../anagrafiche/api/anagrafiche'

export function useIndirizzoSoggettoForm() {
  const form = reactive({
    tipo_indirizzo_codice: null,
    // Modalita' normalizzata
    comune_id: null,
    stradario_obj: null,
    via_nuova: false,
    toponomastica_id: null,
    nome_via: '',
    codice_postale_id: null,
    civico: null,
    estensione_civico: '',
    palazzina: '',
    scala: '',
    piano: '',
    interno: '',
    // Modalita' libera
    indirizzo_libero: '',
    stato_id: null,
    locality: ''
  })

  // Modalita' libera (true = indirizzo estero/libero)
  const isLibera = ref(false)

  // Lookup stati per modalita' libera
  const statiLookup = useLookup(() => lookupStati())

  // Lookup toponomastica per "via nuova" (lazy)
  const toponomasticaLookup = useLookup(
    () => listToponomastica({ limit: 200 })
  )

  // CAP per comune selezionato
  const capOptions = ref([])
  const loadingCap = ref(false)

  // Carica toponomastica quando serve
  watch(() => form.via_nuova, (val) => {
    if (val && !toponomasticaLookup.loaded.value) {
      toponomasticaLookup.load()
    }
  })

  // Carica stati quando si passa a libera
  watch(isLibera, (val) => {
    if (val && !statiLookup.loaded.value) {
      statiLookup.load()
    }
  })

  // Carica CAP quando cambia il comune.
  // Versione per evitare race condition su cambio rapido comune.
  let capVersion = 0
  watch(() => form.comune_id, async (id) => {
    capOptions.value = []
    form.codice_postale_id = null
    if (id) {
      const v = ++capVersion
      loadingCap.value = true
      try {
        const res = await lookupCodiciPostaliByComune(id)
        if (v !== capVersion) return
        capOptions.value = res.data.data.results
        // Auto-seleziona se unico CAP
        if (capOptions.value.length === 1) {
          form.codice_postale_id = capOptions.value[0].id
        }
      } finally {
        if (v === capVersion) loadingCap.value = false
      }
    }
  })

  // Scopo: Validazione in base alla modalita'.
  function validate() {
    const errors = []
    if (!form.tipo_indirizzo_codice) errors.push('tipo_indirizzo_codice')

    if (isLibera.value) {
      if (!form.indirizzo_libero.trim()) errors.push('indirizzo_libero')
      if (!form.stato_id) errors.push('stato_id')
    } else {
      if (!form.comune_id) errors.push('comune_id')
      if (form.via_nuova) {
        if (!form.toponomastica_id) errors.push('toponomastica_id')
        if (!form.nome_via.trim()) errors.push('nome_via')
        if (!form.codice_postale_id) errors.push('codice_postale_id')
      } else {
        if (!form.stradario_obj) errors.push('stradario_obj')
      }
    }
    return errors
  }

  // Scopo: Costruisce il payload per il backend.
  function toPayload() {
    const base = { tipo_indirizzo_codice: form.tipo_indirizzo_codice }

    if (isLibera.value) {
      return {
        ...base,
        indirizzo_libero: form.indirizzo_libero.trim(),
        stato_id: form.stato_id,
        locality: form.locality.trim() || null
      }
    }

    const civicoPart = {
      civico: form.civico,
      estensione_civico: form.estensione_civico.trim() || null,
      palazzina: form.palazzina.trim() || null,
      scala: form.scala.trim() || null,
      piano: form.piano.trim() || null,
      interno: form.interno.trim() || null
    }

    if (form.via_nuova) {
      return {
        ...base,
        toponomastica_id: form.toponomastica_id,
        descrizione_via: form.nome_via.trim(),
        comune_id: form.comune_id,
        codice_postale_id: form.codice_postale_id,
        ...civicoPart
      }
    }

    return {
      ...base,
      stradario_id: form.stradario_obj?.id,
      ...civicoPart
    }
  }

  // Scopo: Indica se il form ha dati sufficienti per il salvataggio.
  const canSave = computed(() => validate().length === 0)

  // Scopo: Reset form ai valori iniziali.
  function reset() {
    form.tipo_indirizzo_codice = null
    form.comune_id = null
    form.stradario_obj = null
    form.via_nuova = false
    form.toponomastica_id = null
    form.nome_via = ''
    form.codice_postale_id = null
    form.civico = null
    form.estensione_civico = ''
    form.palazzina = ''
    form.scala = ''
    form.piano = ''
    form.interno = ''
    form.indirizzo_libero = ''
    form.stato_id = null
    form.locality = ''
    isLibera.value = false
    capOptions.value = []
  }

  // Scopo: Popola il form con dati esistenti (per edit mode).
  function populate(data) {
    form.tipo_indirizzo_codice = data.tipo_indirizzo_codice ?? null
    form.comune_id = data.comune_id ?? null
    form.stradario_obj = data.stradario_obj ?? null
    form.via_nuova = false
    form.toponomastica_id = data.toponomastica_id ?? null
    form.nome_via = data.nome_via || ''
    form.codice_postale_id = data.codice_postale_id ?? null
    form.civico = data.civico ?? null
    form.estensione_civico = data.estensione_civico || ''
    form.palazzina = data.palazzina || ''
    form.scala = data.scala || ''
    form.piano = data.piano || ''
    form.interno = data.interno || ''
    form.indirizzo_libero = data.indirizzo_libero || ''
    form.stato_id = data.stato_id ?? null
    form.locality = data.locality || ''
    isLibera.value = !!data.indirizzo_libero
  }

  return {
    form,
    isLibera,
    statiLookup,
    toponomasticaLookup,
    capOptions,
    loadingCap,
    canSave,
    validate,
    toPayload,
    reset,
    populate
  }
}
