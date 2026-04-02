<script setup>
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useEmailTemplatesStore } from '../stores/emailTemplates'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import EmailTemplateDrawer from '../components/EmailTemplateDrawer.vue'

const { t } = useI18n()
useReadonlyMode('amm_software')
const store = useEmailTemplatesStore()
const drawer = useDrawerState()
const { searchText, onPage, onSort, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'codice'
})

useTabFreshness(store, 'email-templates')

onMounted(() => {
  store.fetchList()
})

function onRowClick({ data }) {
  drawer.editRow(data, 'id')
}
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('common.search')" style="width: 250px;" />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
      </div>
    </div>

    <DataTable
      v-bind="paginatorProps"
      :value="store.items"
      :loading="store.loading"
      :totalRecords="store.totalRecords"
      lazy
      removable-sort
      striped-rows
      scrollable
      scrollHeight="flex"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
    >
      <Column field="codice" :header="t('amm.email_codice')" sortable style="width: 180px;" />
      <Column field="oggetto" :header="t('amm.email_oggetto')" sortable />
      <Column field="lingua" :header="t('amm.email_lingua')" style="width: 80px;" />
      <Column field="unita_organizzativa_descrizione" :header="t('amm.email_uo')" style="width: 180px;" />
      <Column field="variabili_disponibili" :header="t('amm.email_variabili')" style="width: 200px;">
        <template #body="{ data }">
          <span v-if="data.variabili_disponibili">
            {{ data.variabili_disponibili.join(', ') }}
          </span>
        </template>
      </Column>
      <Column field="attivo" :header="t('amm.email_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('amm.email_attivo') : t('amm.email_non_attivo')"
               :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
    </DataTable>

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
