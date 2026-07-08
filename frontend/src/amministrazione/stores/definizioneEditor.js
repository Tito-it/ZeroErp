// Store Pinia per il dettaglio strutturale di una singola edizione di workflow
// (editor FE Fase 3). Non e' una lista paginata → non usa createCrudStore: carica
// il payload dettaglio (definizione + steps con figli annidati + archi a livello
// edizione) da GET /definizioni/<id>/ e lo espone all'editor.
//
// FE-3.1 = sola lettura (ispettore). Gli anelli di editing (3.2 step, 3.3 figli,
// 3.4 archi) estenderanno questo store con le sotto-risorse CRUD.
//
// userScoped: contiene dati dell'edizione ispezionata dall'utente → reset al logout.

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDefinizioneDettaglio } from '../api/definizioniWorkflow'

export const useDefinizioneEditorStore = defineStore('amm-definizione-editor', () => {
  const definizione = ref(null)
  const steps = ref([])
  const archi = ref({ prerequisiti: [], formule_tempo: [], regole_generazione: [] })
  const loading = ref(false)
  const lastError = ref(false)

  async function load(definizioneId) {
    loading.value = true
    lastError.value = false
    try {
      const res = await getDefinizioneDettaglio(definizioneId)
      const data = res.data.data
      definizione.value = data.definizione
      steps.value = data.steps ?? []
      archi.value = data.archi ?? { prerequisiti: [], formule_tempo: [], regole_generazione: [] }
    } catch (e) {
      lastError.value = true
      definizione.value = null
      steps.value = []
      archi.value = { prerequisiti: [], formule_tempo: [], regole_generazione: [] }
      throw e
    } finally {
      loading.value = false
    }
  }

  function reset() {
    definizione.value = null
    steps.value = []
    archi.value = { prerequisiti: [], formule_tempo: [], regole_generazione: [] }
    lastError.value = false
  }

  return { definizione, steps, archi, loading, lastError, load, reset }
}, { userScoped: true })
