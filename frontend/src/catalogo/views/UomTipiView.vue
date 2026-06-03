<script setup>
// Scopo: Vista principale gestione tipologie UoM.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useUomTipiStore } from '../stores/uomTipi'
import UomTipiSearchTable from '../components/UomTipiSearchTable.vue'
import UomTipoDrawer from '../components/UomTipoDrawer.vue'

const drawer = useDrawerState()
const store = useUomTipiStore()
const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)
useReadonlyMode(READONLY_DOMAINS.CATALOGO, READONLY_MODELS.UOM_TIPI)

</script>

<template>
  <div class="app-page">
    <UomTipiSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <UomTipoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :tipo-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
