<script setup>
// Scopo: Lista asset documentali configurabile
//        (`<ListaConfigurabile codice="documenti.template_asset">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro
//        dinamico e personalizzazione per utente. Le righe non si possono
//        eliminare fisicamente (trigger DB A3): soft-disable via PATCH
//        `attivo=false` o `valido_al`. Nessun export: il dominio non ha
//        endpoint (lo scaffolding omette l'azione da se').
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateAssetDocumentiStore } from '../stores/templateAssetDocumenti'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import { formatSize } from '../../core/utils/format'
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
const store = useTemplateAssetDocumentiStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'config.modelli_documenti.asset.new',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'codice' },
})

const attivoFilter = ref(true)
const assetTipoFilter = ref(null)
const boolOptions = buildBoolOptions(t)

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}
function onAssetTipoChange() {
  store.filters.asset_tipo_id = assetTipoFilter.value
  applyFilters()
}
// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

useTabFreshness(store, TAB_ENTITIES.TEMPLATE_ASSET_DOCUMENTI)
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
            :placeholder="t('config.modelli_documenti.asset.search_placeholder')"
          />
          <LookupSelect
            v-model="assetTipoFilter"
            rel="documenti.tipi_asset_documento"
            :placeholder="t('config.modelli_documenti.asset.filter_tipo')"
            show-clear
            @change="onAssetTipoChange"
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
        codice="documenti.template_asset"
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
        <!-- Byte grezzi a video sono illeggibili: la cella resta formattata,
             ma l'ordinamento e' numerico sul campo (BE, `a.file_size_bytes`). -->
        <template #cell-file_size_bytes="{ data }">
          {{ formatSize(data.file_size_bytes) }}
        </template>
        <template #cell-attivo="{ data }">
          <AttivoTag :active="data.attivo" />
        </template>
      </ListaConfigurabile>
    </template>
  </div>
</template>
