<script setup>
// Scopo: pannello gestione tabelle config — i VOCABOLARI della lista a DB
//        `config.tabelle_gestibili` con `pannello` (`GET /core/config/tables/`;
//        tutti ammessi al lookup generico: la lista qui sotto passa da li').
//        ⛔ Nessun registro nel frontend: fino al 2026-09-28 c'era
//        `config-tables.js`, terza copia della lista (D-P5,
//        brief-db-pannello-config-verbo-generico). Aggiungere una tabella =
//        una riga nel CSV del DB piu' l'etichetta
//        `config_panel.tabelle.<schema>.<tabella>` in it.json e en.json.
// Sinistra: lista tabelle raggruppate per schema.
// Destra: DataTable della tabella selezionata con CRUD generico.
// Note: ⚠️ Un errore della lista o del metadata va A VIDEO (toast di
//       `useApiHandler`), mai ingoiato: fino al 2026-09-21 un 400 su una tabella
//       dichiarata nel registro (`magazzino.lotti`, senza `descrizione`) si
//       vedeva come «lista vuota» — piano-be-fe-magazzino-anagrafiche-fuori-
//       dal-pannello-config §1.
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useReadonlyMode } from '../composables/useReadonlyMode'
import { useApiHandler } from '../composables/useApiHandler'
import { MANAGE_ICONS, READONLY_DOMAINS } from '../constants'
import { NAV_ICONS } from '../navigation'
import { labelOrCode } from '../utils/i18nLabel'
import { chiaveEtichettaTabella } from '../utils/campoConfig'
import { useDrawerState } from '../composables/useDrawerState'
import GenericConfigDrawer from './GenericConfigDrawer.vue'
import PageActionsBar from './PageActionsBar.vue'
// DataTable grezza: le colonne non stanno in un catalogo, le descrive
// `/metadata/` a runtime per la tabella di configurazione scelta.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import AttivoTag from './AttivoTag.vue'
import { getConfigTableMetadata, listConfigRecords, listConfigTables } from '../api/configTables'
import FiltriLista from './FiltriLista.vue'
import { USO_MISURA, misuraDefault, misureOpzioni } from '../misurePagina'

const { t, te } = useI18n()
useReadonlyMode(READONLY_DOMAINS.CONFIG)
const drawer = useDrawerState()
const { execute } = useApiHandler()

// Stato
const tabelle = ref([])
const selectedRel = ref(null)
const searchTable = ref('')
const searchRecords = ref('')
const items = ref([])
const totalRecords = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(misuraDefault(USO_MISURA.PAGINA))
const sortField = ref('descrizione')
const sortOrder = ref(1)

// Le tabelle del pannello. Una volta sola: la lista cambia col seed del DB,
// non durante la sessione. Lista non letta: il toast dice perche', e la
// colonna resta vuota.
onMounted(async () => {
  const data = await execute(() => listConfigTables())
  tabelle.value = data ? data.results : []
})

// Tabelle raggruppate per schema (schemi e tabelle in ordine alfabetico, le
// tabelle per etichetta), con l'etichetta tradotta
// (`config_panel.tabelle.<rel>`, ripiego fail-visible sulla rel), e filtrate.
// Computed e non costante: cambia col locale.
const tablesBySchema = computed(() => {
  const grouped = {}
  for (const tbl of tabelle.value) {
    if (!grouped[tbl.schema]) grouped[tbl.schema] = []
    grouped[tbl.schema].push({ ...tbl, label: labelOrCode(t, te, chiaveEtichettaTabella(tbl.rel), tbl.rel) })
  }
  const ordinato = {}
  for (const schema of Object.keys(grouped).sort()) {
    ordinato[schema] = grouped[schema].sort((a, b) => a.label.localeCompare(b.label))
  }
  return ordinato
})
const filteredTables = computed(() => {
  const q = searchTable.value.toLowerCase()
  if (!q) return tablesBySchema.value
  const result = {}
  for (const [schema, tables] of Object.entries(tablesBySchema.value)) {
    const filtered = tables.filter(tbl => tbl.label.toLowerCase().includes(q) || tbl.rel.includes(q))
    if (filtered.length > 0) result[schema] = filtered
  }
  return result
})

// Colonne disponibili (derivate dal metadata della tabella selezionata)
const tableColumns = ref([])
const hasCodice = computed(() => tableColumns.value.includes('codice'))
const hasAttivo = computed(() => tableColumns.value.includes('attivo'))
const hasCodiceInterno = computed(() => tableColumns.value.includes('codice_interno'))

// Label tabella selezionata
const selectedLabel = computed(() =>
  selectedRel.value ? labelOrCode(t, te, chiaveEtichettaTabella(selectedRel.value), selectedRel.value) : '',
)
const pageActions = computed(() => [
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: `${t('common.new')} ${selectedLabel.value}`,
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: onNew,
  },
])

// Carica metadata + records quando cambia la tabella selezionata
watch(selectedRel, async (rel) => {
  page.value = 1
  searchRecords.value = ''
  sortField.value = 'descrizione'
  sortOrder.value = 1
  tableColumns.value = []
  if (rel) {
    const meta = await execute(() => getConfigTableMetadata(rel))
    // Metadata non letto: il toast lo ha detto; la tabella resta con le sole
    // colonne fisse (codice/descrizione).
    if (meta) tableColumns.value = meta.columns.map(c => c.name)
  }
  loadRecords()
})

let searchTimeout = null
watch(searchRecords, () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => { page.value = 1; loadRecords() }, 400)
})
onUnmounted(() => clearTimeout(searchTimeout))

async function loadRecords() {
  if (!selectedRel.value) return
  loading.value = true
  try {
    const params = {
      // La finestra, non la pagina (2026-10-21, un dialetto solo).
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
      attivo_only: false,
    }
    if (searchRecords.value) params.search = searchRecords.value
    if (sortField.value) {
      params.order_col = sortField.value
      params.order_dir = sortOrder.value === -1 ? 'desc' : 'asc'
    }

    const data = await execute(() => listConfigRecords(selectedRel.value, params))
    // Lista non letta (toast gia' mostrato): vuota, e il totale a zero.
    items.value = data ? data.results : []
    totalRecords.value = data ? data.count : 0
  } finally {
    loading.value = false
  }
}

function onPage(event) {
  page.value = Math.floor(event.first / event.rows) + 1
  pageSize.value = event.rows
  loadRecords()
}

function onSort(event) {
  sortField.value = event.sortField
  sortOrder.value = event.sortOrder
  page.value = 1
  loadRecords()
}

function onRowClick(event) {
  if (!selectedRel.value) return
  drawer.editRow(event.data)
}

function onNew() {
  drawer.openCreate()
}

function onSaved() {
  loadRecords()
}

function selectTable(rel) {
  selectedRel.value = rel
}
</script>

<template>
  <div class="config-panel">
    <!-- Colonna sinistra: lista tabelle -->
    <div class="config-panel-nav">
      <InputText
        v-model="searchTable"
        :placeholder="t('config_panel.search_tabella')"
        class="config-panel-search"
      />
      <div class="config-panel-list">
        <template v-for="(tables, schema) in filteredTables" :key="schema">
          <div class="config-panel-schema">{{ schema.toUpperCase() }}</div>
          <div
            v-for="tbl in tables"
            :key="tbl.rel"
            class="config-panel-item"
            :class="{ 'config-panel-item-active': selectedRel === tbl.rel }"
            @click="selectTable(tbl.rel)"
          >
            {{ tbl.label }}
          </div>
        </template>
      </div>
    </div>

    <!-- Colonna destra: DataTable -->
    <div class="config-panel-content">
      <template v-if="selectedRel">
        <div class="app-page-toolbar">
          <!-- ⚠️ Nessuno `:store`: questo pannello non ha uno store-lista e non
               ha FILTRI — solo la ricerca, che per D2 non e' un filtro. Senza
               slot di default il building block non rende ne' l'imbuto ne' il
               drawer, quindi non c'e' nessun segno da alimentare. -->
          <FiltriLista>
            <template #sempre>
              <InputText
                v-model="searchRecords"
                class="app-filter-w-lg"
                :placeholder="t('config_panel.search_record')"
              />
            </template>
          </FiltriLista>
          <PageActionsBar :actions="pageActions" />
        </div>

        <DataTable
          :value="items"
          :loading="loading"
          :total-records="totalRecords"
          :rows="pageSize"
          :first="(page - 1) * pageSize"
          :rows-per-page-options="misureOpzioni()"
          paginator
          paginator-position="top"
          :paginator-template="'FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown CurrentPageReport'"
          :current-page-report-template="'{currentPage}/{totalPages}'"
          lazy
          removable-sort
          striped-rows
          scrollable
          scrollHeight="flex"
          class="app-datatable"
          :sortField="sortField"
          :sortOrder="sortOrder"
          @page="onPage"
          @sort="onSort"
          @row-click="onRowClick"
          selection-mode="single"
          data-key="id"
        >
          <Column v-if="hasCodice" field="codice" :header="t('config_panel.col_codice')" sortable />
          <Column v-if="hasCodiceInterno" field="codice_interno" :header="t('config_panel.col_codice_interno')" />
          <Column field="descrizione" :header="t('config_panel.col_descrizione')" sortable />
          <Column v-if="hasAttivo" field="attivo" :header="t('config_panel.col_attivo')">
            <template #body="{ data }">
              <AttivoTag :active="data.attivo" :active-label="t('config_panel.attivo')" :inactive-label="t('config_panel.non_attivo')" />
            </template>
          </Column>
        </DataTable>
      </template>

      <div v-else class="config-panel-empty">
        <i :class="NAV_ICONS.TABELLE" style="font-size: 2rem; opacity: 0.3;"></i>
        <p>{{ t('config_panel.select_tabella') }}</p>
      </div>
    </div>

    <!-- Drawer generico -->
    <GenericConfigDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :rel="selectedRel || ''"
      :label="selectedLabel"
      :record-id="drawer.state.itemId"
      @saved="onSaved"
    />
  </div>
</template>

<style scoped>
.config-panel {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  gap: 1rem;
}

.config-panel-nav {
  width: 260px;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--p-surface-200);
  padding-right: 1rem;
}

.config-panel-search {
  margin-bottom: 0.5rem;
  width: 100%;
}

.config-panel-list {
  flex: 1;
  overflow-y: auto;
}

.config-panel-schema {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--app-text-muted);
  padding: 0.5rem 0.5rem 0.25rem;
  margin-top: 0.5rem;
  letter-spacing: 0.05em;
}

.config-panel-schema:first-child {
  margin-top: 0;
}

.config-panel-item {
  padding: 0.4rem 0.75rem;
  cursor: pointer;
  border-radius: var(--p-border-radius-sm);
  font-size: 0.85rem;
  color: var(--app-text-color);
  transition: background 0.15s, color 0.15s;
  border-left: 3px solid transparent;
}

.config-panel-item:hover {
  background: var(--app-hover-bg);
  color: var(--p-text-hover-color);
  border-left-color: var(--p-primary-300);
}

.config-panel-item-active {
  background: var(--p-primary-50);
  color: var(--p-primary-700);
  font-weight: 600;
  border-left-color: var(--p-primary-500);
}

.config-panel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.config-panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--app-text-muted);
}
</style>
