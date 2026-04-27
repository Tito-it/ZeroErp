<script setup>
// Scopo: vista principale Gestione Pratiche.
// SearchTable + Drawer creazione/dettaglio.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { usePraticheStore } from '../stores/pratiche'
import PraticheSearchTable from '../components/PraticheSearchTable.vue'
import PraticaDrawer from '../components/PraticaDrawer.vue'

const drawer = useDrawerState()
const store = usePraticheStore()
useReadonlyMode(READONLY_DOMAINS.PRATICHE)

// Scopo: Dopo salvataggio, ricarica lista e chiudi drawer.
async function onDrawerSaved() {
  store.filters.offset = 0
  await store.fetchList()
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <PraticheSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <PraticaDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :pratica-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
