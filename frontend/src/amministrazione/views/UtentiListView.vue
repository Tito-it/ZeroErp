<script setup>
// Scopo: pagina lista operatori con DataTable lazy, filtri e paginazione.
// Click riga -> apre UtenteDrawer in modalita' modifica.
// Button Nuovo -> apre UtenteDrawer in modalita' crea.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtentiStore } from '../stores/utenti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useLookup } from '../../core/composables/useLookup'
import { listUnitaOrganizzative } from '../api/amministrazione'
import UtenteDrawer from '../components/UtenteDrawer.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import NewButton from '../../core/components/NewButton.vue'
import Badge from 'primevue/badge'

const { t } = useI18n()
const store = useUtentiStore()
const unitaOrg = useLookup(listUnitaOrganizzative, { immediate: true })
const { searchText, onPage, onSort, applyFilters, paginatorProps } = useSearchTable(store)
const drawer = useDrawerState()

useTabFreshness(store, 'utente')

// Filtri locali (extra rispetto a search)
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

onMounted(() => { store.fetchList() })

function applyExtraFilters() {
  store.filters.ruolo_sistema = ruoloFilter.value
  store.filters.unita_organizzativa_id = uoFilter.value
  store.filters.is_active = activeFilter.value
  applyFilters()
}

function onDrawerSaved() {
  drawer.close()
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
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('amm.search_placeholder')"
        />
        <Select
          v-model="ruoloFilter"
          :options="ruoloOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amm.filter_ruolo')"
          @change="applyExtraFilters"
        />
        <Select
          v-model="uoFilter"
          :options="[{ descrizione: t('amm.reparto_all'), id: null }, ...unitaOrg.items.value]"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('amm.filter_reparto')"
          @change="applyExtraFilters"
        />
        <Select
          v-model="activeFilter"
          :options="activeOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amm.filter_stato')"
          @change="applyExtraFilters"
        />
      </div>
      <NewButton :tooltip="t('amm.nuovo_operatore')" @click="drawer.openCreate" />
    </div>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy
      removable-sort
      striped-rows
      scrollable
      scrollHeight="flex"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
      @row-click="(e) => drawer.editRow(e.data, 'auth_user_id')"
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
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :auth-user-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>
