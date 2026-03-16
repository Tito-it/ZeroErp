// Scopo: Composable per form indirizzo layer soggetto (identita').
// Supporta multi-tipo: la matrice DB definisce quali tipi sono ammessi/obbligatori.
// L'utente compila un indirizzo alla volta, con auto-clone per gli obbligatori mancanti.
// Modalita' normalizzata (comune + stradario + civico) e libera (estero).

import { reactive, ref, computed, watch } from 'vue'
import { useLookup } from './useLookup'
import { useIndirizzoDuplicato } from './useIndirizzoDuplicato'
import { lookupCodiciPostaliByComune, listToponomastica, lookupStati } from '../../anagrafiche/api/anagrafiche'

export function useIndirizzoSoggettoForm() {
  // Form corrente (un solo indirizzo alla volta)
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

  // === Multi-tipo ===
  // Indirizzi salvati per tipo (codice → snapshot form)
  const indirizziSalvati = ref({})
  // Tipo attivo corrente
  const tipoAttivo = ref(null)
  // Auto-clone: copia indirizzo per tutti gli obbligatori mancanti
  const autoClone = ref(true)

  // Tipi dalla matrice (impostati dal parent via setMatrice)
  const tipiMatrice = ref([])

  // Stato compilazione per ogni tipo (per la barra tag)
  const tipiStato = computed(() =>
    tipiMatrice.value.map(m => ({
      codice: m.codice,
      descrizione: m.descrizione,
      obbligatorio: m.obbligatorio,
      compilato: !!indirizziSalvati.value[m.codice],
      attivo: tipoAttivo.value === m.codice,
    }))
  )

  // Imposta la matrice dal parent e seleziona il primo obbligatorio
  function setMatrice(matrice) {
    tipiMatrice.value = matrice
    indirizziSalvati.value = {}
    const primo = matrice.find(m => m.obbligatorio) || matrice[0]
    if (primo) {
      tipoAttivo.value = primo.codice
      form.tipo_indirizzo_codice = primo.codice
    }
  }

  // Salva snapshot del form corrente per il tipo attivo
  function _salvaSnapshot() {
    if (!tipoAttivo.value) return
    // Salva solo se il form ha dati minimi (comune o indirizzo libero)
    if (!form.comune_id && !form.indirizzo_libero?.trim()) return
    indirizziSalvati.value[tipoAttivo.value] = {
      ..._extractFormData(),
      tipo_indirizzo_codice: tipoAttivo.value,
      isLibera: isLibera.value,
    }
  }

  // Estrae i dati dal form corrente (senza tipo_indirizzo_codice)
  function _extractFormData() {
    return {
      comune_id: form.comune_id,
      stradario_obj: form.stradario_obj,
      via_nuova: form.via_nuova,
      toponomastica_id: form.toponomastica_id,
      nome_via: form.nome_via,
      codice_postale_id: form.codice_postale_id,
      civico: form.civico,
      estensione_civico: form.estensione_civico,
      palazzina: form.palazzina,
      scala: form.scala,
      piano: form.piano,
      interno: form.interno,
      indirizzo_libero: form.indirizzo_libero,
      stato_id: form.stato_id,
      locality: form.locality,
    }
  }

  // Carica snapshot salvato nel form (switch tipo)
  function _caricaSnapshot(codice) {
    const snap = indirizziSalvati.value[codice]
    if (snap) {
      Object.assign(form, {
        tipo_indirizzo_codice: codice,
        comune_id: snap.comune_id,
        stradario_obj: snap.stradario_obj,
        via_nuova: snap.via_nuova,
        toponomastica_id: snap.toponomastica_id,
        nome_via: snap.nome_via,
        codice_postale_id: snap.codice_postale_id,
        civico: snap.civico,
        estensione_civico: snap.estensione_civico,
        palazzina: snap.palazzina,
        scala: snap.scala,
        piano: snap.piano,
        interno: snap.interno,
        indirizzo_libero: snap.indirizzo_libero,
        stato_id: snap.stato_id,
        locality: snap.locality,
      })
      isLibera.value = snap.isLibera || false
    } else {
      // Tipo non ancora compilato: resetta form ma mantieni tipo
      _resetFormFields()
      form.tipo_indirizzo_codice = codice
    }
  }

  // Switch al tipo cliccato nella barra tag
  function switchTipo(codice) {
    if (codice === tipoAttivo.value) return
    // Salva form corrente prima di switchare
    _salvaSnapshot()
    tipoAttivo.value = codice
    _caricaSnapshot(codice)
  }

  // Lookup stati per modalita' libera
  const statiLookup = useLookup(() => lookupStati())

  // Lookup toponomastica per "via nuova" (lazy)
  const toponomasticaLookup = useLookup(
    () => listToponomastica({ limit: 200 })
  )

  // CAP per comune selezionato
  const capOptions = ref([])
  const loadingCap = ref(false)

  // Check duplicato indirizzo (generico)
  const { indirizzoWarnings, checkDuplicato, resetWarnings } = useIndirizzoDuplicato()

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

  // Check duplicato quando cambia stradario o civico
  watch([() => form.stradario_obj, () => form.civico], () => {
    if (!form.stradario_obj?.id) { resetWarnings(); return }
    checkDuplicato(form.stradario_obj.id, form.civico)
  })

  // Carica CAP quando cambia il comune.
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
        if (capOptions.value.length === 1) {
          form.codice_postale_id = capOptions.value[0].id
        }
      } finally {
        if (v === capVersion) loadingCap.value = false
      }
    }
  })

  // Scopo: Validazione del form corrente.
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

  // Scopo: Costruisce payload per un singolo indirizzo.
  function _buildPayload(data, codice) {
    const base = { tipo_indirizzo_codice: codice }

    if (data.isLibera) {
      return {
        ...base,
        indirizzo_libero: (data.indirizzo_libero || '').trim(),
        stato_id: data.stato_id,
        locality: (data.locality || '').trim() || null
      }
    }

    const civicoPart = {
      civico: data.civico,
      estensione_civico: (data.estensione_civico || '').trim() || null,
      palazzina: (data.palazzina || '').trim() || null,
      scala: (data.scala || '').trim() || null,
      piano: (data.piano || '').trim() || null,
      interno: (data.interno || '').trim() || null
    }

    if (data.via_nuova) {
      return {
        ...base,
        toponomastica_id: data.toponomastica_id,
        descrizione_via: (data.nome_via || '').trim(),
        comune_id: data.comune_id,
        codice_postale_id: data.codice_postale_id,
        ...civicoPart
      }
    }

    return {
      ...base,
      stradario_id: data.stradario_obj?.id,
      ...civicoPart
    }
  }

  // Scopo: Genera array payload per tutti gli indirizzi (salvati + auto-clone).
  function toPayloadArray() {
    // Salva il form corrente
    _salvaSnapshot()

    const result = []
    const salvati = { ...indirizziSalvati.value }

    // Indirizzi esplicitamente compilati
    for (const [codice, data] of Object.entries(salvati)) {
      result.push(_buildPayload(data, codice))
    }

    // Auto-clone: per ogni obbligatorio mancante, clona il primo compilato
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

  // Scopo: Indica se almeno un indirizzo e' compilato.
  const canSave = computed(() => validate().length === 0)

  // Scopo: Ha almeno un indirizzo compilato (per il payload).
  const hasIndirizzi = computed(() => {
    // Check form corrente
    if (form.comune_id || (form.indirizzo_libero && form.indirizzo_libero.trim())) return true
    // Check salvati
    return Object.keys(indirizziSalvati.value).length > 0
  })

  function _resetFormFields() {
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
  }

  // Scopo: Reset completo.
  function reset() {
    _resetFormFields()
    capOptions.value = []
    indirizziSalvati.value = {}
    tipoAttivo.value = null
    autoClone.value = true
    tipiMatrice.value = []
    resetWarnings()
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
    toponomasticaLookup,
    capOptions,
    loadingCap,
    indirizzoWarnings,
    // Singolo
    canSave,
    validate,
    reset,
    populate
  }
}
