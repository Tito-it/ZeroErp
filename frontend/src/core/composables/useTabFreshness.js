// Composable centralizzato per inter-tab freshness.
// Sottoscrive onDataChanged per un entityType e chiama store.fetchList() automaticamente.
// Cleanup automatico su onUnmounted.
//
// Uso:
//   useTabFreshness(store, 'utente')

import { onUnmounted } from 'vue'
import { useTabEvents } from './useTabEvents'

export function useTabFreshness(store, entityType) {
  const { onDataChanged } = useTabEvents()
  const cleanup = onDataChanged(e => {
    if (e.entityType === entityType) store.fetchList().catch(() => {})
  })
  onUnmounted(() => { cleanup() })
}
