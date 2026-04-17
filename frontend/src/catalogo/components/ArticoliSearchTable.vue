<script setup>
// Scopo: DataTable paginata articoli con search, filtri e ordinamento.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticoliStore } from '../stores/articoli'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { MANAGE_ICONS } from '../../core/constants'

const emit = defineEmits(['new', 'row-click', 'manage-uom', 'manage-bom', 'manage-note'])
const { t } = useI18n()
const store = useArticoliStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'descrizione'
})

const attivoFilter = ref(true)
const compositoFilter = ref(null)
const utilityFilter = ref(null)
const tipologiaFilter = ref(null)
const gruppoFilter = ref(null)

const boolOptions = [
  { value: null, label: t('common.all') },
  { value: true, label: t('common.yes') },
  { value: false, label: t('common.no') }
]
const attivoOptions = [
  { value: true, label: t('common.active') },
  { value: false, label: t('common.inactive') },
]

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}
function onCompositoChange() {
  store.filters.is_composito = compositoFilter.value
  applyFilters()
}
function onUtilityChange() {
  store.filters.voce_utility = utilityFilter.value
  applyFilters()
}
function onTipologiaChange() {
  store.filters.tipo_voce_id = tipologiaFilter.value
  applyFilters()
}
function onGruppoChange() {
  store.filters.gruppo_voce_id = gruppoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

// Scopo: azioni di riga dell'articolo (sub-drawer gestionali).
// BoM disabilitato su articoli non compositi (guard gia' presente nel drawer).
function buildRowActions(data) {
  return [
    {
      key: 'manage-uom',
      label: t('catalogo.gestisci_uom'),
      icon: MANAGE_ICONS.UOM,
      command: () => emit('manage-uom', data),
    },
    {
      key: 'manage-bom',
      label: t('catalogo.gestisci_bom'),
      icon: MANAGE_ICONS.BOM,
      disabled: !data.is_composito,
      command: () => emit('manage-bom', data),
    },
    {
      key: 'manage-note',
      label: t('catalogo.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => emit('manage-note', data),
    },
  ]
}

useTabFreshness(store, 'articolo')
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('catalogo.search_placeholder')" />
        <Select v-model="attivoFilter" :options="attivoOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" style="width: 130px;" />
        <Select v-model="compositoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_composito')" show-clear @change="onCompositoChange" style="width: 160px;" />
        <Select v-model="utilityFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_utility')" show-clear @change="onUtilityChange" style="width: 160px;" />
        <LookupSelect v-model="tipologiaFilter" rel="vendite.articoli_tipologie"
          :placeholder="t('catalogo.filtro_tipologia')" show-clear @change="onTipologiaChange" style="width: 150px;" />
        <LookupSelect v-model="gruppoFilter" rel="vendite.articoli_gruppi"
          :placeholder="t('catalogo.filtro_gruppo')" show-clear @change="onGruppoChange" style="width: 150px;" />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('catalogo.nuovo_articolo')" @click="emit('new')" />
      </div>
    </div>

    <SearchHint v-if="!store.hasSearched && !store.loading" />

    <DataTable
      v-show="store.hasSearched || store.loading"
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy removable-sort striped-rows scrollable scrollHeight="flex"
      class="app-datatable"
      @page="onPage" @sort="onSort" @row-click="onRowClick"
      selection-mode="single" data-key="id"
    >
      <Column field="codice" :header="t('catalogo.col_codice')" sortable style="width: 100px;">
        <template #body="{ data }">
          <span class="codice-truncate" :title="data.codice">{{ data.codice }}</span>
        </template>
      </Column>
      <Column field="descrizione" :header="t('catalogo.col_descrizione')" sortable style="width: 220px;">
        <template #body="{ data }">
          <span class="desc-truncate" :title="data.descrizione">{{ data.descrizione }}</span>
        </template>
      </Column>
      <Column field="uom_codice" :header="t('catalogo.col_uom')" sortable style="width: 80px;" />
      <Column field="tipologia_descrizione" :header="t('catalogo.col_tipologia')" style="width: 120px;" />
      <Column field="gruppo_descrizione" :header="t('catalogo.col_gruppo')" style="width: 120px;" />
      <Column field="iva_ref_id" :header="t('catalogo.col_iva')" style="width: 70px;">
        <template #body="{ data }">{{ data.iva_aliquota_iva != null ? `${data.iva_aliquota_iva}%` : '' }}</template>
      </Column>
      <Column field="is_solo_componente" :header="t('catalogo.col_solo_comp')" style="width: 90px;">
        <template #body="{ data }">
          <Tag :value="data.is_solo_componente ? t('common.yes') : t('common.no')" :severity="data.is_solo_componente ? 'info' : 'secondary'" />
        </template>
      </Column>
      <Column field="attivo" :header="t('catalogo.col_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.codice-truncate,
.desc-truncate {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
