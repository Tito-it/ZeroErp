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
import { ref, watch } from 'vue'

// Scopo: registra il watch su `form.value.billing_account_id` con guard
// edit/no-op/token, e restituisce `applicaDefaults(baId)` per i drawer che
// devono applicare i default anche all'APERTURA — non solo al cambio BA.
//
// ⚠️ Perché `applicaDefaults` è esposta (fix 2026-08-04, segnalazione di Tid
// «pagamento vuoto» sul PDF preventivo). Il watch scatta su un CAMBIO: quando
// il BA arriva già precompilato (percorso pratica-first: `prefillFromPratica`
// lo imposta all'apertura) non c'è nessun cambio da osservare, quindi i
// default BA-derived non venivano mai applicati. Il drawer preventivi
// compensava con una fetch propria all'apertura che però applicava **solo la
// valuta**, scartando `termine_pagamento_id` — che era nella stessa risposta.
// Risultato misurato: 141 preventivi su 163 senza termine di pagamento, e un
// PDF con «Pagamento: -» anche per clienti che il termine ce l'hanno.
// Ora la logica di applicazione è una sola e la usano entrambe le strade.
//
// ⛔ `inCorso` (2026-10-14): vero finché la risposta del cliente non è
// arrivata. Il drawer lo mette nel suo `canSave`: un Salva premuto prima
// spediva il form SENZA i dati del cliente, e il DB li prendeva per scelte
// dell'operatore — sul contratto la scheda di fornitura vuota sopra quella
// dell'anagrafica, sul preventivo il termine di pagamento perso. Nessun
// errore: un documento salvato con meno di quello che il cliente porta.
export function useBaFormDefaults({ form, isEdit, fetchDefaults, apply = null }) {
  let token = 0
  const inCorso = ref(false)

  // Scopo: recupera e applica i default per un BA (o senza, `null`: il BE
  //   risolve la valuta dall'EF dell'utente). Best-effort: un errore non
  //   blocca il CREATE, il trigger DB risolverà comunque la valuta al save.
  async function applicaDefaults(baId) {
    const tk = ++token
    inCorso.value = true
    let res
    try {
      res = await fetchDefaults(baId ?? null)
    } catch {
      if (tk === token) inCorso.value = false
      return
    }
    // Apertura/chiusura veloce o cambio BA rapido: scarta la risposta stantia.
    // `inCorso` lo spegne solo l'ultima richiesta, quella che conta.
    if (tk !== token) return
    inCorso.value = false
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
  }

  watch(() => form.value.billing_account_id, (newBaId, oldBaId) => {
    if (isEdit.value) return
    if (!newBaId || newBaId === oldBaId) return
    applicaDefaults(newBaId)
  })

  return { applicaDefaults, inCorso }
}
