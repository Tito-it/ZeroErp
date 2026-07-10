<script setup>
// Scopo: Lista DDT di vendita configurabile. Nasce direttamente
// <ListaConfigurabile codice="vendite.ddt">: ritiro dinamico colonne
// (anti-scrollbar), personalizzazione colonne. Scaffolding (useSearchTable +
// ref lista + pageActions) centralizzato in useListaConfigurabilePage; qui
// restano filtri custom, slot e azioni di riga. Righe dalla vista canonica
// `vw_ddt_lista`: destinatario=`destinatario_denominazione`,
// id.fiscale=`id_fiscale_univoco_cf_piva`, ba_codice, causale/aspetto/vettore/
// mittente, ordine_origine_numero. Clone di OrdiniSearchTable (§D-4).
//
// Scostamento vs ordini: NIENTE export (nessun endpoint BE /vendite/ddt/export/,
// export fuori scope in questa slice) → azione 'export' filtrata da pageActions
// e ExportDialog non montato. NIENTE azione PDF di riga (PDF fuori scope).
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import ListaConfigurabile from '../../../core/components/ListaConfigurabile.vue'
import DdtNoteDrawer from './DdtNoteDrawer.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../../core/composables/useStoreFilterBindings'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { DATE_FORMAT, MANAGE_ICONS, TAB_ENTITIES, TIPO_RUOLO } from '../../../core/constants'
import { statoDdtSeverity } from '../../../core/utils/severity'
import { useDdtStore } from '../stores/ddt'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useDdtStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  onConfigLoaded, pageActions: pageActionsRaw,
} = useListaConfigurabilePage(store, {
  // Nessun exportFn: l'export DDT e' fuori scope (nessun endpoint BE).
  newTooltipKey: 'vendite.ddt.nuovo_ddt',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// Toglie l'azione 'export' dalla toolbar: senza endpoint BE il pulsante sarebbe
// un vicolo cieco. Le restanti utility (reload/personalizza) + new restano.
const pageActions = computed(() => pageActionsRaw.value.filter(a => a.key !== 'export'))

// --- Filtri custom (toolbar caller) — binding store via BB ---
const { bindSelect, bindDate } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_codice_interno')
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da')
const { value: dataAlFilter, onChange: onDataAlChange } = bindDate('data_a')

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

// ── Drawer note (azione di riga) ──
const noteDrawerVisible = ref(false)
const noteDrawerDdt = ref(null)

function onNoteClick(row) {
  if (!row?.id) return
  noteDrawerDdt.value = row
  noteDrawerVisible.value = true
}

// Scopo: azioni contestuali di riga. Modifica = click riga. Emissione/cambio
// stato/push vivono nel drawer (dove sono caricate le capability), non in lista:
// la lista resta consultazione + gestione note.
function buildRowActions(data) {
  return [
    {
      key: 'gestisci-note',
      label: t('vendite.ddt.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => onNoteClick(data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.DDT)

// Lista con filtro data_da default anno-1: auto-load al mount (lo store guard
// hasFilters considera data_da come filtro attivo).
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- Toolbar UNICA esterna (pattern lista standard). -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="searchText" :placeholder="t('vendite.ddt.search_placeholder')" style="width: 260px;" />
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_ddt"
            value-field="codice_interno"
            :placeholder="t('vendite.ddt.filtro_stato')"
            show-clear
            style="width: 160px;"
            @change="onStatoChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.ddt.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
            :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
            @date-select="onDataDaChange" @clear-click="onDataDaChange" />
          <DatePicker v-model="dataAlFilter" :placeholder="t('common.data_a')"
            :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
            @date-select="onDataAlChange" @clear-click="onDataAlChange" />
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
        codice="vendite.ddt"
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
        <!-- Numero: NULL in DRAFT (assegnato solo a EMESSO) → mostra "—". -->
        <template #cell-numero="{ data }">
          {{ data.numero || '—' }}
        </template>

        <!-- Stato: Tag severity data-driven (statoDdtSeverity). -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoDdtSeverity(data.stato_codice_interno)" />
        </template>

        <template #actions="{ data, compact }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" :force-compact="compact" />
        </template>
      </ListaConfigurabile>
    </template>

    <DdtNoteDrawer
      v-if="noteDrawerDdt?.id"
      v-model:visible="noteDrawerVisible"
      :ddt-id="noteDrawerDdt.id"
    />
  </div>
</template>
