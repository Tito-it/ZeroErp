<script setup>
// Scopo: Lista admin della matrice utilities x tipi_ruolo, configurabile
//        (`<ListaConfigurabile codice="config.utilities_tipi_ruolo">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico
//        e personalizzazione per utente. Filtri search/attivo/utility/tipo_ruolo
//        restano del caller. Nessun export: il dominio non ha endpoint.
import {ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtilitiesTipiRuoloStore } from '../stores/utilitiesTipiRuolo'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useUtilitiesTipiRuoloStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'amministrazione.matrice_utilities_ruoli.new_row',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'utility_descrizione' },
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

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

useTabFreshness(store, TAB_ENTITIES.UTILITIES_TIPI_RUOLO)
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters" :inert="perimetroBloccato">
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
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="config.utilities_tipi_ruolo"
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
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>
