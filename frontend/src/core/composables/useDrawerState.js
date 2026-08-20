// Composable centralizzato per gestione stato drawer (create/edit).
// Usa reactive() per garantire che le proprietà siano reattive e scrivibili
// nei template senza .value (i ref annidati in oggetti plain non si unwrappano).
//
// Uso:
//   const drawer = useDrawerState()
//   // Template: :visible="drawer.state.visible" @update:visible="v => drawer.state.visible = v"
//   //           :mode="drawer.state.mode" :item="drawer.state.itemData"

import { reactive } from 'vue'
import { registraDrawerChiudibile } from './useDrawerChiusuraGlobale'

export function useDrawerState() {
  const state = reactive({
    visible: false,
    mode: 'create',
    itemId: null,
    itemData: null
  })

  function openCreate() {
    state.mode = 'create'
    state.itemId = null
    state.itemData = null
    state.visible = true
  }

  function editRow(rowData, idField = 'id') {
    state.mode = 'edit'
    state.itemId = rowData[idField]
    state.itemData = rowData
    state.visible = true
  }

  function close() {
    state.visible = false
  }

  // Il drawer di testa risponde alla chiusura globale: quando qualcosa porta
  // l'utente su un'altra rotta, questo pannello non deve restare davanti alla
  // pagina d'arrivo. Vedi `useDrawerChiusuraGlobale` per il perche' il segnale
  // e' uno solo e non un evento per drawer.
  // ⚠️ Si chiude solo cio' che e' APERTO. Qui `close` non ha effetti collaterali
  // (setta un flag), ma la regola vale per tutti i registrati: la chiusura
  // globale scatta a ogni cambio di rotta, e un callback che fa qualcosa su un
  // drawer gia' chiuso lo fa per sempre, a ogni navigazione. E' cosi' che il
  // primo giro produsse `/vendite/commesse/null/stato/` (vedi useDocumentoDrawer).
  registraDrawerChiudibile(() => {
    if (state.visible) close()
  })

  return { state, openCreate, editRow, close }
}
