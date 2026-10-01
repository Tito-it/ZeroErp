import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
// Icona del tipo ruolo: la mappa vive accanto a NAV_ICONS (censimento icone
// §3.1d), qui si legge soltanto.
import { resolveTipoRuoloIcon } from '../core/navigation'

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

// userScoped: true => il plugin `autoResetPlugin` include questo store nel
// reset centralizzato al logout. Pure in-memory, nessun side-effect su
// storage, quindi snapshot iniziale sufficiente (no clearUserState custom).
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
    return resolveTipoRuoloIcon(tipoRuoloCodice.value)
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
}, {
  userScoped: true
})
