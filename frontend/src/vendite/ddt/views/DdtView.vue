<script setup>
// Scopo: Vista principale gestione DDT di vendita. Host della lista
//        configurabile + drawer master (testata trasporto + righe + componenti
//        BoM + azioni stato). Clone di OrdiniView (analisi-ddt-vendita §D-4).
import { useDrawerState } from '../../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../../core/constants'
import { useDdtStore } from '../stores/ddt'
import DdtSearchTable from '../components/DdtSearchTable.vue'
import DdtDrawer from '../components/DdtDrawer.vue'

const drawer = useDrawerState()
const store = useDdtStore()

// Permessi: livello area `vendite` + livello oggetto `ddt` (model_permission BE
// ("vendite","ddt"); fallback ad area se non catalogato, vedi frontend-standards
// §"Drawer autonomo vs figlio puro").
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.DDT)

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
    <DdtSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <DdtDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :ddt-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @changed="onDrawerChanged"
      @cancelled="drawer.close"
    />
  </div>
</template>
