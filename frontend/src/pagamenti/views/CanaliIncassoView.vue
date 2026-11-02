<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pagina dei CANALI DI INCASSO — l'elenco e il drawer di configurazione.
import { ref } from 'vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import CanaliIncassoSearchTable from '../components/CanaliIncassoSearchTable.vue'
import CanaleIncassoDrawer from '../components/CanaleIncassoDrawer.vue'
import { useCanaliIncassoStore } from '../stores/canaliIncasso'

useReadonlyMode(READONLY_DOMAINS.PAGAMENTI)

const store = useCanaliIncassoStore()
const drawerVisible = ref(false)
const canaleId = ref(null)

function apri(riga) {
  canaleId.value = riga?.id ?? null
  drawerVisible.value = true
}

function nuovo() {
  canaleId.value = null
  drawerVisible.value = true
}
</script>

<template>
  <div class="app-page">
    <CanaliIncassoSearchTable @row-click="apri" @new="nuovo" />

    <CanaleIncassoDrawer
      v-model:visible="drawerVisible"
      :canale-id="canaleId"
      @salvato="store.fetchList()"
    />
  </div>
</template>
