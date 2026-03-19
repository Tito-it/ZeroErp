// Scopo: Composable per form indirizzo layer soggetto (identita').
// Compone: useIndirizzoBase (form geografico) + useIndirizzoMultiTipo (snapshot/barra tag)
//          + modalita' libera (indirizzo estero) + payload.
// L'utente compila un indirizzo alla volta, con auto-clone per gli obbligatori mancanti.

import { ref, computed, watch } from 'vue'
import { useLookup } from './useLookup'
import { useIndirizzoBase, buildIndirizzoPayload } from './useIndirizzoBase'
import { useIndirizzoMultiTipo } from './useIndirizzoMultiTipo'
import { lookupStati } from '../../anagrafiche/api/anagrafiche'

export function useIndirizzoSoggettoForm() {
  // Composable base: comune, via, civico, CAP, check duplicato
  const base = useIndirizzoBase()

  // Estendi il form reattivo di base con campi soggetto.
  // Vue 3 reactive() traccia le nuove proprieta' aggiunte dopo la creazione.
  const form = base.form
  form.tipo_indirizzo_codice = null
  form.indirizzo_libero = ''
  form.stato_id = null
  form.locality = ''
  form._isLibera = false

  // Modalita' libera con due slot di memoria: i dati nazionali vengono
  // salvati al toggle verso estero e ripristinati al toggle verso nazionale.
  const _savedNazionale = ref(null)
  const _savedEstero = ref({ indirizzo_libero: '', stato_id: null, locality: '' })

  const isLibera = computed({
    get: () => form._isLibera,
    set: (val) => {
      if (val === form._isLibera) return
      if (val) {
        // Nazionale → Estero: salva dati nazionali, ripristina estero
        _savedNazionale.value = base.snapshot()
        form.indirizzo_libero = _savedEstero.value.indirizzo_libero || ''
        form.stato_id = _savedEstero.value.stato_id || null
        form.locality = _savedEstero.value.locality || ''
      } else {
        // Estero → Nazionale: salva dati estero, ripristina nazionali
        _savedEstero.value = {
          indirizzo_libero: form.indirizzo_libero,
          stato_id: form.stato_id,
          locality: form.locality,
        }
        if (_savedNazionale.value) {
          base.restore(_savedNazionale.value)
        }
      }
      form._isLibera = val
    },
  })

  // Multi-tipo: snapshot/restore, barra tag, auto-clone
  const multiTipo = useIndirizzoMultiTipo({
    baseSnapshot: base.snapshot,
    baseRestore: base.restore,
    baseReset: base.reset,
    form,
  })

  // Lookup stati per modalita' libera (lazy)
  const statiLookup = useLookup(() => lookupStati())

  watch(isLibera, (val) => {
    if (val && !statiLookup.loaded.value) statiLookup.load()
  })

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
    return Object.keys(multiTipo.indirizziSalvati.value).length > 0
  })

  // --- Payload ---
  // Scopo: Costruisce payload da snapshot. Libera ha path dedicato,
  // normalizzato delega a buildIndirizzoPayload (unica source of truth).
  function _buildPayload(snap, codice) {
    if (snap.isLibera) {
      return {
        tipo_indirizzo_codice: codice,
        indirizzo_libero: (snap.indirizzo_libero || '').trim(),
        stato_id: snap.stato_id,
        locality: (snap.locality || '').trim() || null,
      }
    }
    return {
      tipo_indirizzo_codice: codice,
      ...buildIndirizzoPayload(snap),
    }
  }

  // Scopo: Converte snapshot salvati in array payload.
  // Auto-clone NON avviene qui — e' gestito dal backend (_apply_auto_clone).
  function toPayloadArray() {
    multiTipo.salvaSnapshot()
    const salvati = { ...multiTipo.indirizziSalvati.value }
    return Object.entries(salvati).map(([codice, data]) => _buildPayload(data, codice))
  }

  // --- Reset completo ---
  function reset() {
    base.reset()
    form.tipo_indirizzo_codice = null
    form._isLibera = false
    form.indirizzo_libero = ''
    form.stato_id = null
    form.locality = ''
    _savedNazionale.value = null
    _savedEstero.value = { indirizzo_libero: '', stato_id: null, locality: '' }
    multiTipo.reset()
  }

  // --- Popola da dati esistenti ---
  function populate(data) {
    base.restore(data)
    form.tipo_indirizzo_codice = data.tipo_indirizzo_codice ?? null
    form._isLibera = !!data.indirizzo_libero
    form.indirizzo_libero = data.indirizzo_libero || ''
    form.stato_id = data.stato_id ?? null
    form.locality = data.locality || ''
  }

  return {
    form,
    isLibera,
    // Multi-tipo (da composable dedicato)
    tipiStato: multiTipo.tipiStato,
    tipoAttivo: multiTipo.tipoAttivo,
    autoClone: multiTipo.autoClone,
    hasIndirizzi,
    switchTipo: multiTipo.switchTipo,
    setMatrice: multiTipo.setMatrice,
    toPayloadArray,
    // Lookup
    statiLookup,
    capOptions: base.capOptions,
    loadingCap: base.loadingCap,
    indirizzoWarnings: base.indirizzoWarnings,
    existingDettaglioId: base.existingDettaglioId,
    addressNotFound: base.addressNotFound,
    // Singolo
    canSave,
    validate,
    reset,
    populate,
  }
}
