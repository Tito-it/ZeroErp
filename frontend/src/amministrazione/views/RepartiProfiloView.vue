<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: pagina lista reparti (`<ListaConfigurabile codice="amm.reparti">`):
//        colonne, ordine e personalizzazione dal catalogo, paginata dal
//        backend, con la ricerca libera. Click riga -> apre il drawer
//        `RepartoProfiloEditor` sul profilo di accesso del reparto.
//
// ⭐ Dal 2026-09-27 (brief-db-liste-datatable-grezze riga 5): fino a quel
//    giorno una `DataTable` grezza su tutti i reparti in una volta.
// ⚠️ Solo i reparti ATTIVI, come prima: se servano anche i disattivati e' una
//    domanda aperta (§8 punto 5 del brief), e il filtro sta nel backend.
// ⚠️ Niente «Nuovo»: un reparto e' un'unita' organizzativa, che nasce altrove;
//    qui se ne configura il profilo. Niente export: l'endpoint non c'e'.
import { onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Badge from 'primevue/badge'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useRepartiStore } from '../stores/reparti'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, TAB_ENTITIES } from '../../core/constants'
import RepartoProfiloEditor from '../components/RepartoProfiloEditor.vue'

const { t } = useI18n()
const store = useRepartiStore()
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
const { onDataChanged } = useTabEvents()

const {
  searchText, paginatorProps, onPage, onSort, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  // Allineato al preset `reparti_default` (`descrizione asc`).
  searchTableOptions: { defaultSortField: 'descrizione' },
})

const editorVisible = ref(false)
const selectedUoId = ref(null)
const selectedUoNome = ref('')

const cleanup = onDataChanged(e => {
  if (e.entityType === TAB_ENTITIES.PROFILO_REPARTO) store.fetchList()
})
onUnmounted(cleanup)

// ⚠️ Solo `onMounted`: il rientro sotto `<KeepAlive>` lo rinfresca gia'
//    `useSearchTable` dentro lo scaffolding, sulla pagina corrente — tenere
//    anche un `onActivated` qui farebbe due fetch a ogni rientro.
onMounted(() => { store.fetchList() })

function onRowClick(data) {
  selectedUoId.value = data.id
  selectedUoNome.value = data.descrizione
  editorVisible.value = true
}

function onEditorSaved() {
  editorVisible.value = false
  store.fetchList()
}

function profiloSeverity(count) {
  return count > 0 ? 'success' : 'warn'
}
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText
            v-model="searchText"
            class="app-filter-w-lg"
            :placeholder="t('common.search')"
          />
        </template>
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="amm.reparti"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      @config-loaded="onConfigLoaded"
    >
      <!-- La colonna legge il NUMERO di aree del profilo (e per quello
           ordina), a video dice se il profilo c'e'. -->
      <template #cell-profilo_aree_count="{ data }">
        <Badge
          :value="data.profilo_aree_count > 0 ? t('amministrazione.profilo_configurato') : t('amministrazione.profilo_mancante')"
          :severity="profiloSeverity(data.profilo_aree_count)"
        />
      </template>
    </ListaConfigurabile>

    <RepartoProfiloEditor
      v-model:visible="editorVisible"
      :uo-id="selectedUoId"
      :uo-nome="selectedUoNome"
      @saved="onEditorSaved"
      @cancelled="editorVisible = false"
    />
  </div>
</template>

<!-- Stile .app-page definito in main.css -->
