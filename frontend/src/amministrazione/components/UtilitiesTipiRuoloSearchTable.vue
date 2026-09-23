<script setup>
// Scopo: Lista admin della matrice utilities x tipi_ruolo, configurabile
//        (`<ListaConfigurabile codice="config.utilities_tipi_ruolo">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico
//        e personalizzazione per utente. Filtri search/attivo/utility/tipo_ruolo
//        restano del caller. Nessun export: il dominio non ha endpoint.
import { onMounted } from 'vue'
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
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'

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

// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
const { value: tipoRuoloFilter, onChange: onTipoRuoloChange } = bindSelect('tipo_ruolo_id')

const boolOptions = buildBoolOptions(t)

// LookupSelect emette `change` con il valore: usato per propagare la selezione
// allo store filters senza binding manuale @update:modelValue.

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
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText
            v-model="searchText"
            class="app-filter-w-lg"
            :placeholder="t('amministrazione.matrice_utilities_ruoli.search_placeholder')"
          />
        </template>
        <LookupSelect
          v-model="utilityFilter"
          class="app-filter-w-md"
          @change="onUtilityChange"
          rel="config.utilities"
          :placeholder="t('amministrazione.matrice_utilities_ruoli.filter_utility')"
          showClear
        />
        <LookupSelect
          v-model="tipoRuoloFilter"
          class="app-filter-w-md"
          @change="onTipoRuoloChange"
          rel="config.tipi_ruoli"
          :placeholder="t('amministrazione.matrice_utilities_ruoli.filter_tipo_ruolo')"
          showClear
        />
        <Select
          v-model="attivoFilter"
          class="app-filter-w-sm"
          :options="boolOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('common.attivo')"
          @change="onAttivoChange"
        />
      </FiltriLista>
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
