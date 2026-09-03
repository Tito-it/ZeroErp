// Composable: gli handler standard "il drawer ha cambiato qualcosa → la lista
// dietro è stantia". Estrae il pattern ripetuto identico in piu' viste
// lista+drawer:
//   reset offset → ricarica lista → se era una CREATE riapre la riga in edit
//   (per gestire le sotto-entita: contatti/indirizzi/banca/...), altrimenti chiude.
//
// Uso:
//   const { onDrawerSaved, onDrawerChanged } = useDrawerSavedListRefresh(store, drawer)
//   // template: <EntityDrawer @saved="onDrawerSaved" @changed="onDrawerChanged" />
//
// Dipendenze (duck-typing, nessun accoppiamento a uno store specifico):
//   store:  { filters: { offset }, fetchList() }
//   drawer: useDrawerState() — { state: { mode }, editRow(), close() }
//
// ── ⭐ DUE EVENTI, E LA DIFFERENZA E' *SE IL LAVORO E' FINITO* ────────────────
//
//   `saved`   → l'atto CHIUDE il lavoro sul documento: si ricarica la lista e
//               si chiude il drawer (o si riapre in edit, dopo una create).
//   `changed` → l'atto ha cambiato la riga ma il lavoro CONTINUA: si ricarica
//               la lista e il drawer **resta aperto**.
//
// 🔴 NASCE DA UN DIFETTO TROVATO IN COLLAUDO (Tid, 2026-09-01, prova A di
//    `collaudo-in-app-v2-dl23-e-area-resi`): generato un DDT da un ordine, la
//    lista ordini restava indietro e il transito «In corso · DDT DRAFT»
//    compariva solo ricaricando a mano. Cercando il gemello sono emerse
//    **quattro** copie dello stesso momento — «il drawer genera un documento e
//    il lavoro prosegue» — con **tre** comportamenti diversi:
//
//    | Dominio     | Callback                          | Notificava la lista        |
//    | ----------- | --------------------------------- | -------------------------- |
//    | ordini      | `onEvaso` (genera DDT)            | ⛔ niente                   |
//    | ddt         | `onResoCreato` (genera reso)      | ⛔ niente                   |
//    | preventivi  | `onSmistato` (genera ordine)      | solo l'ALTRA tab, non la sua |
//    | resi        | `onCoperturaRiconsegnaCambiata`   | `saved` → **chiudeva** il drawer |
//
//    ⭐ Nessuna delle quattro falliva: due tacevano, una faceva una cosa in
//    piu'. E' la forma di difetto che nessun test vede — la pagina non sbaglia,
//    e' solo **ferma** ([[feedback_duplicazione_nasconde_il_bug]]: due copie
//    sono gia' divergenti quando le trovi).
//
// ⚠️ Il nome `changed` NON e' nuovo: e' quello che LottoDrawer→LottiListView e
//    la dashboard competenza usano gia' per la stessa cosa («riallinea senza
//    chiudere»). Qui viene reso disponibile a tutte le liste invece di restare
//    un accordo privato fra due componenti.

// Scopo: costruisce gli handler legati a (store, drawer).
// `riapriDopoCreate = false` per i drawer che gestiscono da se' la transizione
// CREATE → "edit-evolved" (auto-save bozza): li' una riapertura dall'esterno
// rimonterebbe il drawer sotto le mani di chi sta scrivendo.
export function useDrawerSavedListRefresh(
  store, drawer, { riapriDopoCreate = true, soloSeCercata = false } = {},
) {
  // Scopo: la ricarica vera, in UNA sede — la usano entrambi gli handler.
  //
  // ⚠️ `soloSeCercata` — NON e' una preferenza, e non e' ridondante. La prima
  //    stesura di questo BB lo aveva omesso sostenendo che il controllo fosse
  //    «gia' dentro `fetchList`». **E' falso su queste liste**: la guardia
  //    empty-state di `useListaEmptyStateFetch` scatta solo con
  //    `!searchTerm && !hasActiveFilters(f)`, e le cinque liste documento
  //    nascono con `data_da` valorizzato dal default standard — che *conta come
  //    filtro attivo* (lo dice il commento di `ordini.js`). Quindi li' la
  //    guardia non scatta mai e `fetchList` va davvero in rete.
  //
  // ⛔ Senza questo parametro, salvare da un drawer su una lista che
  //    l'operatore non ha mai cercato la **riempirebbe**, buttando via lo stato
  //    vuoto che quelle liste hanno di proposito.
  //
  // 📌 E il default `false` NON e' una svista: i sette adottanti storici oggi
  //    ricaricano **sempre**, e quattro di loro un `hasSearched` ce l'hanno.
  //    Unificare i due comportamenti e' una decisione di UX — non una cosa che
  //    un BB puo' prendersi di straforo cambiando cio' che l'operatore vede in
  //    sette schermate.
  async function ricaricaLista() {
    store.filters.offset = 0
    if (soloSeCercata && !store.hasSearched) return
    await store.fetchList()
  }

  // Scopo: dopo il salvataggio ricarica la lista; se era una creazione
  //        riapre la riga in edit per gestire le sotto-entita, altrimenti chiude.
  async function onDrawerSaved(result) {
    await ricaricaLista()
    if (riapriDopoCreate && result && result.id && drawer.state.mode === 'create') {
      drawer.editRow({ id: result.id }, 'id')
    } else {
      drawer.close()
    }
  }

  // Scopo: la riga e' cambiata ma il lavoro non e' finito — ricarica la lista e
  //        LASCIA IL DRAWER APERTO.
  // ⛔ Non chiama `drawer.close()`, ed e' tutta la sua ragione di esistere: un
  //    drawer che si chiude da solo mentre l'operatore sta ancora lavorando e'
  //    il difetto che questo handler toglie, non una sua omissione.
  async function onDrawerChanged() {
    await ricaricaLista()
  }

  return { onDrawerSaved, onDrawerChanged }
}
