<script setup>
// Scopo: Lista template email configurabile
//        (`<ListaConfigurabile codice="config.email_template">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro
//        dinamico e personalizzazione per utente. Nessuna azione "Nuovo" (i
//        template nascono dal seed) e nessun export: lo scaffolding le omette
//        da se', non ricevendo `onNew` ne' `exportFn`.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import AttivoTag from '../../core/components/AttivoTag.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, TAB_ENTITIES } from '../../core/constants'
import { useEmailTemplatesStore } from '../stores/emailTemplates'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import EmailTemplateDrawer from '../components/EmailTemplateDrawer.vue'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
const store = useEmailTemplatesStore()
const drawer = useDrawerState()
const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'codice' },
})

useTabFreshness(store, TAB_ENTITIES.EMAIL_TEMPLATES)

onMounted(() => {
  store.fetchList()
})

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) {
  drawer.editRow(data, 'id')
}
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('common.search')" style="width: 250px;" />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="config.email_template"
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
      <!-- Array JSONB: senza slot si vedrebbe la resa grezza della lista. -->
      <template #cell-variabili_disponibili="{ data }">
        <span v-if="data.variabili_disponibili">
          {{ data.variabili_disponibili.join(', ') }}
        </span>
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" :active-label="t('amministrazione.email_attivo')"
          :inactive-label="t('amministrazione.email_non_attivo')" />
      </template>
    </ListaConfigurabile>

    <EmailTemplateDrawer
      :visible="drawer.state.visible"
      :mode="drawer.state.mode"
      :templateId="drawer.state.itemId"
      @update:visible="v => drawer.state.visible = v"
      @saved="() => { drawer.close(); store.fetchList() }"
      @cancelled="drawer.close()"
    />
  </div>
</template>
