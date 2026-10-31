<script setup>
// Scopo: Il drawer della RICERCA UNIVERSALE dei soggetti (topbar).
// ⭐ Dal 2026-10-31 la lista e' a catalogo (`anagrafiche.ricerca_soggetti`,
//    113; brief-db-liste-datatable-grezze-secondo-giro riga 6): colonne,
//    personalizzazione e ordinamento dal catalogo, paginazione dello store. La
//    riga espansa resta su `SearchDetailTable` (eccezione nominata dalla regola
//    zero). ⛔ Fino a quel giorno una `DataTable` grezza con paginazione,
//    ordinamento e debounce scritti a mano.
// ⚠️ La colonna degli emittenti e' a catalogo SEMPRE accesa, e vuota per i
//    ruoli diversi da CLIENTE: il catalogo non sa legare la visibilita' di una
//    colonna al valore di un filtro (§3.2 del brief, limite dichiarato).
//    L'operatore puo' nasconderla dal preset personale.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import { lookupTipiRuoloRicerca } from '../api/ricerca'
import { useApiHandler } from '../composables/useApiHandler'
import { useDrawerTabLista } from '../composables/useDrawerTabLista'
import { useContextStore } from '../../stores/context'
import { useRicercaSoggettiStore } from '../stores/ricercaSoggetti'
import { DRAWER_WIDTH, MANAGE_ICONS, RICERCA, STATUS_ICONS, TIPO_RUOLO } from '../constants'
import { ROTTA_LISTA_PER_TIPO_RUOLO, ROTTA_LISTA_SOGGETTI, rottaListaTipoRuolo } from '../navigation'
import { termineCorto } from '../utils/listParams'
import AppDrawer from './AppDrawer.vue'
import DrawerTabLista from './DrawerTabLista.vue'
import SearchDetailTable from './details/SearchDetailTable.vue'
import { useAuthStore } from '../../stores/auth'

const { t } = useI18n()
const router = useRouter()
const { execute } = useApiHandler()
const context = useContextStore()
const auth = useAuthStore()
const store = useRicercaSoggettiStore()

const props = defineProps({
  visible: { type: Boolean, required: true }
})

const emit = defineEmits(['update:visible'])

// ⭐ Il «padre» e' l'apertura: a drawer chiuso lo store si azzera (i risultati
//    della ricerca precedente non restano sotto la prossima).
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useDrawerTabLista(store, {
  parentId: () => (props.visible ? true : null),
})

// I tipi ruolo cercabili; il primo e' quello di partenza.
const tipiRuolo = ref([])
const selectedTipoRuolo = computed(
  () => tipiRuolo.value.find((r) => r.id === store.filters.tipo_ruolo_id) || null,
)

// Il messaggio del vuoto: sotto la soglia si dice quanti caratteri servono.
const termineInsufficiente = computed(() => {
  const termine = (searchText.value || '').trim()
  return !termine || termineCorto(termine, { minCaratteri: store.ricercaMinCaratteri })
})

// Etichetta di perimetro sulla ricerca (P-2c): chi cerca dentro piu' di un
// emittente deve saperlo PRIMA di leggere i risultati, e sui tipi ruolo
// diversi da CLIENTE e' l'unica informazione disponibile.

// Mappa tipo ruolo codice -> variante del componente dettaglio
const DETAIL_VARIANTS = { [TIPO_RUOLO.CLIENTE]: 'cliente', [TIPO_RUOLO.FORNITORE]: 'fornitore' }

const currentDetailVariant = computed(() => {
  return DETAIL_VARIANTS[selectedTipoRuolo.value?.codice] || 'generic'
})

// Scopo: carica i tipi ruolo visibili nella ricerca
async function loadTipiRuolo() {
  const data = await execute(
    () => lookupTipiRuoloRicerca(),
    { silent: true }
  )
  if (data?.results) {
    tipiRuolo.value = data.results
    applicaTipoDiPartenza()
  }
}

// Scopo: senza tipo ruolo la ricerca non si fa (l'endpoint lo vuole, 400), e
//        il dettaglio non sa che variante aprire: vuoto, torna il primo.
// ⚠️ Non basta al caricamento dei tipi (una volta sola): il `reset()` dello
//    store — alla chiusura, alla riapertura, su «Pulisci filtri» — lo riporta
//    a `null` (`filterDefaults`), e i tipi non si rileggono.
function applicaTipoDiPartenza() {
  if (store.filters.tipo_ruolo_id == null && tipiRuolo.value.length > 0) {
    store.filters.tipo_ruolo_id = tipiRuolo.value[0].id
  }
}
watch(() => store.filters.tipo_ruolo_id, applicaTipoDiPartenza)

// Scopo: cambiando tipo ruolo, la ricerca riparte.
function onFilterChange() {
  applyFilters()
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
    searchTerm: searchText.value
  })
  emit('update:visible', false)

  // Naviga solo se la pagina corrente non gestisce il contesto
  const currentRoute = router.currentRoute.value.name
  if (!CONTEXT_AWARE_ROUTES.has(currentRoute)) {
    const routeName = rottaListaTipoRuolo(codice)
    const query = searchText.value ? { search: searchText.value } : {}
    router.push({ name: routeName, query })
  }
}

// Scopo: naviga alla scheda anagrafica completa del soggetto
function handleOpenDetail() {
  const codice = selectedTipoRuolo.value?.codice
  const routeName = rottaListaTipoRuolo(codice)
  const query = searchText.value ? { search: searchText.value } : {}
  emit('update:visible', false)
  router.push({ name: routeName, query })
}

// Scopo: all'apertura i tipi ruolo (una volta).
// ⚠️ `immediate`: la topbar monta il drawer alla PRIMA apertura
//    (`ricercaMontata` in AppTopbar), quindi nasce con `visible` gia' true e
//    un watch senza `immediate` non scatta mai su quella apertura — la combo
//    dei tipi ruolo restava vuota fino alla seconda.
watch(() => props.visible, (newVal) => {
  if (newVal) {
    if (tipiRuolo.value.length === 0) {
      loadTipiRuolo()
    }
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
      <!-- Perimetro della ricerca: chi cerca dentro piu' di un emittente deve
           saperlo, perche' due omonimi di emittenti diversi sono voci
           indistinguibili. -->
      <div v-if="auth.perimetroMultiEmittente" class="search-perimetro">
        <i :class="STATUS_ICONS.INFO" />
        <span>{{ t('common.perimetro_emittente.etichetta_ricerca') }}</span>
      </div>

      <DrawerTabLista
        ref="listaRef"
        codice="anagrafiche.ricerca_soggetti"
        data-key="soggetto_id"
        :store="store"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        :page-actions="pageActions"
        :dirty="dirty"
        :perimetro-bloccato="perimetroBloccato"
        @page="onPage"
        @sort="onSort"
        @config-loaded="onConfigLoaded"
      >
        <template #filtri-sempre>
          <Select
            v-model="store.filters.tipo_ruolo_id"
            :options="tipiRuolo"
            option-label="descrizione"
            option-value="id"
            :placeholder="t('search.select_type')"
            class="search-tipo-select"
            @change="onFilterChange"
          />
          <InputText
            v-model="searchText"
            :placeholder="t('search.placeholder')"
            class="app-filter-w-lg"
          />
        </template>
        <template #empty>
          <div class="search-empty">
            {{ termineInsufficiente ? t('search.min_chars', { n: store.ricercaMinCaratteri ?? RICERCA.MIN_CARATTERI }) : t('common.no_results') }}
          </div>
        </template>
        <template #cell-utility_list="{ data }">{{ data.utility_list || '--' }}</template>
        <template #cell-emittente_ragione_sociale="{ data }">{{ data.emittente_ragione_sociale || '--' }}</template>
        <template #row-expansion="{ data }">
          <SearchDetailTable
            :row="data"
            :variant="currentDetailVariant"
            @set-context="handleSetContext"
            @open-detail="handleOpenDetail"
          />
        </template>
      </DrawerTabLista>
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

.search-tipo-select {
  width: 180px;
  flex-shrink: 0;
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

.search-empty {
  text-align: center;
  padding: 2rem;
  color: var(--app-text-muted);
}
</style>
