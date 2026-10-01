<script setup>
// Scopo: Lista tipologie UoM configurabile
//        (`<ListaConfigurabile codice="catalogo.uom_tipi">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente. Nessun export: il dominio non ha
//        endpoint (lo scaffolding omette l'azione da se', non ricevendo
//        `exportFn`).
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo cio' che distingue questa lista — filtri, celle, testi.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUomTipiStore } from '../stores/uomTipi'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { TAB_ENTITIES } from '../../core/constants'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import { buildBoolOptions } from '../../core/utils/options'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useUomTipiStore()
// `applyFilters` lo possiede la pagina (legge la casella di ricerca): lo si
// chiede pigro, al cambio del filtro.
const pagina = ref(null)
const { bindSelect } = useStoreFilterBindings(store, () => pagina.value.applyFilters())
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const boolOptions = buildBoolOptions(t)
</script>

<template>
  <ListaPaginaSemplice
    ref="pagina"
    :store="store"
    codice="catalogo.uom_tipi"
    :tab-entity="TAB_ENTITIES.UOM_TIPI"
    :search-placeholder="t('catalogo.uom_tipi_search_placeholder')"
    new-tooltip-key="catalogo.nuovo_uom_tipo"
    default-sort-field="descrizione"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  >
    <template #filtri>
      <Select
        v-model="attivoFilter"
        class="app-filter-w-sm"
        :options="boolOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('catalogo.filtro_attivo')"
        @change="onAttivoChange"
      />
    </template>
    <template #cell-attivo="{ data }">
      <AttivoTag :active="data.attivo" />
    </template>
  </ListaPaginaSemplice>
</template>
