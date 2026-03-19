// Scopo: Composable per gestione multi-tipo indirizzo soggetto.
// Responsabilita': snapshot/restore per tipo, barra tag, auto-clone obbligatori.
// Riceve il form reattivo di useIndirizzoBase e le funzioni snapshot/restore di base.
// NON gestisce: form fields, validazione, payload, check duplicato (delegati a base/soggetto).

import { ref, computed } from 'vue'

export function useIndirizzoMultiTipo({ baseSnapshot, baseRestore, baseReset, form }) {
  const indirizziSalvati = ref({})
  const tipoAttivo = ref(null)
  const autoClone = ref(true)
  const tipiMatrice = ref([])

  // Stato tipi per barra tag UI
  const tipiStato = computed(() =>
    tipiMatrice.value.map(m => ({
      codice: m.codice,
      descrizione: m.descrizione,
      obbligatorio: m.obbligatorio,
      compilato: !!indirizziSalvati.value[m.codice],
      attivo: tipoAttivo.value === m.codice,
    }))
  )

  // Scopo: Inizializza la matrice tipi e seleziona il primo obbligatorio.
  function setMatrice(matrice) {
    tipiMatrice.value = matrice
    indirizziSalvati.value = {}
    const primo = matrice.find(m => m.obbligatorio) || matrice[0]
    if (primo) {
      tipoAttivo.value = primo.codice
      form.tipo_indirizzo_codice = primo.codice
    }
  }

  // --- Snapshot con campi soggetto ---
  function _snapshot() {
    return {
      ...baseSnapshot(),
      tipo_indirizzo_codice: form.tipo_indirizzo_codice,
      isLibera: form._isLibera,
      indirizzo_libero: form.indirizzo_libero,
      stato_id: form.stato_id,
      locality: form.locality,
    }
  }

  function _restore(snap) {
    baseRestore(snap)
    form.tipo_indirizzo_codice = snap.tipo_indirizzo_codice ?? null
    form._isLibera = snap.isLibera ?? false
    form.indirizzo_libero = snap.indirizzo_libero || ''
    form.stato_id = snap.stato_id ?? null
    form.locality = snap.locality || ''
  }

  // Scopo: Salva snapshot del tipo attivo (se compilato).
  function _salvaSnapshot() {
    if (!tipoAttivo.value) return
    if (!form.comune_id && !(form.indirizzo_libero || '').trim()) return
    indirizziSalvati.value[tipoAttivo.value] = _snapshot()
  }

  // Scopo: Carica snapshot di un tipo, o resetta se non salvato.
  function _caricaSnapshot(codice) {
    const snap = indirizziSalvati.value[codice]
    if (snap) {
      _restore(snap)
    } else {
      baseReset()
      form.tipo_indirizzo_codice = codice
      form._isLibera = false
      form.indirizzo_libero = ''
      form.stato_id = null
      form.locality = ''
    }
  }

  // Scopo: Switch tra tipi — salva attuale, carica target.
  function switchTipo(codice) {
    if (codice === tipoAttivo.value) return
    _salvaSnapshot()
    tipoAttivo.value = codice
    _caricaSnapshot(codice)
  }

  // Scopo: Salva snapshot corrente e prepara per toPayloadArray.
  function salvaSnapshot() {
    _salvaSnapshot()
  }

  // Scopo: Reset completo multi-tipo.
  function reset() {
    indirizziSalvati.value = {}
    tipoAttivo.value = null
    autoClone.value = true
    tipiMatrice.value = []
  }

  return {
    indirizziSalvati,
    tipoAttivo,
    autoClone,
    tipiMatrice,
    tipiStato,
    setMatrice,
    switchTipo,
    salvaSnapshot,
    reset,
  }
}
