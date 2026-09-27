<script setup>
// Scopo: Lista admin della matrice utilities x tipi_ruolo, configurabile
//        (`<ListaConfigurabile codice="config.utilities_tipi_ruolo">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico
//        e personalizzazione per utente. Filtri search/attivo/utility/tipo_ruolo
//        restano del caller. Nessun export: il dominio non ha endpoint.
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo cio' che distingue questa lista — filtri, celle, testi.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtilitiesTipiRuoloStore } from '../stores/utilitiesTipiRuolo'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { TAB_ENTITIES } from '../../core/constants'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { buildBoolOptions } from '../../core/utils/options'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useUtilitiesTipiRuoloStore()
// `applyFilters` lo possiede la pagina (legge la casella di ricerca): lo si
// chiede pigro, al cambio del filtro.
const pagina = ref(null)
const { bindSelect } = useStoreFilterBindings(store, () => pagina.value.applyFilters())
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
const { value: tipoRuoloFilter, onChange: onTipoRuoloChange } = bindSelect('tipo_ruolo_id')
const boolOptions = buildBoolOptions(t)
</script>

<template>
  <ListaPaginaSemplice
    ref="pagina"
    :store="store"
    codice="config.utilities_tipi_ruolo"
    :tab-entity="TAB_ENTITIES.UTILITIES_TIPI_RUOLO"
    :search-placeholder="t('amministrazione.matrice_utilities_ruoli.search_placeholder')"
    new-tooltip-key="amministrazione.matrice_utilities_ruoli.new_row"
    default-sort-field="utility_descrizione"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  >
    <template #filtri>
      <LookupSelect
        v-model="utilityFilter"
        class="app-filter-w-md"
        rel="config.utilities"
        :placeholder="t('amministrazione.matrice_utilities_ruoli.filter_utility')"
        show-clear
        @change="onUtilityChange"
      />
      <LookupSelect
        v-model="tipoRuoloFilter"
        class="app-filter-w-md"
        rel="config.tipi_ruoli"
        :placeholder="t('amministrazione.matrice_utilities_ruoli.filter_tipo_ruolo')"
        show-clear
        @change="onTipoRuoloChange"
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
    </template>
    <template #cell-attivo="{ data }">
      <AttivoTag :active="data.attivo" />
    </template>
  </ListaPaginaSemplice>
</template>
