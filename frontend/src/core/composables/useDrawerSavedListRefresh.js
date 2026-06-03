// Composable: handler standard "salvataggio drawer → refresh lista".
// Estrae il pattern ripetuto identico in piu' viste lista+drawer:
//   reset offset → ricarica lista → se era una CREATE riapre la riga in edit
//   (per gestire le sotto-entita: contatti/indirizzi/banca/...), altrimenti chiude.
//
// Uso:
//   const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)
//   // template: <EntityDrawer @saved="onDrawerSaved" />
//
// Dipendenze (duck-typing, nessun accoppiamento a uno store specifico):
//   store:  { filters: { offset }, fetchList() }
//   drawer: useDrawerState() — { state: { mode }, editRow(), close() }

// Scopo: costruisce l'handler onDrawerSaved legato a (store, drawer).
export function useDrawerSavedListRefresh(store, drawer) {
  // Scopo: dopo il salvataggio ricarica la lista; se era una creazione
  //        riapre la riga in edit per gestire le sotto-entita, altrimenti chiude.
  async function onDrawerSaved(result) {
    store.filters.offset = 0
    await store.fetchList()
    if (result && result.id && drawer.state.mode === 'create') {
      drawer.editRow({ id: result.id }, 'id')
    } else {
      drawer.close()
    }
  }

  return { onDrawerSaved }
}
