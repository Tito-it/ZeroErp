<script setup>
// Scopo: DataTable paginata matrice utilities x tipi_ruolo con filtri search,
//        attivo, utility, tipo_ruolo. Pattern unita_misura.
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtilitiesTipiRuoloStore } from '../stores/utilitiesTipiRuolo'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useUtilitiesTipiRuoloStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'utility_descrizione'
})

const attivoFilter = ref(true)
const utilityFilter = ref(null)
const tipoRuoloFilter = ref(null)

const boolOptions = buildBoolOptions(t)
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
    tooltip: t('amministrazione.matrice_utilities_ruoli.new_row'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

// LookupSelect emette `change` con il valore: usato per propagare la selezione
// allo store filters senza binding manuale @update:modelValue.
function onUtilityChange(value) {
  store.filters.utility_id = value ?? null
  applyFilters()
}

function onTipoRuoloChange(value) {
  store.filters.tipo_ruolo_id = value ?? null
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, TAB_ENTITIES.UTILITIES_TIPI_RUOLO)
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('amministrazione.matrice_utilities_ruoli.search_placeholder')"
        />
        <LookupSelect
          v-model="utilityFilter"
          @change="onUtilityChange"
          rel="config.utilities"
          :placeholder="t('amministrazione.matrice_utilities_ruoli.filter_utility')"
          showClear
          style="min-width: 200px;"
        />
        <LookupSelect
          v-model="tipoRuoloFilter"
          @change="onTipoRuoloChange"
          rel="config.tipi_ruoli"
          :placeholder="t('amministrazione.matrice_utilities_ruoli.filter_tipo_ruolo')"
          showClear
          style="min-width: 200px;"
        />
        <Select
          v-model="attivoFilter"
          :options="boolOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('common.attivo')"
          @change="onAttivoChange"
          style="width: 120px;"
        />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
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
      @row-click="onRowClick"
      selection-mode="single"
      data-key="id"
    >
      <Column
        field="utility_codice"
        :header="t('amministrazione.matrice_utilities_ruoli.col_utility_codice')"
        sortable
        style="width: 130px;"
      />
      <Column
        field="utility_descrizione"
        :header="t('amministrazione.matrice_utilities_ruoli.col_utility_descrizione')"
        sortable
        style="min-width: 220px;"
      />
      <Column
        field="tipo_ruolo_codice"
        :header="t('amministrazione.matrice_utilities_ruoli.col_tipo_ruolo_codice')"
        sortable
        style="width: 120px;"
      />
      <Column
        field="tipo_ruolo_descrizione"
        :header="t('amministrazione.matrice_utilities_ruoli.col_tipo_ruolo_descrizione')"
        sortable
        style="min-width: 220px;"
      />
      <Column
        field="attivo"
        :header="t('amministrazione.matrice_utilities_ruoli.col_attivo')"
        sortable
        style="width: 100px;"
      >
        <template #body="{ data }">
          <AttivoTag :active="data.attivo" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
