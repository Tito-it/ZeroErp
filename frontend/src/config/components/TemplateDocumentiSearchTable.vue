<script setup>
// Scopo: Lista template documentali configurabile
//        (`<ListaConfigurabile codice="documenti.template_documenti">`):
//        colonne, ordine e visibilita' dal catalogo `ui.lista_colonna`, con
//        ritiro dinamico e personalizzazione per utente. Search + filtri
//        (tipo output, sorgente, attivo); le versioni si gestiscono nel drawer
//        template testata. Nessun export: il dominio non ha endpoint (lo
//        scaffolding omette l'azione da se', non ricevendo `exportFn`).
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateDocumentiStore } from '../stores/templateDocumenti'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useTemplateDocumentiStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'config.modelli_documenti.new',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'codice' },
})

const attivoFilter = ref(true)
const sorgenteTipoFilter = ref(null)
const tipoOutputFilter = ref(null)

const boolOptions = buildBoolOptions(t)

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}
function onSorgenteChange() {
  store.filters.sorgente_tipo_id = sorgenteTipoFilter.value
  applyFilters()
}
function onTipoOutputChange() {
  store.filters.tipo_documento_output_id = tipoOutputFilter.value
  applyFilters()
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

useTabFreshness(store, TAB_ENTITIES.TEMPLATE_DOCUMENTI)
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
            :placeholder="t('config.modelli_documenti.search_placeholder')"
          />
          <LookupSelect
            v-model="tipoOutputFilter"
            rel="documenti.tipi_documento_output"
            :placeholder="t('config.modelli_documenti.filter_tipo_output')"
            show-clear
            @change="onTipoOutputChange"
          />
          <LookupSelect
            v-model="sorgenteTipoFilter"
            rel="config.sorgenti"
            :placeholder="t('config.modelli_documenti.filter_sorgente')"
            show-clear
            @change="onSorgenteChange"
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
        codice="documenti.template_documenti"
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
        <template #cell-is_default="{ data }">
          <Tag v-if="data.is_default" :value="t('common.yes')" severity="info" />
        </template>
        <template #cell-attivo="{ data }">
          <AttivoTag :active="data.attivo" />
        </template>
      </ListaConfigurabile>
    </template>
  </div>
</template>
