// Composable per modalita' sola lettura e blocco accesso area funzionale.
//
// Pattern "protect" (AS/400): l'utente con livello LETTURA vede i dati
// ma non puo' interagire con form, pulsanti, drawer di scrittura.
// L'utente con livello BLOCCATO non accede all'area (route guard + sidebar).
//
// Uso nella View (provider):
//   const { isReadonly, isBlocked } = useReadonlyMode('anagrafiche')
//
// Uso nei componenti figli (consumer):
//   const isReadonly = useInjectReadonly()
//   const isBlocked = useInjectBlocked()

import { computed, provide, inject, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'

export const READONLY_KEY = Symbol('appReadonly')
export const BLOCKED_KEY = Symbol('appBlocked')

// Provider: la View chiama questo composable con l'area funzionale.
// Fornisce isReadonly e isBlocked a tutti i componenti figli via provide.
// Se un parent ha gia' fornito readonly=true (es. SplitReadonlyPanel),
// il valore viene propagato con OR — il pannello split forza readonly
// indipendentemente dai permessi dell'operatore.
export function useReadonlyMode(areaSchemaDb) {
  const auth = useAuthStore()
  const parentReadonly = inject(READONLY_KEY, ref(false))
  const isReadonly = computed(() => parentReadonly.value || auth.isAreaReadonly(areaSchemaDb))
  const isBlocked = computed(() => auth.isAreaBlocked(areaSchemaDb))
  provide(READONLY_KEY, isReadonly)
  provide(BLOCKED_KEY, isBlocked)
  return { isReadonly, isBlocked }
}

// Consumer: i componenti figli (drawer, NewButton, DrawerFooter)
// iniettano il valore. Default false se nessun provider nell'albero.
export function useInjectReadonly() {
  return inject(READONLY_KEY, ref(false))
}

// Consumer: componenti che devono reagire al livello BLOCCATO.
// In pratica il route guard blocca prima, questo e' una safety net.
export function useInjectBlocked() {
  return inject(BLOCKED_KEY, ref(false))
}
