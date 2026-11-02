<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: La lista del log email (`<ListaConfigurabile codice="config.email_log">`)
//        con i suoi filtri — ricerca, stato, periodo — e le celle di stato ed
//        errore. Lista di sola consultazione: niente «Nuovo», niente click di
//        riga, niente export — lo scaffolding omette le azioni da se'.
//
// ⭐ BUILDING BLOCK (regola del 2, ok Tid 2026-09-26): la usano il log
//    dell'amministratore (`amministrazione/views/EmailLogsListView`, rotta
//    `/amm-software/email-log/`) e le email dell'operatore
//    (`strumenti/views/EmailLogView`, rotta `/core/email/log/`). Stessa lista,
//    due porte: cambia solo lo STORE, cioe' da dove legge. Chi vede quale riga
//    lo decide la porta (l'admin tutto, l'operatore il suo perimetro per RLS),
//    non questo componente.
// ⛔ Qui non c'e' `useReadonlyMode`: la modalita' e' della SCHERMATA (l'admin
//    la dichiara per Amm. Software, il dominio Personale non ha un'area).
//
// Uso:
//   <EmailLogLista :store="useEmailLogsStore()" />
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import ListaConfigurabile from './ListaConfigurabile.vue'
import ListaConfigStatusTag from './ListaConfigStatusTag.vue'
import PageActionsBar from './PageActionsBar.vue'
import FiltroPeriodo from './FiltroPeriodo.vue'
import FiltriLista from './FiltriLista.vue'
import EmailLogStatoSelect from './EmailLogStatoSelect.vue'
import { useListaConfigurabilePage } from '../composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../composables/useStoreFilterBindings'
import { statoEmailLogSeverity } from '../utils/severity'

const props = defineProps({
  // Uno store `createListaStore` sulla lista `config.email_log`, con i filtri
  // `stato`, `data_da`, `data_a`.
  store: { type: Object, required: true },
})

const { t } = useI18n()
const store = props.store
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  searchTableOptions: {
    defaultSortField: 'data_insert',
    // 'desc', NON -1: il contratto di useSearchTable e' 'asc'/'desc'.
    defaultSortOrder: 'desc',
  },
})

// Il periodo e' UN filtro con due estremi: un binding, un componente, con
// l'invariante `da <= a`.
const { bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const periodo = bindPeriodo()

// Scopo: applica il filtro stato e riparte dalla prima pagina.
function onStatoChange(val) {
  store.filters.stato = val
  store.filters.offset = 0
  store.fetchList()
}

onMounted(() => {
  store.fetchList()
})
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText v-model="searchText" class="app-filter-w-lg" :placeholder="t('common.search')" />
        </template>
        <EmailLogStatoSelect
          class="app-filter-w-sm"
          :modelValue="store.filters.stato"
          :placeholder="t('core.email_log.stato')"
          @update:modelValue="onStatoChange"
        />
        <FiltroPeriodo :periodo="periodo" />
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="config.email_log"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @config-loaded="onConfigLoaded"
    >
      <!-- La data non ha slot: il seed dichiara `datetime_short` e il formatter
           di serie la rende gia' cosi'. -->
      <template #cell-errore="{ data }">
        <span v-if="data.errore" style="font-size: 0.85rem;">{{ data.errore }}</span>
      </template>
      <template #cell-stato="{ data }">
        <Tag :value="data.stato" :severity="statoEmailLogSeverity(data.stato)" />
      </template>
    </ListaConfigurabile>
  </div>
</template>
