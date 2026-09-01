<script setup>
// Scopo: Vista principale gestione ordini di vendita. Host della lista DEF-8 +
//        drawer master (testata + righe + componenti + azioni stato).
import { useDrawerState } from '../../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../../core/composables/useDrawerSavedListRefresh'
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
// Handler standard, dal BB: `saved` ricarica e chiude, `changed` ricarica e
// LASCIA APERTO (il drawer ha generato un documento e il lavoro continua).
// `riapriDopoCreate: false` — la transizione CREATE → "edit-evolved" e' interna
// al drawer (auto-save bozza) e non passa di qui.
const { onDrawerSaved, onDrawerChanged } = useDrawerSavedListRefresh(
  store, drawer, { riapriDopoCreate: false, soloSeCercata: true },
)
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
      @changed="onDrawerChanged"
      @cancelled="drawer.close"
    />
  </div>
</template>
