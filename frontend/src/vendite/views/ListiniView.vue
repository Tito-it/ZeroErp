<script setup>
// Scopo: Vista principale gestione listini vendite.
import { ref } from 'vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useListiniStore } from '../stores/listini'
import ListiniSearchTable from '../components/ListiniSearchTable.vue'
import ListinoDrawer from '../components/ListinoDrawer.vue'
import ListinoVersioniDrawer from '../components/ListinoVersioniDrawer.vue'
import ListinoAssociazioniDrawer from '../components/ListinoAssociazioniDrawer.vue'
import TestResolverDialog from '../components/TestResolverDialog.vue'

const drawer = useDrawerState()
const store = useListiniStore()
useReadonlyMode('vendite')

// Sub-drawer autonomi (istanza unica per view)
const versioniVisible = ref(false)
const versioniListinoId = ref(null)
const associazioniVisible = ref(false)
const associazioniListinoId = ref(null)
const resolverVisible = ref(false)

async function onDrawerSaved(result) {
  store.filters.offset = 0
  await store.fetchList()
  if (result && result.id && drawer.state.mode === 'create') {
    drawer.editRow({ id: result.id }, 'id')
  } else {
    drawer.close()
  }
}

function onOpenVersioni(data) {
  versioniListinoId.value = data.id
  versioniVisible.value = true
}

function onOpenAssociazioni(data) {
  associazioniListinoId.value = data.id
  associazioniVisible.value = true
}

function onSubDrawerSaved() {
  store.fetchList()
}
</script>

<template>
  <div class="app-page">
    <ListiniSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @open-versioni="onOpenVersioni"
      @open-associazioni="onOpenAssociazioni"
      @test-resolver="resolverVisible = true"
    />

    <ListinoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :listino-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
      @open-versioni="onOpenVersioni"
      @open-associazioni="onOpenAssociazioni"
    />

    <!-- Drawer autonomi dalla lista -->
    <ListinoVersioniDrawer
      :visible="versioniVisible"
      @update:visible="v => versioniVisible = v"
      :listino-id="versioniListinoId"
      @saved="onSubDrawerSaved"
    />
    <ListinoAssociazioniDrawer
      :visible="associazioniVisible"
      @update:visible="v => associazioniVisible = v"
      :listino-id="associazioniListinoId"
      @saved="onSubDrawerSaved"
    />

    <TestResolverDialog v-if="resolverVisible"
      :visible="resolverVisible"
      @update:visible="v => resolverVisible = v" />
  </div>
</template>
