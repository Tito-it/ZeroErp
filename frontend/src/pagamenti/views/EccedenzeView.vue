<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pagina delle ECCEDENZE DA SISTEMARE — i documenti su cui e' entrato
//        piu' del dovuto, raggruppati per cliente perche' e' li' che si decide,
//        e il drawer in cui la decisione si prende.
//
// ⭐ La vista PRESENTA, la persona DECIDE, l'atto diventa un fatto: sono tre
//    momenti distinti, e il drawer e' il secondo. Nessuna riga si sana da sola —
//    sanarla vorrebbe dire muovere denaro senza che nessuno l'abbia deciso.
import { ref } from 'vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import EccedenzeSearchTable from '../components/EccedenzeSearchTable.vue'
import SistemazioneDrawer from '../components/SistemazioneDrawer.vue'
import { useEccedenzeStore } from '../stores/eccedenze'

useReadonlyMode(READONLY_DOMAINS.PAGAMENTI)

const store = useEccedenzeStore()
const drawerVisible = ref(false)
const eccedenza = ref(null)

// ⚠️ Si passa la RIGA intera e non il solo `fattura_id`: il drawer mostra il
//    verso del credito, il totale del cliente e quanti altri documenti ha —
//    numeri che la vista ha gia' calcolati in finestra, e che rileggerli uno a
//    uno costerebbe un giro in piu' per dire le stesse cose.
function apri(riga) {
  if (!riga?.fattura_id) return
  eccedenza.value = riga
  drawerVisible.value = true
}
</script>

<template>
  <div class="app-page">
    <EccedenzeSearchTable @row-click="apri" />

    <!-- ⚠️ `@cambiata` ricarica l'elenco anche quando la riga NON sparisce: un
         atto in BOZZA non toglie l'eccedenza, ma cambia il contatore che dice
         «ci sta gia' lavorando qualcuno». -->
    <SistemazioneDrawer
      v-model:visible="drawerVisible"
      :eccedenza="eccedenza"
      @cambiata="store.fetchList()"
    />
  </div>
</template>
