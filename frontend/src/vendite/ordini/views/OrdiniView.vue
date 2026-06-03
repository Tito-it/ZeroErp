<script setup>
// Scopo: Vista principale gestione ordini di vendita. Host della lista DEF-8 +
//        drawer master (testata + righe + componenti + azioni stato).
import { useDrawerState } from '../../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../../core/constants'
import { useOrdiniStore } from '../stores/ordini'
import OrdiniSearchTable from '../components/OrdiniSearchTable.vue'
import OrdiniDrawer from '../components/OrdiniDrawer.vue'

const drawer = useDrawerState()
const store = useOrdiniStore()

// Permessi: livello area `vendite` + livello oggetto `ordine` (in attesa che il
// BE catalogizzi il model in config.area_model_overrides — fallback ad area se
// non catalogato, vedi frontend-standards §"Drawer autonomo vs figlio puro").
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.ORDINE)

// Su 'saved': refresh lista + chiude drawer. La transizione CREATE →
// "edit-evolved" (auto-save bozza con righe inline) e' interna al drawer e NON
// emette 'saved'; qui arriva il save manuale / le azioni stato.
async function onDrawerSaved() {
  store.filters.offset = 0
  if (store.hasSearched) await store.fetchList()
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <OrdiniSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <OrdiniDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :ordine-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
