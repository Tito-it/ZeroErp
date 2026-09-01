<script setup>
// Scopo: Vista principale gestione preventivi vendita.
import { useDrawerState } from '../../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../../core/constants'
import { usePreventiviStore } from '../stores/preventivi'
import PreventiviList from '../components/PreventiviList.vue'
import PreventiviDrawer from '../components/PreventiviDrawer.vue'

const drawer = useDrawerState()
const store = usePreventiviStore()
useReadonlyMode(READONLY_DOMAINS.VENDITE)

// Su 'saved': aggiorna lista + chiude drawer.
// La transizione CREATE → "edit-evolved" (auto-save bozza con righe inline) e'
// gestita internamente dal drawer via createdId/hasDetail e NON emette 'saved'.
// Quindi qui arriva solo il save manuale dell'utente (UPDATE testata o create
// fallback): refresh + close lineare.
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
    <PreventiviList
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <PreventiviDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :preventivo-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @changed="onDrawerChanged"
      @cancelled="drawer.close"
    />
  </div>
</template>
