<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, READONLY_DOMAINS, TAB_ENTITIES } from '../../core/constants'
import { useEmailAccountsStore } from '../stores/emailAccounts'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import EmailAccountDrawer from '../components/EmailAccountDrawer.vue'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
const store = useEmailAccountsStore()
const drawer = useDrawerState()
const { searchText, onPage, onSort, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'codice'
})
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: reload,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('amm.email_new_account'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => drawer.openCreate(),
  },
])

useTabFreshness(store, TAB_ENTITIES.EMAIL_ACCOUNTS)

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
      <PageActionsBar :actions="pageActions" />
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
      <Column field="codice" :header="t('amm.email_codice')" sortable style="width: 120px;" />
      <Column field="descrizione" :header="t('amm.email_descrizione')" sortable />
      <Column field="smtp_host" :header="t('amm.email_smtp_host')" style="width: 180px;" />
      <Column field="email_from" :header="t('amm.email_from')" style="width: 220px;" />
      <Column field="unita_organizzativa_descrizione" :header="t('amm.email_uo')" style="width: 180px;" />
      <Column field="attivo" :header="t('amm.email_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('amm.email_attivo') : t('amm.email_non_attivo')"
               :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
    </DataTable>

    <EmailAccountDrawer
      :visible="drawer.state.visible"
      :mode="drawer.state.mode"
      :accountId="drawer.state.itemId"
      @update:visible="v => drawer.state.visible = v"
      @saved="() => { drawer.close(); store.fetchList() }"
      @cancelled="drawer.close()"
    />
  </div>
</template>
