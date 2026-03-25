import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// Mappa tipo ruolo -> icona PrimeIcons
const TIPO_RUOLO_ICONS = {
  CLIENTE: 'pi pi-user',
  FORNITORE: 'pi pi-truck',
  VENDITORE: 'pi pi-briefcase',
  DISTRIB: 'pi pi-share-alt',
  RESELLER: 'pi pi-shop',
  VETTORE: 'pi pi-car',
  BANK: 'pi pi-building-columns'
}

// Mappa tipo ruolo -> severity chip PrimeVue
const TIPO_RUOLO_SEVERITY = {
  CLIENTE: 'info',
  FORNITORE: 'warn',
  VENDITORE: 'success',
  DISTRIB: 'secondary',
  RESELLER: 'contrast',
  VETTORE: 'secondary',
  BANK: 'danger'
}

export const useContextStore = defineStore('context', () => {
  const tipoRuoloId = ref(null)
  const tipoRuoloCodice = ref(null)
  const soggettoId = ref(null)
  const soggettoRuoloId = ref(null)
  const entitaId = ref(null)
  const label = ref('')
  const meta = ref(null)
  const searchTerm = ref('')

  const hasContext = computed(() => !!soggettoId.value)

  const contextLabel = computed(() => label.value || '')

  const contextIcon = computed(() => {
    return TIPO_RUOLO_ICONS[tipoRuoloCodice.value] || 'pi pi-user'
  })

  const contextSeverity = computed(() => {
    return TIPO_RUOLO_SEVERITY[tipoRuoloCodice.value] || 'secondary'
  })

  // Scopo: imposta il contesto globale con l'entita' selezionata dalla ricerca
  function setContext(payload) {
    tipoRuoloId.value = payload.tipo_ruolo_id
    tipoRuoloCodice.value = payload.tipo_ruolo_codice || null
    soggettoId.value = payload.soggetto_id
    soggettoRuoloId.value = payload.soggetto_ruolo_id
    entitaId.value = payload.entita_id || null
    label.value = payload.label || ''
    meta.value = payload.meta || null
    searchTerm.value = payload.searchTerm || ''
  }

  // Scopo: rimuove il contesto globale, torna a navigazione non filtrata
  function clearContext() {
    tipoRuoloId.value = null
    tipoRuoloCodice.value = null
    soggettoId.value = null
    soggettoRuoloId.value = null
    entitaId.value = null
    label.value = ''
    meta.value = null
    searchTerm.value = ''
  }

  return {
    tipoRuoloId,
    tipoRuoloCodice,
    soggettoId,
    soggettoRuoloId,
    entitaId,
    label,
    meta,
    searchTerm,
    hasContext,
    contextLabel,
    contextIcon,
    contextSeverity,
    setContext,
    clearContext
  }
})
