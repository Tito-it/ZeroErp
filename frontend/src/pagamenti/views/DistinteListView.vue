<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pagina della LISTA DISTINTE — host dell'elenco configurabile e del
//        drawer della distinta.
//
// ⚠️ Il permesso e' di AREA (`pagamenti`): questo dominio non ha ancora un
//    livello oggetto a catalogo, quindi non si dichiara un `modelName` che il
//    backend non presidia — sarebbe una granularita' che non esiste.
import { ref } from 'vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import DistinteSearchTable from '../components/DistinteSearchTable.vue'
import DistintaDrawer from '../components/DistintaDrawer.vue'

useReadonlyMode('pagamenti')

const drawerVisible = ref(false)
const distintaId = ref(null)

// Scopo: click su una riga -> apre la distinta.
function apriDistinta(riga) {
  if (!riga?.id) return
  distintaId.value = riga.id
  drawerVisible.value = true
}
</script>

<template>
  <div class="app-page">
    <DistinteSearchTable @row-click="apriDistinta" />

    <DistintaDrawer
      v-model:visible="drawerVisible"
      :distinta-id="distintaId"
    />
  </div>
</template>
