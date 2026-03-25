// Composable per verificare se un'azione di processo e' abilitata.
//
// Livello 2 permessi: le azioni processo controllano singole operazioni
// (es. genera_fatture_lotti, reset_lotto_draft) dentro un'area accessibile.
//
// Uso diretto (nei componenti):
//   const { isAllowed } = useActionPermission('genera_fatture_lotti')
//   <Button v-if="isAllowed" ... />
//
// Uso multiplo:
//   const auth = useAuthStore()
//   const canGenerate = computed(() => auth.isActionAllowed('genera_fatture_lotti'))
//   const canReset = computed(() => auth.isActionAllowed('reset_lotto_draft'))

import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth'

// Scopo: Verifica se un'azione di processo e' abilitata per l'utente corrente.
// Ritorna un computed reattivo che si aggiorna se cambiano i permessi.
export function useActionPermission(codename) {
  const auth = useAuthStore()
  const isAllowed = computed(() => auth.isActionAllowed(codename))
  return { isAllowed }
}
