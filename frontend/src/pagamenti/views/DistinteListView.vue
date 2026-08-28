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
import ApriDistintaDialog from '../components/ApriDistintaDialog.vue'
import { useDistinteStore } from '../stores/distinte'

useReadonlyMode('pagamenti')

const store = useDistinteStore()
const drawerVisible = ref(false)
const apriVisible = ref(false)
const distintaId = ref(null)

// Scopo: aperta (o RITROVATA) una distinta, la si apre subito nel drawer — e' il
//        posto dove si digitano le righe, cioe' il motivo per cui la si e'
//        aperta. La lista si ricarica perche' puo' esserci una riga in piu'.
// Note: ⚠️ Vale anche per una distinta RITROVATA: il dialog ha gia' annunciato
//       che conteneva delle righe, e portarci dentro e' cio' che rende
//       l'annuncio azionabile invece che una notifica e basta.
function onAperta(id) {
  if (!id) return
  distintaId.value = id
  drawerVisible.value = true
  store.fetchList()
}

// Scopo: click su una riga -> apre la distinta.
function apriDistinta(riga) {
  if (!riga?.id) return
  distintaId.value = riga.id
  drawerVisible.value = true
}
</script>

<template>
  <div class="app-page">
    <DistinteSearchTable @row-click="apriDistinta" @new="apriVisible = true" />

    <ApriDistintaDialog v-model:visible="apriVisible" @aperta="onAperta" />

    <!-- ⚠️ `@cambiata` ricarica la lista: i contatori di riga (registrabili,
         totale, scarto) cambiano a ogni gesto fatto dentro il drawer, e una
         lista ferma direbbe numeri vecchi accanto a un foglio gia' avanzato. -->
    <DistintaDrawer
      v-model:visible="drawerVisible"
      :distinta-id="distintaId"
      @cambiata="store.fetchList()"
    />
  </div>
</template>
