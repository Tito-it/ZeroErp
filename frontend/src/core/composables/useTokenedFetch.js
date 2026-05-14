// Scopo: Pattern token "scarta risposte stantie" per fetch a contesto che
//        cambia rapidamente (cambio articolo, cambio riga, switch lookup).
//
//        Senza pattern token, due fetch concorrenti possono ritornare in
//        ordine inverso e l'ultima risposta arrivata vince — anche se non
//        corrisponde piu' al contesto corrente. Es. utente seleziona
//        articolo A (fetch lento), poi articolo B (fetch veloce): la
//        risposta B arriva, poi quella A sovrascrive con dati del vecchio
//        contesto.
//
//        Pattern: ogni fetch incrementa un counter monotono e ne salva
//        copia locale (`tk`); a risposta ricevuta, il caller confronta
//        `tk` col counter corrente — se diverso significa che e' partita
//        una fetch piu' nuova nel frattempo, la risposta corrente va
//        scartata.
//
//        Usato da: ComponentiDialog (preview), ContrattoRigheDrawer
//        (preview), useRigaComponenti (list), useArticoloUomOptions
//        (lookup UoM). Pattern allineato cross-codebase.
//
// Esempio d'uso:
//   const { nextToken, isCurrent, invalidate } = useTokenedFetch()
//   async function load(id) {
//     const tk = nextToken()
//     const res = await api.get(`/items/${id}/`)
//     if (!isCurrent(tk)) return  // risposta stantia, scarta
//     items.value = res.data
//   }
//
//   function reset() {
//     invalidate()  // invalida tutte le fetch in volo
//   }
//
// Pure JS, no Vue ref reattivo: il counter NON e' reattivo, vive nella
// closure dell'istanza. La reattivita' la decide il caller sul dato
// fetchato.
export function useTokenedFetch() {
  let _token = 0

  // Scopo: Genera il prossimo token incrementale per identificare la
  // fetch in volo. Da catturare localmente prima dell'await.
  function nextToken() {
    return ++_token
  }

  // Scopo: Verifica se `tk` e' ancora il token corrente. False se nel
  // frattempo e' partita una fetch piu' nuova (`nextToken()` chiamato
  // dopo `tk` ma prima di questo check) — la risposta va scartata.
  function isCurrent(tk) {
    return tk === _token
  }

  // Scopo: Invalida esplicitamente tutte le fetch in volo senza
  // emetterne una nuova. Usato per reset/cleanup (es. cambio riga padre
  // svuota la lista: invalidate impedisce a risposte vecchie di
  // ripopolare la lista appena svuotata).
  function invalidate() {
    _token++
  }

  return { nextToken, isCurrent, invalidate }
}
