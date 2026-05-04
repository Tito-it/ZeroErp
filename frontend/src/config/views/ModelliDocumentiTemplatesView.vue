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

useReadonlyMode(READONLY_DOMAINS.CONFIG)

async function onDrawerSaved() {
  // Su create il drawer evolve a edit (versioni inline) - manteniamo aperto.
  // Su update teniamo aperto per consentire ulteriori modifiche.
  // Aggiorniamo solo la lista in background.
  store.filters.offset = 0
  await store.fetchList()
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
