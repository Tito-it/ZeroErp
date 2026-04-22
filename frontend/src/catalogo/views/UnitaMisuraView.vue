<script setup>
// Scopo: Vista principale gestione unita' di misura.
//        Drawer UoM + sub-drawer conversioni apribile dalla lista.
import { ref } from 'vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useUnitaMisuraStore } from '../stores/unitaMisura'
import UnitaMisuraSearchTable from '../components/UnitaMisuraSearchTable.vue'
import UnitaMisuraDrawer from '../components/UnitaMisuraDrawer.vue'
import UomConversioniDrawer from '../components/UomConversioniDrawer.vue'

const drawer = useDrawerState()
const store = useUnitaMisuraStore()
useReadonlyMode(READONLY_DOMAINS.CATALOGO, READONLY_MODELS.UNITA_MISURA)

// Sub-drawer conversioni
const convDrawerVisible = ref(false)
const convUomId = ref(null)
const convUomCodice = ref('')

async function onDrawerSaved(result) {
  store.filters.offset = 0
  await store.fetchList()
  if (result && result.id && drawer.state.mode === 'create') {
    drawer.editRow({ id: result.id }, 'id')
  } else {
    drawer.close()
  }
}

function onManageConversioni(data) {
  convUomId.value = data.id
  convUomCodice.value = data.codice || ''
  convDrawerVisible.value = true
}
</script>

<template>
  <div class="app-page">
    <UnitaMisuraSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @manage-conversioni="onManageConversioni"
    />

    <UnitaMisuraDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :uom-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <UomConversioniDrawer
      :visible="convDrawerVisible"
      @update:visible="v => convDrawerVisible = v"
      :uom-id="convUomId"
      :uom-codice="convUomCodice"
    />
  </div>
</template>
