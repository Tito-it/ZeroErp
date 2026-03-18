// Composable per modalita' sola lettura basata su permessi area funzionale.
//
// Pattern "protect" (AS/400): l'utente con livello LETTURA vede i dati
// ma non puo' interagire con form, pulsanti, drawer di scrittura.
//
// Uso nella View (provider):
//   const { isReadonly } = useReadonlyMode('anagrafiche')
//
// Uso nei componenti figli (consumer):
//   const isReadonly = useInjectReadonly()
//   // Template: :class="{ 'app-readonly': isReadonly }"

import { computed, provide, inject, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'

export const READONLY_KEY = Symbol('appReadonly')

// Provider: la View chiama questo composable con l'area funzionale.
// Fornisce isReadonly a tutti i componenti figli via provide.
export function useReadonlyMode(areaSchemaDb) {
  const auth = useAuthStore()
  const isReadonly = computed(() => auth.isAreaReadonly(areaSchemaDb))
  provide(READONLY_KEY, isReadonly)
  return { isReadonly }
}

// Consumer: i componenti figli (drawer, NewButton, DrawerFooter)
// iniettano il valore. Default false se nessun provider nell'albero.
export function useInjectReadonly() {
  return inject(READONLY_KEY, ref(false))
}
