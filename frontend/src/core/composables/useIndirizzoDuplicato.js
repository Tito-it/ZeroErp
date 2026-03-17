// Scopo: Composable generico per check duplicato indirizzo.
// Riutilizzabile da IndirizzoDrawer e IndirizzoSoggettoForm.
// Chiama POST /indirizzi/check-duplicato/ e ritorna warnings + id esistente.
// Distingue match esatto (indirizzo identico) da match prefix (simile).

import { ref } from 'vue'
import { checkIndirizzoDuplicato } from '../../anagrafiche/api/anagrafiche'

export function useIndirizzoDuplicato() {
  // Warning info mostrati nel form (solo per match esatti)
  const indirizzoWarnings = ref([])
  // ID dell'indirizzo dettaglio trovato (solo match esatto, per riuso diretto)
  const existingDettaglioId = ref(null)

  // Scopo: Check duplicato con tutti i campi civico.
  async function checkDuplicato(params) {
    indirizzoWarnings.value = []
    existingDettaglioId.value = null
    if (!params.stradario_id) return
    try {
      const res = await checkIndirizzoDuplicato(params)
      const warnings = res.data.data.warnings || []
      if (warnings.length > 0) {
        const w = warnings[0]
        if (w.exact_match) {
          // Match esatto: mostra info + imposta id per riuso
          indirizzoWarnings.value = [w.message]
          existingDettaglioId.value = w.indirizzo_dettaglio_id
        }
        // Match prefix (non esatto): nessun warning info, nessun id.
        // Il parent (addressNotFound) gestisce il messaggio warn.
      }
    } catch {
      indirizzoWarnings.value = []
      existingDettaglioId.value = null
    }
  }

  function resetWarnings() {
    indirizzoWarnings.value = []
    existingDettaglioId.value = null
  }

  return { indirizzoWarnings, existingDettaglioId, checkDuplicato, resetWarnings }
}
