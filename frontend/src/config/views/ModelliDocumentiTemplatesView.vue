<script setup>
// Scopo: Vista Configurazione "Modelli documenti — Template" (Tranche L).
//        Pattern coerente con CategorieClientiListView: SearchTable
//        emette `new` / `row-click` -> drawer crea/edit.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { useTemplateDocumentiStore } from '../stores/templateDocumenti'
import TemplateDocumentiSearchTable from '../components/TemplateDocumentiSearchTable.vue'
import TemplateDocumentoDrawer from '../components/TemplateDocumentoDrawer.vue'

const drawer = useDrawerState()
const store = useTemplateDocumentiStore()

// I template documentali appartengono allo schema/area `documenti`, non
// `config` (la navigazione e' in config solo per UX/raggruppamento).
// L'area BE che enforce i permessi e' `documenti` -> coerentemente il
// readonly e i guard FE devono essere calcolati sulla stessa area.
useReadonlyMode(READONLY_DOMAINS.DOCUMENTI)

async function onDrawerSaved(result) {
  const wasCreate = drawer.state.mode === 'create'
  store.filters.offset = 0
  await store.fetchList()
  if (wasCreate && result?.id) {
    // Dopo il primo save la testata esiste: il drawer resta aperto in edit
    // e mostra la sezione versioni.
    drawer.state.mode = 'edit'
    drawer.state.itemId = result.id
    return
  }
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <TemplateDocumentiSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <TemplateDocumentoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
