// Scopo: Composable generico per check duplicato indirizzo.
// Riutilizzabile da IndirizzoDrawer e IndirizzoSoggettoForm.
// Chiama POST /indirizzi/check-duplicato/ e ritorna warnings.

import { ref } from 'vue'
import { checkIndirizzoDuplicato } from '../../anagrafiche/api/anagrafiche'

export function useIndirizzoDuplicato() {
  const indirizzoWarnings = ref([])

  async function checkDuplicato(stradarioId, civico) {
    indirizzoWarnings.value = []
    if (!stradarioId) return
    try {
      const res = await checkIndirizzoDuplicato({
        stradario_id: stradarioId,
        civico: civico || null,
      })
      indirizzoWarnings.value = res.data.data.warnings.map(w => w.message)
    } catch {
      indirizzoWarnings.value = []
    }
  }

  function resetWarnings() {
    indirizzoWarnings.value = []
  }

  return { indirizzoWarnings, checkDuplicato, resetWarnings }
}
