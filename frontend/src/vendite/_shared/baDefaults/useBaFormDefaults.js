// Scopo: al cambio billing_account in CREATE, recupera i default BA-derived
// dal BE (BB `resolve_valuta_default`) e li applica al form, con guard
// latest-wins contro risposte stantie. Condiviso dai drawer testata vendite
// (preventivi / offerte / contratti) — estrazione "regola del 2" del watcher
// valuta/default-BA, prima triplicato. La guard token, che originariamente
// aveva solo PreventiviDrawer, vale ora per tutti e tre (fix bug latente
// race-condition su apertura/chiusura veloce o cambi BA rapidi).
//
// NON gestisce `onBaSelected` (set utility/istanza/categoria): quella logica
// diverge per dominio e resta nel singolo drawer.
import { watch } from 'vue'

// Scopo: registra il watch su `form.value.billing_account_id` con guard
// edit/no-op/token. `fetchDefaults(baId)` è la fn API del dominio; `apply`
// (opzionale) applica i default extra specifici di dominio (es. termine
// pagamento) dopo che la valuta è stata risolta.
export function useBaFormDefaults({ form, isEdit, fetchDefaults, apply = null }) {
  let token = 0
  watch(() => form.value.billing_account_id, async (newBaId, oldBaId) => {
    if (isEdit.value) return
    if (!newBaId || newBaId === oldBaId) return
    const tk = ++token
    let res
    try {
      res = await fetchDefaults(newBaId)
    } catch {
      // Best-effort: errore form-defaults non blocca il CREATE.
      // Il trigger DB risolverà comunque la valuta al save.
      return
    }
    // Apertura/chiusura veloce o cambio BA rapido: scarta la risposta stantia.
    if (tk !== token) return
    const data = res?.data?.data
    if (!data) return
    // Valuta: il BA (o il suo EF) vince sempre sulla valuta dell'EF utente
    // caricata al mount (regola di coerenza dominio "valuta del BA wins").
    if (data.valuta_id != null) {
      form.value.valuta_id = data.valuta_id
    }
    // Default aggiuntivi specifici di dominio (sovrascrivono solo se vuoti,
    // a discrezione del callback).
    if (apply) apply(data, form.value)
  })
}
