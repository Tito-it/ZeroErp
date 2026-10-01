<script setup>
// Scopo: Lista template documentali configurabile
//        (`<ListaConfigurabile codice="documenti.template_documenti">`):
//        colonne, ordine e visibilita' dal catalogo `ui.lista_colonna`, con
//        ritiro dinamico e personalizzazione per utente. Search + filtri
//        (tipo output, sorgente, attivo); le versioni si gestiscono nel drawer
//        template testata. Nessun export: il dominio non ha endpoint (lo
//        scaffolding omette l'azione da se', non ricevendo `exportFn`).
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo cio' che distingue questa lista — filtri, celle, testi.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateDocumentiStore } from '../stores/templateDocumenti'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { TAB_ENTITIES } from '../../core/constants'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { buildBoolOptions } from '../../core/utils/options'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useTemplateDocumentiStore()
// `applyFilters` lo possiede la pagina (legge la casella di ricerca): lo si
// chiede pigro, al cambio del filtro.
const pagina = ref(null)
const { bindSelect } = useStoreFilterBindings(store, () => pagina.value.applyFilters())
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: sorgenteTipoFilter, onChange: onSorgenteChange } = bindSelect('sorgente_tipo_id')
const { value: tipoOutputFilter, onChange: onTipoOutputChange } = bindSelect('tipo_documento_output_id')
const boolOptions = buildBoolOptions(t)
</script>

<template>
  <ListaPaginaSemplice
    ref="pagina"
    :store="store"
    codice="documenti.template_documenti"
    :tab-entity="TAB_ENTITIES.TEMPLATE_DOCUMENTI"
    :search-placeholder="t('config.modelli_documenti.search_placeholder')"
    new-tooltip-key="config.modelli_documenti.new"
    default-sort-field="codice"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  >
    <template #filtri>
      <LookupSelect
        v-model="tipoOutputFilter"
        class="app-filter-w-md"
        rel="documenti.tipi_documento_output"
        :placeholder="t('config.modelli_documenti.filter_tipo_output')"
        show-clear
        @change="onTipoOutputChange"
      />
      <LookupSelect
        v-model="sorgenteTipoFilter"
        class="app-filter-w-md"
        rel="config.sorgenti"
        :placeholder="t('config.modelli_documenti.filter_sorgente')"
        show-clear
        @change="onSorgenteChange"
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
    <template #cell-is_default="{ data }">
      <Tag v-if="data.is_default" :value="t('common.yes')" severity="info" />
    </template>
    <template #cell-attivo="{ data }">
      <AttivoTag :active="data.attivo" />
    </template>
  </ListaPaginaSemplice>
</template>
