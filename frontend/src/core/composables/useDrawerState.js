// Composable centralizzato per gestione stato drawer (create/edit).
// Usa reactive() per garantire che le proprietà siano reattive e scrivibili
// nei template senza .value (i ref annidati in oggetti plain non si unwrappano).
//
// Uso:
//   const drawer = useDrawerState()
//   // Template: :visible="drawer.state.visible" @update:visible="v => drawer.state.visible = v"
//   //           :mode="drawer.state.mode" :item="drawer.state.itemData"

import { reactive } from 'vue'

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

  return { state, openCreate, editRow, close }
}
