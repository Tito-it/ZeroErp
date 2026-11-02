<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pagina della LISTA del documento interno di magazzino — inventari o
//        rettifiche: UNA vista per due rotte, la famiglia la dice
//        `route.meta.famiglia` (Q-1). Host dell'elenco configurabile, del
//        dialog di apertura e del drawer del documento.
//
// ⚠️ Il permesso e' di AREA (`magazzino`): il dominio non ha un livello
//    oggetto a catalogo, quindi non si dichiara un `modelName` che il backend
//    non presidia — sarebbe una granularita' che non esiste.
//
// ⚠️ La famiglia si legge dalla rotta UNA volta: la vista vive sotto KeepAlive
//    con `:key="$route.path"`, quindi le due porte sono due istanze diverse e
//    nessuna cambia famiglia sotto i piedi.
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import ApriDocumentoInternoDialog from '../components/ApriDocumentoInternoDialog.vue'
import DocumentiInterniSearchTable from '../components/DocumentiInterniSearchTable.vue'
import DocumentoInternoDrawer from '../components/DocumentoInternoDrawer.vue'
import { FAMIGLIE } from '../vocabolari'

useReadonlyMode(READONLY_DOMAINS.MAGAZZINO)

const route = useRoute()
const famiglia = route.meta.famiglia
if (!(famiglia in FAMIGLIE)) {
  throw new Error(`[magazzino] la rotta ${String(route.name)} non dichiara una famiglia valida`)
}

const drawerVisible = ref(false)
const apriVisible = ref(false)
const documentoId = ref(null)

// Scopo: aperto un documento, lo si apre subito nel drawer — e' il posto dove
//        si digitano le righe, cioe' il motivo per cui lo si e' aperto.
// ⛔ Nessun `store.fetchList()` qui, ne' sul drawer: ogni verbo dello store
//    emette l'evento della famiglia e la lista si ricarica da sola
//    (`useTabFreshness`). Un secondo refetch qui sarebbero DUE richieste
//    identiche, e due risposte possono tornare in ordine inverso.
function onAperto(id) {
  if (!id) return
  documentoId.value = id
  drawerVisible.value = true
}

// Scopo: click su una riga -> apre il documento.
function apriDocumento(riga) {
  if (!riga?.id) return
  documentoId.value = riga.id
  drawerVisible.value = true
}
</script>

<template>
  <div class="app-page">
    <DocumentiInterniSearchTable
      :famiglia="famiglia"
      @row-click="apriDocumento"
      @new="apriVisible = true"
    />

    <ApriDocumentoInternoDialog
      v-model:visible="apriVisible"
      :famiglia="famiglia"
      @aperto="onAperto"
    />

    <!-- `righe_count` in lista cambia a ogni riga scritta nel drawer: lo store
         emette, la lista ascolta — niente handler qui. -->
    <DocumentoInternoDrawer
      v-model:visible="drawerVisible"
      :famiglia="famiglia"
      :documento-id="documentoId"
    />
  </div>
</template>
