<script setup>
// Scopo: DataTable paginata matrice utilities x tipi_ruolo con filtri search,
//        attivo, utility, tipo_ruolo. Pattern unita_misura.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtilitiesTipiRuoloStore } from '../stores/utilitiesTipiRuolo'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectReadonly, useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import LookupSelect from '../../core/components/LookupSelect.vue'
import NewButton from '../../core/components/NewButton.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useUtilitiesTipiRuoloStore()
const isReadonly = useInjectReadonly()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'utility_descrizione'
})

const attivoFilter = ref(true)
const utilityFilter = ref(null)
const tipoRuoloFilter = ref(null)

const boolOptions = buildBoolOptions(t)

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
      <div class="app-page-actions">
        <ReadonlyBadge />
        <ReloadButton @click="reload" />
        <NewButton
          v-if="!isReadonly"
          :tooltip="t('amministrazione.matrice_utilities_ruoli.new_row')"
          @click="emit('new')"
        />
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
          <Tag
            :value="data.attivo ? t('common.active') : t('common.inactive')"
            :severity="data.attivo ? 'success' : 'warn'"
          />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
