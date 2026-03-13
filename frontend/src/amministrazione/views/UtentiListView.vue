<script setup>
// Scopo: pagina lista operatori con DataTable lazy, filtri e paginazione.
// Click riga -> apre UtenteDrawer in modalita' modifica.
// Button Nuovo -> apre UtenteDrawer in modalita' crea.
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtentiStore } from '../stores/utenti'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { PAGINATION } from '../../core/constants'
import UtenteDrawer from '../components/UtenteDrawer.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import Toolbar from 'primevue/toolbar'

const { t } = useI18n()
const store = useUtentiStore()
const { onDataChanged } = useTabEvents()

// Drawer state
const drawerVisible = ref(false)
const drawerMode = ref('create') // 'create' | 'edit'
const drawerUserId = ref(null)

// Filtri locali
const searchText = ref('')
const ruoloFilter = ref(null)
const uoFilter = ref(null)
const activeFilter = ref(null)

const ruoloOptions = [
  { label: t('amm.ruolo_all'), value: null },
  { label: t('amm.ruolo_admin'), value: 'ADMIN' },
  { label: t('amm.ruolo_operativo'), value: 'OPERATIVO' },
  { label: t('amm.ruolo_disabilitato'), value: 'DISABILITATO' }
]

const activeOptions = [
  { label: t('amm.stato_all'), value: null },
  { label: t('amm.stato_attivo'), value: true },
  { label: t('amm.stato_inattivo'), value: false }
]

// Inter-tab freshness
const cleanup = onDataChanged(e => {
  if (e.entityType === 'utente') store.fetchList()
})
onUnmounted(cleanup)

onMounted(async () => {
  await store.fetchUnitaOrganizzative()
  await store.fetchList()
})

function onPage(event) {
  store.filters.offset = event.first
  store.filters.limit = event.rows
  store.fetchList()
}

function onSort(event) {
  store.filters.order_by = event.sortField
  store.filters.order_dir = event.sortOrder === 1 ? 'ASC' : 'DESC'
  store.fetchList()
}

function applyFilters() {
  store.filters.search = searchText.value || ''
  store.filters.ruolo_sistema = ruoloFilter.value
  store.filters.unita_organizzativa_id = uoFilter.value
  store.filters.is_active = activeFilter.value
  store.filters.offset = 0
  store.fetchList()
}

// Debounce search
let searchTimeout = null
watch(searchText, () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(applyFilters, 400)
})

function onRowClick(event) {
  drawerMode.value = 'edit'
  drawerUserId.value = event.data.auth_user_id
  drawerVisible.value = true
}

function openCreateDrawer() {
  drawerMode.value = 'create'
  drawerUserId.value = null
  drawerVisible.value = true
}

function onDrawerSaved() {
  drawerVisible.value = false
  store.fetchList()
}

function ruoloBadgeSeverity(ruolo) {
  if (ruolo === 'ADMIN') return 'danger'
  if (ruolo === 'DISABILITATO') return 'secondary'
  return 'info'
}

function activeBadgeSeverity(active) {
  return active ? 'success' : 'warn'
}
</script>

<template>
  <div class="utenti-list-view">
    <Toolbar class="mb-3">
      <template #start>
        <InputText
          v-model="searchText"
          :placeholder="t('amm.search_placeholder')"
          class="mr-2"
          style="width: 260px"
        />
        <Select
          v-model="ruoloFilter"
          :options="ruoloOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amm.filter_ruolo')"
          class="mr-2"
          style="width: 180px"
          @change="applyFilters"
        />
        <Select
          v-model="uoFilter"
          :options="[{ nome: t('amm.reparto_all'), id: null }, ...store.unitaOrganizzative]"
          option-label="nome"
          option-value="id"
          :placeholder="t('amm.filter_reparto')"
          class="mr-2"
          style="width: 200px"
          @change="applyFilters"
        />
        <Select
          v-model="activeFilter"
          :options="activeOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amm.filter_stato')"
          style="width: 160px"
          @change="applyFilters"
        />
      </template>
      <template #end>
        <Button
          :label="t('amm.nuovo_operatore')"
          icon="pi pi-plus"
          @click="openCreateDrawer"
        />
      </template>
    </Toolbar>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      :total-records="store.totalRecords"
      :rows="store.filters.limit"
      :first="store.filters.offset"
      :rows-per-page-options="PAGINATION.ROWS_OPTIONS"
      lazy
      paginator
      removable-sort
      striped-rows
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      selection-mode="single"
      data-key="auth_user_id"
    >
      <Column field="last_name" :header="t('amm.col_nome')" sortable>
        <template #body="{ data }">
          {{ data.last_name }} {{ data.first_name }}
        </template>
      </Column>
      <Column field="username" :header="t('amm.col_username')" sortable />
      <Column field="unita_organizzativa_nome" :header="t('amm.col_reparto')" sortable />
      <Column field="ruolo_sistema" :header="t('amm.col_ruolo')" sortable>
        <template #body="{ data }">
          <Badge :value="data.ruolo_sistema" :severity="ruoloBadgeSeverity(data.ruolo_sistema)" />
        </template>
      </Column>
      <Column field="is_active" :header="t('amm.col_stato')" sortable>
        <template #body="{ data }">
          <Badge
            :value="data.is_active ? t('amm.stato_attivo') : t('amm.stato_inattivo')"
            :severity="activeBadgeSeverity(data.is_active)"
          />
        </template>
      </Column>
      <Column field="data_insert" :header="t('amm.col_data_insert')" sortable />
    </DataTable>

    <UtenteDrawer
      v-model:visible="drawerVisible"
      :mode="drawerMode"
      :auth-user-id="drawerUserId"
      @saved="onDrawerSaved"
      @cancelled="drawerVisible = false"
    />
  </div>
</template>

<style scoped>
.utenti-list-view {
  padding: 1rem;
}
</style>
