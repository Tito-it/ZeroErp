// Store Pinia per la gestione impostazioni parametri.
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useParameterSettings } from '../../core/composables/useParameterSettings'

export const useImpostazioniStore = defineStore('config-impostazioni', () => {
  const { parameters, loading, load, saveOverride, removeOverride } = useParameterSettings()

  const searchText = ref('')

  // Scopo: Filtra i parametri per testo di ricerca (code o description).
  const filteredParameters = computed(() => {
    const q = (searchText.value || '').trim().toLowerCase()
    if (!q) return parameters.value
    return parameters.value.filter(p =>
      (p.code || '').toLowerCase().includes(q) ||
      (p.description || '').toLowerCase().includes(q)
    )
  })

  async function fetchList() {
    await load()
  }

  return {
    parameters,
    filteredParameters,
    loading,
    searchText,
    fetchList,
    saveOverride,
    removeOverride
  }
})
