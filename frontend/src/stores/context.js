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
  const label = ref('')
  const meta = ref(null)

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
    label.value = payload.label || ''
    meta.value = payload.meta || null
  }

  // Scopo: rimuove il contesto globale, torna a navigazione non filtrata
  function clearContext() {
    tipoRuoloId.value = null
    tipoRuoloCodice.value = null
    soggettoId.value = null
    soggettoRuoloId.value = null
    label.value = ''
    meta.value = null
  }

  return {
    tipoRuoloId,
    tipoRuoloCodice,
    soggettoId,
    soggettoRuoloId,
    label,
    meta,
    hasContext,
    contextLabel,
    contextIcon,
    contextSeverity,
    setContext,
    clearContext
  }
})
