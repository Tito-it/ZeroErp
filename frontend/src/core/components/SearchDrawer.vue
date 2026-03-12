<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import api from '../api'
import { useApiHandler } from '../composables/useApiHandler'
import { usePagination } from '../composables/usePagination'
import { useContextStore } from '../../stores/context'
import { DRAWER_WIDTH } from '../constants'
import SearchDetailTable from './details/SearchDetailTable.vue'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const pagination = usePagination()
const context = useContextStore()

const props = defineProps({
  visible: { type: Boolean, required: true }
})
const emit = defineEmits(['update:visible'])

// Stato ricerca
const tipiRuolo = ref([])
const selectedTipoRuolo = ref(null)
const searchTerm = ref('')
const results = ref([])
const expandedRows = ref({})
const sortField = ref(null)
const sortOrder = ref(null)
let debounceTimer = null

// Mappa tipo ruolo codice -> variante del componente dettaglio
const DETAIL_VARIANTS = { CLIENTE: 'cliente', FORNITORE: 'fornitore' }

const currentDetailVariant = computed(() => {
  return DETAIL_VARIANTS[selectedTipoRuolo.value?.codice] || 'generic'
})

// Scopo: mostra il paginator solo se i risultati superano una pagina
const showPaginator = computed(() => {
  return pagination.totalRecords.value > pagination.rows.value
})

// Scopo: carica i tipi ruolo visibili nella ricerca
async function loadTipiRuolo() {
  const data = await execute(
    () => api.get('/core/lookup/tipi-ruoli/', { params: { ricerca_visibile: true } }),
    { silent: true }
  )
  if (data?.results) {
    tipiRuolo.value = data.results
    if (tipiRuolo.value.length > 0 && !selectedTipoRuolo.value) {
      selectedTipoRuolo.value = tipiRuolo.value[0]
    }
  }
}

// Scopo: esegue la ricerca soggetti con i parametri correnti
async function doSearch() {
  if (!selectedTipoRuolo.value || searchTerm.value.length < 3) {
    results.value = []
    return
  }

  const params = {
    q: searchTerm.value,
    tipo_ruolo_id: selectedTipoRuolo.value.id,
    ...pagination.queryParams.value,
    ...(sortField.value ? { order_by: sortField.value, order_dir: sortOrder.value === 1 ? 'ASC' : 'DESC' } : {})
  }

  const data = await execute(
    () => api.get('/core/search/', { params }),
    { silent: true }
  )
  if (data) {
    results.value = data.results || []
    pagination.updateFromResponse(data)
  }
}

// Scopo: gestisce il debounce della digitazione nel campo ricerca
function onSearchInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    pagination.reset()
    expandedRows.value = {}
    doSearch()
  }, 300)
}

// Cleanup timer al dismount per evitare leak
onUnmounted(() => clearTimeout(debounceTimer))

// Scopo: cambiando tipo ruolo, riesegue la ricerca e resetta espansioni e ordinamento
function onFilterChange() {
  pagination.reset()
  expandedRows.value = {}
  sortField.value = null
  sortOrder.value = null
  doSearch()
}

// Scopo: gestisce il cambio pagina nella tabella risultati
function onPage(event) {
  pagination.onPage(event)
  doSearch()
}

// Scopo: gestisce il click sull'header colonna per ordinamento
function onSort(event) {
  sortField.value = event.sortField
  sortOrder.value = event.sortOrder
  pagination.reset()
  doSearch()
}

// Mappa tipo ruolo codice -> chiave ID entita' nel JSONB di dettaglio
const ENTITA_ID_KEY = {
  CLIENTE: 'cliente_id',
  FORNITORE: 'fornitore_id'
}

// Scopo: imposta il contesto globale dall'entita' selezionata e chiude il drawer
function handleSetContext(row) {
  const codice = selectedTipoRuolo.value?.codice
  const entitaKey = ENTITA_ID_KEY[codice]

  context.setContext({
    tipo_ruolo_id: row.tipo_ruolo_id || selectedTipoRuolo.value?.id,
    tipo_ruolo_codice: codice,
    soggetto_id: row.soggetto_id,
    soggetto_ruolo_id: row.soggetto_ruolo_id,
    entita_id: entitaKey ? row[entitaKey] : null,
    label: row.ragione_sociale_completa,
    meta: {
      codice: row.soggetto_codice,
      id_fiscale: row.id_fiscale_univoco
    }
  })
  emit('update:visible', false)
}

// Scopo: naviga alla scheda anagrafica completa del soggetto
function handleOpenDetail(row) {
  // Navigazione alla scheda — da implementare quando le rotte anagrafiche saranno pronte
  emit('update:visible', false)
}

// Scopo: reset stato quando il drawer viene aperto
watch(() => props.visible, (newVal) => {
  if (newVal) {
    if (tipiRuolo.value.length === 0) {
      loadTipiRuolo()
    }
    expandedRows.value = {}
  }
})
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :modal="true"
    :dismissable="true"
    @update:visible="emit('update:visible', $event)"
  >
    <template #header>
      <span class="search-drawer-title">{{ t('search.title') }}</span>
    </template>

    <div class="search-drawer-content">
      <!-- Filtri ricerca -->
      <div class="search-filters">
        <div class="search-row-primary">
          <Select
            v-model="selectedTipoRuolo"
            :options="tipiRuolo"
            optionLabel="descrizione"
            :placeholder="t('search.select_type')"
            class="search-tipo-select"
            @change="onFilterChange"
          />
          <div class="search-input-wrapper">
            <i class="pi pi-search search-input-icon" />
            <InputText
              v-model="searchTerm"
              :placeholder="t('search.placeholder')"
              class="search-input"
              @input="onSearchInput"
            />
            <Button
              v-if="searchTerm"
              icon="pi pi-times"
              text
              rounded
              size="small"
              class="search-clear-btn"
              @click="searchTerm = ''; results = []; pagination.reset()"
            />
          </div>
        </div>

      </div>

      <!-- Risultati -->
      <DataTable
        v-model:expandedRows="expandedRows"
        :value="results"
        :loading="loading"
        dataKey="soggetto_id"
        size="small"
        stripedRows
        lazy
        removableSort
        :sortField="sortField"
        :sortOrder="sortOrder"
        :totalRecords="pagination.totalRecords.value"
        :rows="pagination.rows.value"
        :first="pagination.first.value"
        :rowsPerPageOptions="pagination.rowsOptions"
        :paginator="showPaginator"
        @page="onPage"
        @sort="onSort"
        class="search-results-table app-datatable"
      >
        <template #empty>
          <div class="search-empty">
            {{ searchTerm.length < 3 ? t('search.min_chars') : t('common.no_results') }}
          </div>
        </template>

        <Column expander style="width: 3rem" />
        <Column field="soggetto_codice" :header="t('search.col_code')" sortable style="width: 90px" />
        <Column field="ragione_sociale_completa" :header="t('search.col_name')" sortable />
        <Column field="id_fiscale_univoco" :header="t('search.col_fiscal_id')" sortable style="width: 160px" />
        <Column
          v-if="selectedTipoRuolo?.codice === 'CLIENTE'"
          field="utility_list"
          :header="t('search.col_utility')"
          sortable
          style="width: 80px"
        >
          <template #body="{ data }">
            {{ data.utility_list || '--' }}
          </template>
        </Column>

        <template #expansion="{ data }">
          <SearchDetailTable
            :row="data"
            :variant="currentDetailVariant"
            @set-context="handleSetContext"
            @open-detail="handleOpenDetail"
          />
        </template>
      </DataTable>
    </div>
  </Drawer>
</template>

<style scoped>
.search-drawer-title {
  font-weight: 600;
  font-size: var(--app-font-size-lg);
  color: var(--p-text-color);
}

.search-drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 0.75rem;
}

.search-filters {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.search-row-primary {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.search-tipo-select {
  width: 180px;
  flex-shrink: 0;
}

.search-input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.search-input-icon {
  position: absolute;
  left: 0.75rem;
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding-left: 2.25rem;
  padding-right: 2.25rem;
}

.search-clear-btn {
  position: absolute;
  right: 0.25rem;
}

.search-results-table {
  flex: 1;
  min-height: 0;
}

.search-empty {
  text-align: center;
  padding: 2rem;
  color: var(--p-text-muted-color);
}
</style>
