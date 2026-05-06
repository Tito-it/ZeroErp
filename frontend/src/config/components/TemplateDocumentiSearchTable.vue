<script setup>
// Scopo: DataTable lista template documentali sotto Configurazione
//        (Tranche L). Pattern coerente con CategorieClientiSearchTable
//        + UtilitiesTipiRuoloSearchTable: search + filtri (sorgente,
//        attivo) + RowActionsMenu (modifica). Le versioni si gestiscono
//        nel drawer template testata.
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateDocumentiStore } from '../stores/templateDocumenti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
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
const store = useTemplateDocumentiStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } =
  useSearchTable(store, { defaultSortField: 'codice' })

const attivoFilter = ref(true)
const sorgenteTipoFilter = ref(null)
const tipoOutputFilter = ref(null)
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
    tooltip: t('config.modelli_documenti.new'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

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

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, TAB_ENTITIES.TEMPLATE_DOCUMENTI)
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
        <Column
          field="codice"
          :header="t('config.modelli_documenti.col_codice')"
          sortable
          style="width: 160px;"
        />
        <Column
          field="descrizione"
          :header="t('config.modelli_documenti.col_descrizione')"
          sortable
          style="min-width: 240px;"
        />
        <Column
          field="tipo_documento_output_descrizione"
          :header="t('config.modelli_documenti.col_tipo_output')"
          sortable
          style="width: 180px;"
        />
        <Column
          field="sorgente_tipo_descrizione"
          :header="t('config.modelli_documenti.col_sorgente')"
          sortable
          style="width: 180px;"
        />
        <Column
          field="emittente_fiscale_descrizione"
          :header="t('config.modelli_documenti.col_emittente')"
          style="width: 200px;"
        />
        <Column
          field="is_default"
          :header="t('config.modelli_documenti.col_is_default')"
          style="width: 110px;"
        >
          <template #body="{ data }">
            <Tag
              v-if="data.is_default"
              :value="t('common.yes')"
              severity="info"
            />
          </template>
        </Column>
        <Column
          field="attivo"
          :header="t('common.attivo')"
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
