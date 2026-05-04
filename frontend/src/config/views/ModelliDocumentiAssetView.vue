<script setup>
// Scopo: Vista Configurazione "Modelli documenti — Asset" (Tranche L).
//        Lista asset documentali + upload (multipart). DELETE bloccata
//        a livello DB: la disattivazione e' soft via PATCH attivo=false.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { useTemplateAssetDocumentiStore } from '../stores/templateAssetDocumenti'
import TemplateAssetSearchTable from '../components/TemplateAssetSearchTable.vue'
import TemplateAssetDrawer from '../components/TemplateAssetDrawer.vue'

const drawer = useDrawerState()
const store = useTemplateAssetDocumentiStore()

useReadonlyMode(READONLY_DOMAINS.CONFIG)

async function onDrawerSaved() {
  store.filters.offset = 0
  await store.fetchList()
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <TemplateAssetSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <TemplateAssetDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
