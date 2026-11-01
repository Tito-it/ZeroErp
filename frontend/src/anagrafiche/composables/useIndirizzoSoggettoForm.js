// Scopo: Composable per form indirizzo layer soggetto (identita').
// Compone: useIndirizzoBase (form geografico) + useIndirizzoMultiTipo (snapshot/barra tag)
//          + modalita' libera (due forme decise dallo stato, `indirizzoLibero.js`) + payload.
// L'utente compila un indirizzo alla volta, con auto-clone per gli obbligatori mancanti.

import { ref, computed, watch } from 'vue'
import { useLookup } from '../../core/composables/useLookup'
import { useIndirizzoBase, buildIndirizzoPayload } from './useIndirizzoBase'
import { useIndirizzoMultiTipo } from './useIndirizzoMultiTipo'
import { lookupStati } from '../api/anagrafiche'
import { lookupMatriceIndirizzi, lookupMatriceIndirizziRuolo } from '../../core/apiCore'
import {
  assegnaCampiLiberi, campiLiberi, payloadLibero, statoDi, validaLibero,
} from './indirizzoLibero'

export function useIndirizzoSoggettoForm() {
  // Composable base: comune, via, civico, CAP, check duplicato
  const base = useIndirizzoBase()

  // Estendi il form reattivo di base con campi soggetto.
  // Vue 3 reactive() traccia le nuove proprieta' aggiunte dopo la creazione.
  const form = base.form
  form.tipo_indirizzo_codice_interno = null
  assegnaCampiLiberi(form)
  form._isLibera = false

  // Modalita' libera con due slot di memoria: i dati nazionali vengono
  // salvati al toggle verso estero e ripristinati al toggle verso nazionale.
  // Comune e CAP sono della parte geografica (base): la forma libera «del
  // catalogo» li usa, e restano condivisi fra le due modalita'.
  const _savedNazionale = ref(null)
  const _savedEstero = ref(campiLiberi())

  const isLibera = computed({
    get: () => form._isLibera,
    set: (val) => {
      if (val === form._isLibera) return
      if (val) {
        // Nazionale → Estero: salva dati nazionali, ripristina estero
        _savedNazionale.value = base.snapshot()
        assegnaCampiLiberi(form, _savedEstero.value)
      } else {
        // Estero → Nazionale: salva dati estero, ripristina nazionali
        _savedEstero.value = campiLiberi(form)
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

  // Lookup stati per modalita' libera (lazy). Ogni stato porta
  // `catalogo_comuni_completo` (la forma) e `proposto` (la preselezione).
  const statiLookup = useLookup(() => lookupStati())

  watch(isLibera, (val) => {
    if (val && !statiLookup.loaded.value) statiLookup.load()
  })

  // Lo stato proposto (parametro STATO_PROPOSTO_ISO2, dal DB) si preseleziona
  // quando l'indirizzo libero non ne ha uno: mai scelto in silenzio sopra una
  // scelta dell'operatore.
  watch([isLibera, () => statiLookup.items.value], ([libera, stati]) => {
    if (!libera || form.stato_id || !Array.isArray(stati)) return
    const proposto = stati.find((s) => s.proposto)
    if (proposto) form.stato_id = proposto.id
  })

  // Lo stato scelto, la cui riga decide la forma dell'indirizzo libero
  // (`indirizzoLibero.js`; quali campi mostrare lo decide il componente).
  const statoLibero = computed(() => statoDi(statiLookup.items.value, form.stato_id))

  // --- Validazione ---
  function validate() {
    const errors = []
    if (!form.tipo_indirizzo_codice_interno) errors.push('tipo_indirizzo_codice_interno')

    if (isLibera.value) {
      errors.push(...validaLibero(form, statoLibero.value))
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
  // ⚠️ Il tipo e' `tipo_indirizzo_codice_interno` in ingresso, in uscita e nello
  //    stato del form (2026-11-01, regola C del naming): il DB rifiuta la vecchia
  //    `tipo_indirizzo_codice` con E_CAMPO_NON_AMMESSO, che ora e' solo il display.
  function _buildPayload(snap, codice) {
    if (snap.isLibera) {
      return {
        tipo_indirizzo_codice_interno: codice,
        ...payloadLibero(snap, statoDi(statiLookup.items.value, snap.stato_id)),
      }
    }
    return {
      tipo_indirizzo_codice_interno: codice,
      ...buildIndirizzoPayload(snap),
    }
  }

  // Scopo: Converte snapshot salvati in array payload.
  // Auto-clone NON avviene qui — lo fa la madre del DB
  // `anagrafiche.fn_crea_indirizzi_soggetto` (flag `auto_clone` del payload).
  function toPayloadArray() {
    multiTipo.salvaSnapshot()
    const salvati = { ...multiTipo.indirizziSalvati.value }
    return Object.entries(salvati).map(([codice, data]) => _buildPayload(data, codice))
  }

  // --- Reset completo ---
  function reset() {
    base.reset()
    form.tipo_indirizzo_codice_interno = null
    form._isLibera = false
    assegnaCampiLiberi(form)
    _savedNazionale.value = null
    _savedEstero.value = campiLiberi()
    multiTipo.reset()
  }

  // --- Popola da dati esistenti ---
  function populate(data) {
    base.restore(data)
    form.tipo_indirizzo_codice_interno = data.tipo_indirizzo_codice_interno ?? null
    form._isLibera = !!data.indirizzo_libero
    assegnaCampiLiberi(form, data)
  }

  // Scopo: Carica matrice indirizzi per tipo soggetto dettaglio e setta nel multi-tipo.
  async function loadMatriceTipo(tipoSoggettoDettaglioId) {
    try {
      const res = await lookupMatriceIndirizzi(tipoSoggettoDettaglioId)
      multiTipo.setMatrice(res.data?.data?.results || [])
    } catch { multiTipo.setMatrice([]) }
  }

  // Scopo: Carica matrice indirizzi per codice ruolo (es. 'FO', 'CL') e setta nel multi-tipo.
  async function loadMatriceRuolo(tipoRuoloCodice) {
    try {
      const res = await lookupMatriceIndirizziRuolo(tipoRuoloCodice)
      multiTipo.setMatrice(res.data?.data?.results || [])
    } catch { multiTipo.setMatrice([]) }
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
    loadMatriceTipo,
    loadMatriceRuolo,
    toPayloadArray,
    // Lookup
    statiLookup,
    capOptions: base.capOptions,
    loadingCap: base.loadingCap,
    indirizzoWarnings: base.indirizzoWarnings,
    existingDettaglioId: base.existingDettaglioId,
    addressNotFound: base.addressNotFound,
    resetWarnings: base.resetWarnings,
    withSuppressedChecks: base.withSuppressedChecks,
    // Singolo
    canSave,
    validate,
    reset,
    populate,
  }
}
