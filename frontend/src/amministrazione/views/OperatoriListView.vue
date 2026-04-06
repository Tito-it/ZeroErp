<script setup>
// Scopo: pagina lista operatori con DataTable lazy, filtri e paginazione.
// Click riga -> apre OperatoreDrawer in modalita' modifica.
// Button Nuovo -> apre OperatoreDrawer in modalita' crea.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOperatoriStore } from '../stores/operatori'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useLookup } from '../../core/composables/useLookup'
import { listUnitaOrganizzative } from '../api/amministrazione'
import { RUOLO_SISTEMA, buildRuoloOptions, getRuoloSeverity } from '../constants'
import OperatoreDrawer from '../components/OperatoreDrawer.vue'
import OperatorePermessiDrawer from '../components/OperatorePermessiDrawer.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import NewButton from '../../core/components/NewButton.vue'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import { displayDate } from '../../core/utils/date'

const { t } = useI18n()
const store = useOperatoriStore()
const unitaOrg = useLookup(listUnitaOrganizzative, { immediate: true })
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store)
const drawer = useDrawerState()
const permessiDrawer = useDrawerState()
const { isReadonly } = useReadonlyMode('amm_software')

useTabFreshness(store, 'operatore')

// Filtri locali (extra rispetto a search)
const ruoloFilter = ref(null)
const uoFilter = ref(null)
const activeFilter = ref(null)

const ruoloOptions = buildRuoloOptions(t, { includeAll: true })

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

// Scopo: apre il drawer permessi per la riga cliccata senza aprire il drawer
//        completo di modifica operatore. Intercetta il click sul pulsante per
//        evitare che il click propaghi alla riga (che aprirebbe il drawer edit).
function openPermessi(row, event) {
  event.stopPropagation()
  permessiDrawer.editRow(row, 'auth_user_id')
}

const ruoloBadgeSeverity = getRuoloSeverity

function activeBadgeSeverity(active) {
  return active ? 'success' : 'danger'
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
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('amm.nuovo_operatore')" @click="drawer.openCreate" />
      </div>
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
      <Column field="soggetto_cognome" :header="t('amm.col_nome')" sortable>
        <template #body="{ data }">
          {{ data.soggetto_cognome }} {{ data.soggetto_nome }}
        </template>
      </Column>
      <Column field="username" :header="t('amm.col_username')" sortable />
      <Column field="unita_organizzativa_nome" :header="t('amm.col_reparto')" sortable />
      <Column field="emittenti_descrizione" :header="t('amm.field_emittente')" />
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
      <Column field="valido_dal" :header="t('amm.col_valido_dal')" sortable>
        <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
      </Column>
      <Column field="valido_al" :header="t('amm.col_valido_al')" sortable>
        <template #body="{ data }">{{ displayDate(data.valido_al) }}</template>
      </Column>
      <Column v-if="!isReadonly" :header="t('amm.col_actions')" style="width: 70px;" frozen alignFrozen="right">
        <template #body="{ data }">
          <Button
            icon="pi pi-shield"
            text rounded size="small"
            class="app-manage-btn"
            v-tooltip.bottom="t('amm.gestisci_permessi')"
            @click="openPermessi(data, $event)"
          />
        </template>
      </Column>
    </DataTable>

    <OperatoreDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :auth-user-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <OperatorePermessiDrawer
      :visible="permessiDrawer.state.visible"
      @update:visible="v => permessiDrawer.state.visible = v"
      :auth-user-id="permessiDrawer.state.itemId"
    />
  </div>
</template>
