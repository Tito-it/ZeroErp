<script setup>
// Scopo: DataTable paginata matrice tipi_ruolo x tipi_indirizzo con search e filtri.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTipiRuoloTipiIndirizzoStore } from '../stores/tipiRuoloTipiIndirizzo'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly, useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import NewButton from '../../core/components/NewButton.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useTipiRuoloTipiIndirizzoStore()
const isReadonly = useInjectReadonly()
const isBlocked = useInjectBlocked()
const { execute } = useApiHandler()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'tipo_ruolo_descrizione'
})

useTabFreshness(store, TAB_ENTITIES.TIPI_RUOLO_TIPI_INDIRIZZO)

const tipoRuoloFilter = ref(store.filters.tipo_ruolo_id)
const tipoIndirizzoFilter = ref(store.filters.tipo_indirizzo_id)
const attivoFilter = ref(store.filters.attivo)

const attivoOptions = [
  { value: true, label: t('common.attivo') },
  { value: false, label: t('common.non_attivo') }
]

const fallbackOptionsByRow = ref({})
const fallbackOptionsLoadingByRow = ref({})

// Scopo: opzioni fallback inline, riusando gli stessi metadata del drawer
// (`fallback_options` calcolate dal backend sul detail: no self-ref + no cicli).
function fallbackOptions(row) {
  if (fallbackOptionsByRow.value[row.id]) return fallbackOptionsByRow.value[row.id]
  if (!row.fallback_tipo_indirizzo_id) return []
  return [{
    tipo_indirizzo_id: row.fallback_tipo_indirizzo_id,
    codice: row.fallback_codice,
    descrizione: row.fallback_descrizione || row.fallback_codice
  }]
}

async function loadFallbackOptions(row) {
  if (fallbackOptionsByRow.value[row.id] || fallbackOptionsLoadingByRow.value[row.id]) return
  fallbackOptionsLoadingByRow.value[row.id] = true
  try {
    const detail = await store.fetchDetail(row.id)
    fallbackOptionsByRow.value[row.id] = Array.isArray(detail?.fallback_options)
      ? detail.fallback_options
      : []
  } finally {
    fallbackOptionsLoadingByRow.value[row.id] = false
  }
}

function onTipoRuoloChange() {
  store.filters.tipo_ruolo_id = tipoRuoloFilter.value
  applyFilters()
}
function onTipoIndirizzoChange() {
  store.filters.tipo_indirizzo_id = tipoIndirizzoFilter.value
  applyFilters()
}
function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

async function changeFallback(row, newFallbackId) {
  const result = await execute(
    () => store.update(row.id, { fallback_tipo_indirizzo_id: newFallbackId || null }),
    { successMessage: t('amministrazione.matrice_indirizzi_ruoli.saved') }
  )
  if (result !== null) {
    row.fallback_tipo_indirizzo_id = result.fallback_tipo_indirizzo_id
    row.fallback_codice = result.fallback_codice
    row.fallback_descrizione = result.fallback_descrizione
    fallbackOptionsByRow.value[row.id] = Array.isArray(result.fallback_options)
      ? result.fallback_options
      : fallbackOptionsByRow.value[row.id]
  }
}

onMounted(() => { if (!store.hasSearched) store.fetchList() })
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('amministrazione.matrice_indirizzi_ruoli.search_placeholder')"
          @keydown.enter="applyFilters" />
        <LookupSelect v-model="tipoRuoloFilter" rel="config.tipi_ruoli"
          :placeholder="t('amministrazione.matrice_indirizzi_ruoli.filter_tipo_ruolo')"
          show-clear @change="onTipoRuoloChange" />
        <LookupSelect v-model="tipoIndirizzoFilter" rel="config.tipi_indirizzi"
          :placeholder="t('amministrazione.matrice_indirizzi_ruoli.filter_tipo_indirizzo')"
          show-clear @change="onTipoIndirizzoChange" />
        <Select v-model="attivoFilter" :options="attivoOptions" option-label="label" option-value="value"
          :placeholder="t('common.tutti')" show-clear @change="onAttivoChange" />
      </div>
      <div class="app-page-actions">
        <ReadonlyBadge />
        <ReloadButton @click="reload" />
        <NewButton v-if="!isReadonly" :tooltip="t('amministrazione.matrice_indirizzi_ruoli.new_row')" @click="emit('new')" />
      </div>
    </div>

    <DataTable :value="store.items" :loading="store.loading" lazy :totalRecords="store.totalRecords"
      v-bind="paginatorProps" @page="onPage" @sort="onSort"
      striped-rows scrollable scrollHeight="flex" class="app-datatable"
      data-key="id" @row-click="e => emit('row-click', e.data)">
      <template #empty>
        <div class="app-empty-state">{{ t('common.empty_list') }}</div>
      </template>

      <Column field="tipo_ruolo_codice" :header="t('amministrazione.matrice_indirizzi_ruoli.col_tipo_ruolo_codice')" sortable style="width: 120px;" />
      <Column field="tipo_ruolo_descrizione" :header="t('amministrazione.matrice_indirizzi_ruoli.col_tipo_ruolo_descrizione')" sortable style="min-width: 180px;" />
      <Column field="tipo_indirizzo_codice" :header="t('amministrazione.matrice_indirizzi_ruoli.col_tipo_indirizzo_codice')" sortable style="width: 120px;" />
      <Column field="tipo_indirizzo_descrizione" :header="t('amministrazione.matrice_indirizzi_ruoli.col_tipo_indirizzo_descrizione')" sortable style="min-width: 180px;" />
      <Column field="obbligatorio" :header="t('amministrazione.matrice_indirizzi_ruoli.col_obbligatorio')" style="width: 110px;">
        <template #body="{ data }">
          <Tag :value="data.obbligatorio ? t('common.yes') : t('common.no')"
            :severity="data.obbligatorio ? 'warn' : 'secondary'" />
        </template>
      </Column>
      <Column field="fallback_codice" :header="t('amministrazione.matrice_indirizzi_ruoli.col_fallback')" style="width: 190px;">
        <template #body="{ data }">
          <div @click.stop>
            <Select
              :modelValue="data.fallback_tipo_indirizzo_id"
              @before-show="loadFallbackOptions(data)"
              @focus="loadFallbackOptions(data)"
              @update:modelValue="val => changeFallback(data, val)"
              :options="fallbackOptions(data)"
              option-label="descrizione"
              option-value="tipo_indirizzo_id"
              :placeholder="t('amministrazione.matrice_indirizzi_ruoli.no_fallback')"
              :disabled="isReadonly || fallbackOptionsLoadingByRow[data.id]"
              show-clear
              filter
              class="w-full"
              style="min-width: 150px;"
            />
          </div>
        </template>
      </Column>
      <Column field="attivo" :header="t('amministrazione.matrice_indirizzi_ruoli.col_attivo')" sortable style="width: 100px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.attivo') : t('common.non_attivo')"
            :severity="data.attivo ? 'success' : 'danger'" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
