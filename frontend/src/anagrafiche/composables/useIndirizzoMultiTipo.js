// Scopo: Composable per gestione multi-tipo indirizzo soggetto.
// Responsabilita': snapshot/restore per tipo, barra tag, auto-clone obbligatori.
// Riceve il form reattivo di useIndirizzoBase e le funzioni snapshot/restore di base.
// NON gestisce: form fields, validazione, payload, check duplicato (delegati a base/soggetto).

import { ref, computed } from 'vue'
import { assegnaCampiLiberi, campiLiberi } from './indirizzoLibero'

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

  // Scopo: Inizializza la matrice tipi e seleziona il primo obbligatorio disponibile.
  // excludeCodici: Set di codici gia' esistenti da non pre-selezionare.
  function setMatrice(matrice, excludeCodici = null) {
    tipiMatrice.value = matrice
    indirizziSalvati.value = {}
    const disponibili = excludeCodici
      ? matrice.filter(m => !excludeCodici.has(m.codice))
      : matrice
    const primo = disponibili.find(m => m.obbligatorio) || disponibili[0] || null
    if (primo) {
      tipoAttivo.value = primo.codice
      form.tipo_indirizzo_codice_interno = primo.codice
    } else {
      tipoAttivo.value = null
      form.tipo_indirizzo_codice_interno = null
    }
  }

  // --- Snapshot con campi soggetto ---
  function _snapshot() {
    return {
      ...baseSnapshot(),
      tipo_indirizzo_codice_interno: form.tipo_indirizzo_codice_interno,
      isLibera: form._isLibera,
      ...campiLiberi(form),
    }
  }

  function _restore(snap) {
    baseRestore(snap)
    form.tipo_indirizzo_codice_interno = snap.tipo_indirizzo_codice_interno ?? null
    form._isLibera = snap.isLibera ?? false
    assegnaCampiLiberi(form, snap)
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
      form.tipo_indirizzo_codice_interno = codice
      form._isLibera = false
      assegnaCampiLiberi(form)
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
