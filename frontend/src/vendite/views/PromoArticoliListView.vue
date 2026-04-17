<script setup>
// Scopo: Vista admin promo articoli (dominio vendite, operativa-commerciale).
//        STADIO 0 del resolver pricing v5.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { usePromoArticoliStore } from '../stores/promoArticoli'
import PromoArticoliSearchTable from '../components/PromoArticoliSearchTable.vue'
import PromoArticoloDrawer from '../components/PromoArticoloDrawer.vue'

const drawer = useDrawerState()
const store = usePromoArticoliStore()

// Provider readonly del dominio vendite: i drawer figli ereditano lo stato
// (se l'operatore non ha grant sul dominio -> tutto in sola lettura).
useReadonlyMode('vendite')

async function onDrawerSaved() {
  store.filters.offset = 0
  await store.fetchList()
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <PromoArticoliSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <PromoArticoloDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
