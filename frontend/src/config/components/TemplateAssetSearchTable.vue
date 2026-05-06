<script setup>
// Scopo: DataTable lista asset documentali (Tranche L). Pattern coerente
//        con TemplateDocumentiSearchTable. Le righe non si possono
//        eliminare fisicamente (trigger DB A3): soft-disable via PATCH
//        `attivo=false` o `valido_al`.
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateAssetDocumentiStore } from '../stores/templateAssetDocumenti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import { formatSize } from '../../core/utils/format'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import LookupSelect from '../../core/components/LookupSelect.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useTemplateAssetDocumentiStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } =
  useSearchTable(store, { defaultSortField: 'codice' })

const attivoFilter = ref(true)
const assetTipoFilter = ref(null)
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
    tooltip: t('config.modelli_documenti.asset.new'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}
function onAssetTipoChange() {
  store.filters.asset_tipo_id = assetTipoFilter.value
  applyFilters()
}
function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, TAB_ENTITIES.TEMPLATE_ASSET_DOCUMENTI)
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
        <Column field="codice" :header="t('config.modelli_documenti.asset.col_codice')" sortable style="width: 160px;" />
        <Column field="descrizione" :header="t('config.modelli_documenti.asset.col_descrizione')" sortable style="min-width: 240px;" />
        <Column field="asset_tipo_descrizione" :header="t('config.modelli_documenti.asset.col_tipo')" sortable style="width: 160px;" />
        <Column field="mime_type" :header="t('config.modelli_documenti.asset.col_mime')" style="width: 160px;" />
        <Column field="file_name" :header="t('config.modelli_documenti.asset.col_file_name')" style="min-width: 200px;" />
        <Column field="file_size_bytes" :header="t('config.modelli_documenti.asset.col_size')" sortable style="width: 110px;">
          <template #body="{ data }">
            {{ formatSize(data.file_size_bytes) }}
          </template>
        </Column>
        <Column field="emittente_fiscale_descrizione" :header="t('config.modelli_documenti.col_emittente')" style="width: 200px;" />
        <Column field="attivo" :header="t('common.attivo')" sortable style="width: 100px;">
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
