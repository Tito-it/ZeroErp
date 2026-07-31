<script setup>
// Scopo: pagina lista emittenti fiscali (admin only), configurabile
//        (`<ListaConfigurabile codice="anagrafiche.emittenti_fiscali">`):
//        colonne, ordine e visibilita' dal catalogo `ui.lista_colonna`, con
//        ritiro dinamico e personalizzazione per utente.
// Click riga -> apre EmittenteFiscaleDrawer (anagrafica) in modifica.
// Pulsanti riga BA / Utilities -> aprono i drawer DEDICATI per la sotto-entita',
// senza passare dal drawer dati.
// Nessun export: il dominio non ha endpoint (lo scaffolding omette l'azione da
// se', non ricevendo `exportFn`).
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliStore } from '../stores/emittentiFiscali'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, TAB_ENTITIES, MANAGE_ICONS } from '../../core/constants'
import EmittenteFiscaleDrawer from '../components/EmittenteFiscaleDrawer.vue'
import EmittenteFiscaleBillingAccountDrawer from '../components/EmittenteFiscaleBillingAccountDrawer.vue'
import EmittenteFiscaleUtilitiesDrawer from '../components/EmittenteFiscaleUtilitiesDrawer.vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Badge from 'primevue/badge'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const { t } = useI18n()
const store = useEmittentiFiscaliStore()
const {
  searchText, applyFilters, paginatorProps, onPage, onSort, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'amministrazione.emittenti_fiscali.new',
  onNew: () => openCreate(),
  searchTableOptions: { defaultSortField: 'descrizione' },
})

// Tre drawer indipendenti: anagrafica, BA mapping, utility matrix.
const drawer = useDrawerState()
const baDrawer = useDrawerState()
const utDrawer = useDrawerState()

// Provider readonly: livello LETTURA disabilita i pulsanti di scrittura nei drawer figli.
const { isReadonly, isBlocked } = useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)

useTabFreshness(store, TAB_ENTITIES.EMITTENTE_FISCALE)

const attivoFilter = ref(null)
const attivoOptions = [
  { label: t('amministrazione.stato_all'), value: null },
  { label: t('amministrazione.stato_attivo'), value: true },
  { label: t('amministrazione.stato_inattivo'), value: false }
]
onMounted(() => { store.fetchList() })

function applyExtraFilters() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

function onDrawerSaved() {
  drawer.close()
  store.fetchList()
}

function openCreate() {
  drawer.openCreate()
}

function openEdit(row) {
  drawer.editRow(row, 'id')
}

// Scopo: azioni di riga emittente fiscale (sub-drawer BA + utilities).
function buildRowActions(data) {
  return [
    {
      key: 'ba',
      label: t('amministrazione.emittenti_fiscali.action_ba'),
      icon: MANAGE_ICONS.BILLING_ACCOUNT,
      command: () => baDrawer.editRow(data, 'id'),
    },
    {
      key: 'utilities',
      label: t('amministrazione.emittenti_fiscali.action_utilities'),
      icon: MANAGE_ICONS.UTILITY,
      command: () => utDrawer.editRow(data, 'id'),
    },
  ]
}
</script>

<template>
  <div class="app-page">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('amministrazione.emittenti_fiscali.search_placeholder')"
        />
        <Select
          v-model="attivoFilter"
          :options="attivoOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.filter_stato')"
          @change="applyExtraFilters"
        />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="anagrafiche.emittenti_fiscali"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="openEdit"
      @config-loaded="onConfigLoaded"
    >
      <template #cell-attivo="{ data }">
        <Badge
          :value="data.attivo ? t('amministrazione.stato_attivo') : t('amministrazione.stato_inattivo')"
          :severity="data.attivo ? 'success' : 'danger'"
        />
      </template>

      <!-- v-if sul TEMPLATE dello slot, non sul menu: senza slot `actions` la
           BB non monta proprio la colonna (haAzioni), come la <Column v-if>
           pre-conversione. Il v-if interno lascerebbe una colonna vuota. -->
      <template v-if="!isReadonly" #actions="{ data, compact }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)"
          :force-compact="compact" />
      </template>
    </ListaConfigurabile>
    </template>

    <EmittenteFiscaleDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :emittente-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <EmittenteFiscaleBillingAccountDrawer
      :visible="baDrawer.state.visible"
      @update:visible="v => baDrawer.state.visible = v"
      :emittente-id="baDrawer.state.itemId"
      :emittente-codice="baDrawer.state.itemData?.codice || ''"
      :emittente-ragione-sociale="baDrawer.state.itemData?.ragione_sociale_completa || ''"
      @close="baDrawer.close"
    />

    <EmittenteFiscaleUtilitiesDrawer
      :visible="utDrawer.state.visible"
      @update:visible="v => utDrawer.state.visible = v"
      :emittente-id="utDrawer.state.itemId"
      :emittente-codice="utDrawer.state.itemData?.codice || ''"
      :emittente-ragione-sociale="utDrawer.state.itemData?.ragione_sociale_completa || ''"
      :emittente-attivo="utDrawer.state.itemData?.attivo ?? true"
      @close="utDrawer.close"
    />
  </div>
</template>
