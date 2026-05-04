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
import { useSetupStatus } from '../composables/useSetupStatus'
import { buildFilterSuperAdminOptions, buildFilterStatoOptions } from '../constants'
import { RUOLO_APPLICATIVO, READONLY_DOMAINS, TAB_ENTITIES, MANAGE_ICONS } from '../../core/constants'
import OperatoreDrawer from '../components/OperatoreDrawer.vue'
import OperatorePermessiDrawer from '../components/OperatorePermessiDrawer.vue'
import OperatoriNonAssegnatiBanner from '../components/OperatoriNonAssegnatiBanner.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import NewButton from '../../core/components/NewButton.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import Badge from 'primevue/badge'
import { displayDate } from '../../core/utils/date'

const { t } = useI18n()
const store = useOperatoriStore()
const unitaOrg = useLookup(listUnitaOrganizzative, { immediate: true })
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store)
const drawer = useDrawerState()
const permessiDrawer = useDrawerState()
const { isReadonly, isBlocked } = useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
// Destruct: Vue auto-unwrap i ref destrutturati nel template, non nel
// reactive object proxy. Pattern idiomatic.
const { status: setupStatusData, load: loadSetupStatus, hasOperatoriNonAssegnati } = useSetupStatus()

useTabFreshness(store, TAB_ENTITIES.OPERATORE)

// Filtri locali (extra rispetto a search).
// Multi-face auth Stage B: il vecchio filtro ruolo_sistema (ADMIN/OPERATIVO/
// DISABILITATO) e' scomposto in:
//   - superAdminFilter: toggle Sì/No/Tutti sul binding SUPER_ADMIN
//   - activeFilter: stato attivo identita' (ex "DISABILITATO")
const superAdminFilter = ref(null)
const uoFilter = ref(null)
const activeFilter = ref(null)

const superAdminOptions = buildFilterSuperAdminOptions(t)
const activeOptions = buildFilterStatoOptions(t)

onMounted(() => {
  store.fetchList()
  loadSetupStatus()
})

// Refresh setup status quando si chiude il drawer (assignment puo' essere
// cambiato dall'admin nel drawer operatore).
function onDrawerSavedWithStatus() {
  drawer.close()
  store.fetchList()
  loadSetupStatus(true)
}

function applyExtraFilters() {
  store.filters.is_super_admin = superAdminFilter.value
  store.filters.unita_organizzativa_id = uoFilter.value
  store.filters.is_active = activeFilter.value
  applyFilters()
}

// Scopo: apre il drawer permessi per la riga cliccata senza aprire il drawer
//        completo di modifica operatore. Intercetta il click sul pulsante per
//        evitare che il click propaghi alla riga (che aprirebbe il drawer edit).
function openPermessi(row, event) {
  event.stopPropagation()
  permessiDrawer.editRow(row, 'auth_user_id')
}

function activeBadgeSeverity(active) {
  return active ? 'success' : 'danger'
}

// i18n label per ruolo applicativo: chiave auth.ruolo_applicativo.<VALORE>
// con fallback sul valore grezzo.
function ruoloAppLabel(ruoloApp) {
  if (!ruoloApp) return '—'
  const key = `auth.ruolo_applicativo.${ruoloApp}`
  const translated = t(key)
  return translated === key ? ruoloApp : translated
}

// Scopo: azioni di riga operatore (apertura drawer permessi), nascoste in readonly.
function buildRowActions(data) {
  return [
    {
      key: 'gestisci-permessi',
      label: t('amm.gestisci_permessi'),
      icon: MANAGE_ICONS.PERMISSIONS,
      command: () => permessiDrawer.editRow(data, 'auth_user_id'),
    },
  ]
}
</script>

<template>
  <div class="app-page">
    <OperatoriNonAssegnatiBanner
      v-if="hasOperatoriNonAssegnati"
      :count="setupStatusData.operatori_non_assegnati"
    />

    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('amm.search_placeholder')"
        />
        <Select
          v-model="superAdminFilter"
          :options="superAdminOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amm.filter_super_admin')"
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
        <ReadonlyBadge />
        <ReloadButton @click="reload" />
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
      <Column :header="t('amm.col_ruolo')">
        <template #body="{ data }">
          <div class="operatore-ruolo-badges">
            <Badge v-if="data.is_super_admin"
              :value="t('amm.is_super_admin.badge')" severity="warn" />
            <Badge :value="ruoloAppLabel(data.ruolo_applicativo)"
              :severity="data.ruolo_applicativo === RUOLO_APPLICATIVO.DISABILITATO ? 'danger' : 'info'" />
          </div>
        </template>
      </Column>
      <Column field="valido_dal" :header="t('amm.col_valido_dal')" sortable>
        <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
      </Column>
      <Column field="valido_al" :header="t('amm.col_valido_al')" sortable>
        <template #body="{ data }">{{ displayDate(data.valido_al) }}</template>
      </Column>
      <Column field="is_active" :header="t('amm.col_stato')" sortable>
        <template #body="{ data }">
          <Badge
            :value="data.is_active ? t('amm.stato_attivo') : t('amm.stato_inattivo')"
            :severity="activeBadgeSeverity(data.is_active)"
          />
        </template>
      </Column>
      <Column v-if="!isReadonly" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false" frozen alignFrozen="right">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>
    </template>

    <OperatoreDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :auth-user-id="drawer.state.itemId"
      @saved="onDrawerSavedWithStatus"
      @cancelled="drawer.close"
    />

    <OperatorePermessiDrawer
      :visible="permessiDrawer.state.visible"
      @update:visible="v => permessiDrawer.state.visible = v"
      :auth-user-id="permessiDrawer.state.itemId"
    />
  </div>
</template>

<style scoped>
.operatore-ruolo-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}
</style>
