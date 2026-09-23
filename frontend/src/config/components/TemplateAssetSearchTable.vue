<script setup>
// Scopo: Lista asset documentali configurabile
//        (`<ListaConfigurabile codice="documenti.template_asset">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro
//        dinamico e personalizzazione per utente. Le righe non si possono
//        eliminare fisicamente (trigger DB A3): soft-disable via PATCH
//        `attivo=false` o `valido_al`. Nessun export: il dominio non ha
//        endpoint (lo scaffolding omette l'azione da se').
import { onMounted } from 'vue'
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
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'

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

// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: assetTipoFilter, onChange: onAssetTipoChange } = bindSelect('asset_tipo_id')
const boolOptions = buildBoolOptions(t)

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
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('config.modelli_documenti.asset.search_placeholder')"
            />
          </template>
          <LookupSelect
            v-model="assetTipoFilter"
            class="app-filter-w-md"
            rel="documenti.tipi_asset_documento"
            :placeholder="t('config.modelli_documenti.asset.filter_tipo')"
            show-clear
            @change="onAssetTipoChange"
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
