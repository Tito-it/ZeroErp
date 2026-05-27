// Composable per modalita' sola lettura e blocco accesso area funzionale.
//
// Pattern "protect" (AS/400): l'utente con livello LETTURA vede i dati
// ma non puo' interagire con form, pulsanti, drawer di scrittura.
// L'utente con livello BLOCCATO non accede all'area (route guard + sidebar).
//
// Uso nella View (provider) — livello area:
//   const { isReadonly, isBlocked } = useReadonlyMode('anagrafiche')
//
// Uso nella View (provider) — livello oggetto (v2):
//   const { isReadonly, isBlocked } = useReadonlyMode('anagrafiche', 'conto_bancario')
//   Se l'operatore ha un override oggetto, viene usato. Altrimenti fallback area.
//
// Uso nei componenti figli (consumer):
//   const isReadonly = useInjectReadonly()
//   const isBlocked = useInjectBlocked()
//
// Convenzione (non rompere): chi fa `provide(READONLY_KEY, ...)` DEVE
// includere `inject(READONLY_KEY)` nell'OR. Sovrascrivere senza OR rompe
// la propagazione del readonly da contesti superiori (SplitReadonlyPanel,
// LETTURA area/oggetto, drawer parent in stato locked).

import { computed, provide, inject, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'

export const READONLY_KEY = Symbol('appReadonly')
export const BLOCKED_KEY = Symbol('appBlocked')

// Provider: la View chiama questo composable con l'area funzionale e
// opzionalmente il model per granularita' oggetto (v2 permessi).
// Fornisce isReadonly e isBlocked a tutti i componenti figli via provide.
// Se un parent ha gia' fornito readonly=true (es. SplitReadonlyPanel),
// il valore viene propagato con OR — il pannello split forza readonly
// indipendentemente dai permessi dell'operatore.
export function useReadonlyMode(areaSchemaDb, modelName = null) {
  const auth = useAuthStore()
  const parentReadonly = inject(READONLY_KEY, ref(false))
  // isReadonly = true se LETTURA (area o oggetto) oppure BLOCCATO **solo
  // per livello oggetto**. A livello area il route guard gestisce BLOCCATO
  // impedendo la navigazione → se l'utente e' nella pagina, non e' bloccato.
  // Per livello oggetto invece l'utente naviga nell'area liberamente e
  // puo' trovare BLOCCATO su specifici model → serve il blocco UI.
  const isReadonly = computed(() => {
    if (parentReadonly.value) return true
    if (modelName) {
      return auth.isObjectReadonly(areaSchemaDb, modelName)
          || auth.isObjectBlocked(areaSchemaDb, modelName)
    }
    return auth.isAreaReadonly(areaSchemaDb)
  })
  const isBlocked = computed(() =>
    modelName
      ? auth.isObjectBlocked(areaSchemaDb, modelName)
      : auth.isAreaBlocked(areaSchemaDb)
  )
  provide(READONLY_KEY, isReadonly)
  provide(BLOCKED_KEY, isBlocked)
  return { isReadonly, isBlocked }
}

// Consumer: i componenti figli (drawer, NewButton, FormFooter)
// iniettano il valore. Default false se nessun provider nell'albero.
export function useInjectReadonly() {
  return inject(READONLY_KEY, ref(false))
}

// Consumer: componenti che devono reagire al livello BLOCCATO.
// In pratica il route guard blocca prima, questo e' una safety net.
export function useInjectBlocked() {
  return inject(BLOCKED_KEY, ref(false))
}
