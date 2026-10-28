<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import { lookupTipiRuoloRicerca, ricercaSoggetti } from '../api/ricerca'
import { useApiHandler } from '../composables/useApiHandler'
import { usePagination } from '../composables/usePagination'
import { useContextStore } from '../../stores/context'
import { DRAWER_WIDTH, MANAGE_ICONS, RICERCA, STATUS_ICONS, TIPO_RUOLO } from '../constants'
import { ROTTA_LISTA_PER_TIPO_RUOLO, ROTTA_LISTA_SOGGETTI, rottaListaTipoRuolo } from '../navigation'
import { termineCorto } from '../utils/listParams'
import AppDrawer from './AppDrawer.vue'
import SearchDetailTable from './details/SearchDetailTable.vue'
import { useAuthStore } from '../../stores/auth'



const { t } = useI18n()
const router = useRouter()
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
// Il termine come lo legge il backend (`require_min_search_length` fa lo
// `strip`): la soglia si misura su questo, non sul testo della casella —
// « ab» sono tre caratteri nella casella e un 400 per il backend. La soglia
// e' quella di progetto (`termineCorto` senza `minCaratteri`): la ricerca
// universale non e' una lista a catalogo.
const termine = computed(() => searchTerm.value.trim())
const termineInsufficiente = computed(() => !termine.value || termineCorto(termine.value))
const auth = useAuthStore()

// Etichetta di perimetro sulla ricerca (P-2c): qui il rischio non e' «non
// capisco», e' «scelgo fra due voci uguali» — due clienti omonimi di due
// emittenti diversi. Bloccare una ricerca sarebbe sproporzionato: si dichiara
// il perimetro e si lascia cercare.
//
// ✅ Residuo D-3 CHIUSO il 2026-08-18: `fn_search_soggetti_universale` espone
//    ora `emittente_ragione_sociale` (changeSet `20260818-60`), e la colonna e'
//    in tabella per i CLIENTI — due omonimi di emittenti diversi si
//    distinguono.
// ⚠️ L'etichetta di perimetro resta, e non e' ridondante: la colonna dice da
//    quale emittente arriva OGNI RIGA, l'etichetta dice che la ricerca sta
//    guardando piu' emittenti — che e' l'informazione utile PRIMA di leggere i
//    risultati, e l'unica disponibile sui tipi ruolo diversi da CLIENTE.
const results = ref([])
const expandedRows = ref({})
const sortField = ref('ragione_sociale_completa')
const sortOrder = ref(1)
let debounceTimer = null

// Mappa tipo ruolo codice -> variante del componente dettaglio
const DETAIL_VARIANTS = { [TIPO_RUOLO.CLIENTE]: 'cliente', [TIPO_RUOLO.FORNITORE]: 'fornitore' }

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
    () => lookupTipiRuoloRicerca(),
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
  if (!selectedTipoRuolo.value || termineInsufficiente.value) {
    results.value = []
    return
  }

  const params = {
    q: termine.value,
    tipo_ruolo_id: selectedTipoRuolo.value.id,
    ...pagination.queryParams.value,
    ...(sortField.value ? { order_by: sortField.value, order_dir: sortOrder.value === 1 ? 'ASC' : 'DESC' } : {})
  }

  const data = await execute(
    () => ricercaSoggetti(params),
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
  sortField.value = 'ragione_sociale_completa'
  sortOrder.value = 1
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
  [TIPO_RUOLO.CLIENTE]: 'cliente_id',
  [TIPO_RUOLO.FORNITORE]: 'fornitore_id'
}

// Rotte che possono gestire il contesto senza navigazione (hanno watcher su ctx):
// sono le liste d'arrivo di `rottaListaTipoRuolo`, tutte e sole.
const CONTEXT_AWARE_ROUTES = new Set([
  ROTTA_LISTA_SOGGETTI,
  ...Object.values(ROTTA_LISTA_PER_TIPO_RUOLO),
])

// Scopo: imposta il contesto globale dall'entita' selezionata, chiude il drawer.
// Se la pagina corrente puo' gestire il contesto, non naviga (il watcher della View
// aprira' il drawer). Altrimenti naviga alla lista corrispondente.
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
    },
    searchTerm: searchTerm.value
  })
  emit('update:visible', false)

  // Naviga solo se la pagina corrente non gestisce il contesto
  const currentRoute = router.currentRoute.value.name
  if (!CONTEXT_AWARE_ROUTES.has(currentRoute)) {
    const routeName = rottaListaTipoRuolo(codice)
    const query = searchTerm.value ? { search: searchTerm.value } : {}
    router.push({ name: routeName, query })
  }
}

// Scopo: naviga alla scheda anagrafica completa del soggetto
function handleOpenDetail() {
  const codice = selectedTipoRuolo.value?.codice
  const routeName = rottaListaTipoRuolo(codice)
  const query = searchTerm.value ? { search: searchTerm.value } : {}
  emit('update:visible', false)
  router.push({ name: routeName, query })
}

// Scopo: reset stato quando il drawer viene aperto
// ⚠️ `immediate`: la topbar monta il drawer alla PRIMA apertura
//    (`ricercaMontata` in AppTopbar), quindi nasce con `visible` gia' true e
//    un watch senza `immediate` non scatta mai su quella apertura — la combo
//    dei tipi ruolo restava vuota fino alla seconda.
watch(() => props.visible, (newVal) => {
  if (newVal) {
    if (tipiRuolo.value.length === 0) {
      loadTipiRuolo()
    }
    expandedRows.value = {}
  }
}, { immediate: true })
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). Drawer di
       consultazione: footer «Chiudi», come ogni drawer che mostra una lista
       (fino a quel giorno non ne aveva, e si usciva solo dalla X). -->
  <AppDrawer
    :visible="visible"
    :title="t('search.title')"
    :icon="MANAGE_ICONS.RICERCA"
    :width="DRAWER_WIDTH.WIDE"
    :proteggi-corpo="false"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
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
            <i class="search-input-icon" :class="MANAGE_ICONS.RICERCA" />
            <InputText
              v-model="searchTerm"
              :placeholder="t('search.placeholder')"
              class="search-input"
              @input="onSearchInput"
            />
            <Button
              v-if="searchTerm"
              :icon="MANAGE_ICONS.SVUOTA"
              text
              rounded
              size="small"
              class="search-clear-btn"
              @click="searchTerm = ''; results = []; pagination.reset()"
            />
          </div>
        </div>

      </div>

      <!-- Perimetro della ricerca: chi cerca dentro piu' di un emittente deve
           saperlo, perche' due omonimi di emittenti diversi sono voci
           indistinguibili. -->
      <div v-if="auth.perimetroMultiEmittente" class="search-perimetro">
        <i :class="STATUS_ICONS.INFO" />
        <span>{{ t('common.perimetro_emittente.etichetta_ricerca') }}</span>
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
            {{ termineInsufficiente ? t('search.min_chars', { n: RICERCA.MIN_CARATTERI }) : t('common.no_results') }}
          </div>
        </template>

        <Column expander style="width: 3rem" />
        <Column field="soggetto_codice" :header="t('search.col_code')" sortable style="width: 90px" />
        <Column field="ragione_sociale_completa" :header="t('search.col_name')" sortable />
        <Column field="id_fiscale_univoco" :header="t('search.col_fiscal_id')" sortable style="width: 160px" />
        <!-- ⛔ Non ordinabile (2026-10-10, brief-db-ricerca-universale-tetto-10000
             D-2): è un aggregato che il DB calcola per le sole righe della
             pagina, e `p_order_by` lo rifiuta. -->
        <Column
          v-if="selectedTipoRuolo?.codice === TIPO_RUOLO.CLIENTE"
          field="utility_list"
          :header="t('search.col_utility')"
          style="width: 80px"
        >
          <template #body="{ data }">
            {{ data.utility_list || '--' }}
          </template>
        </Column>
        <!-- Emittente/i presso cui il soggetto è cliente (R-5 del brief Fase E).
             ⚠️ L'intestazione NON è «Emittente»: su una riga-soggetto questa
             colonna mostra una RELAZIONE, non un attributo — il soggetto non
             ha un emittente, ce l'ha il suo billing account.
             ⚠️ Solo per i CLIENTI: sugli altri tipi ruolo il valore è NULL per
             costruzione (una ricerca fornitori non ha perimetro emittente), e
             una colonna sempre vuota è peggio di nessuna colonna.
             ⚠️ NON `sortable`: il valore è un aggregato (`string_agg`) e
             ordinarci sopra ordinerebbe per la stringa concatenata (BE-E4). -->
        <Column
          v-if="selectedTipoRuolo?.codice === TIPO_RUOLO.CLIENTE"
          field="emittente_ragione_sociale"
          :header="t('search.col_emittenti')"
          style="width: 200px"
        >
          <template #body="{ data }">
            {{ data.emittente_ragione_sociale || '--' }}
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
  </AppDrawer>
</template>

<style scoped>

/* Layout base ereditato da .app-drawer-content (main.css) */
.search-drawer-content {
  display: flex;
  flex-direction: column;
  gap: var(--app-drawer-gap);
  height: 100%;
  min-width: 0;
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
  color: var(--app-icon-color);
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

.search-perimetro {
  /* Dichiarazione di perimetro: informazione di contorno, non un avviso. */
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-style: italic;
  opacity: 0.85;
  padding: 0.25rem 0.1rem 0.5rem;
}

.search-results-table {
  flex: 1;
  min-height: 0;
}

.search-empty {
  text-align: center;
  padding: 2rem;
  color: var(--app-text-muted);
}
</style>
