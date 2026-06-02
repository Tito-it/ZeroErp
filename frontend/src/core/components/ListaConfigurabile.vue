<script setup>
// Scopo: Wrapper PrimeVue DataTable parametrizzato dalla configurazione
// risolta dal BE (`ui.fn_resolve_lista_config`). Costruisce le colonne
// dinamicamente, applica `tipo_colonna` per le icon column / azione,
// `fissata` per frozen, `esportabile` per filtrare l'export.
//
// Confine di responsabilita': il componente si occupa SOLO della
// configurazione di presentazione. Il caller fornisce i dati riga
// (`rows`), il `total`, il `loading`, e gestisce paginazione/sort
// reagendo agli eventi `@page`/`@sort`/`@filter`. Tipico:
//
//   <ListaConfigurabile
//     codice="anagrafiche.clienti"
//     :rows="store.items"
//     :total="store.total"
//     :loading="store.loading"
//     @page="onPage"
//     @sort="onSort"
//     @row-click="onRowClick"
//   >
//     <template #cell-data_attivazione="{ value }">{{ displayDate(value) }}</template>
//     <template #cell-stato="{ data }">
//       <Tag :value="data.stato_descrizione" :severity="statoClienteSeverity(data.stato_codice)" />
//     </template>
//     <template #actions="{ data }">
//       <RowActionsMenu :row="data" :actions="buildActions(data)" />
//     </template>
//   </ListaConfigurabile>
//
// Render slot priorita':
//   1. slot dinamico `cell-{codice}` per la colonna (massima priorita')
//   2. formatter built-in da `formato` (`date_short`, `currency_eur`, ecc.)
//   3. fallback grezzo `data[codice]`
//
// Le colonne con `tipo_colonna='azione'` non hanno field e si renderizzano
// via slot `actions`. L'app cliente passa il proprio RowActionsMenu.

import { computed, ref, onMounted, watch, useSlots } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'
import Button from 'primevue/button'
import { PAGINATION } from '../constants'
import { useListaConfig } from '../composables/useListaConfig'
import { useResponsiveColumns } from '../composables/useResponsiveColumns'
import CellaConfigurabile from './CellaConfigurabile.vue'
import ListaColonneModal from './ListaColonneModal.vue'

// Default paginator allineato al pattern lista standard
// (paginatorPosition=top, JumpToPageDropdown 1/N, font compatto).
// Il caller puo' override passando paginatorProps di useSearchTable o
// un oggetto custom via la prop `paginator-options`. La modalita' lazy +
// removable-sort + striped + scrollable rimane fissata: sono regole del
// pattern, non parametriche (vedi frontend-standards.md).
const _DEFAULT_PAGINATOR_OPTIONS = Object.freeze({
  paginator: true,
  paginatorPosition: 'top',
  paginatorTemplate:
    'FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink ' +
    'RowsPerPageDropdown JumpToPageDropdown CurrentPageReport',
  currentPageReportTemplate: '{currentPage}/{totalPages}',
  rowsPerPageOptions: PAGINATION.ROWS_OPTIONS,
})

const props = defineProps({
  // Codice stabile della lista (es. 'anagrafiche.clienti').
  codice: { type: String, required: true },
  // Dati riga forniti dal caller (no fetch interno).
  rows: { type: Array, default: () => [] },
  // Conteggio totale per paginator (server-side).
  total: { type: Number, default: 0 },
  // Loading flag controllato dal caller.
  loading: { type: Boolean, default: false },
  // Pagina corrente 1-based (display nel paginator).
  page: { type: Number, default: 1 },
  // Field e direction correnti per l'header sortable.
  sortField: { type: String, default: null },
  sortOrder: { type: Number, default: null }, // 1 asc, -1 desc, null
  // Selection mode (vedi PrimeVue DataTable). Default 'single'.
  selectionMode: { type: String, default: 'single' },
  // Data key per riga.
  dataKey: { type: String, default: 'id' },
  // Override prop paginator: tipicamente `paginatorProps` di useSearchTable.
  // Mergiato con i default del pattern (top + jump + 1/N + rowsOptions).
  // Le prop esplicite del caller hanno precedenza sui default.
  paginatorOptions: { type: Object, default: null },
  // Ritiro dinamico colonne (packing a somma via ResizeObserver) per evitare
  // la scrollbar orizzontale quando lo spazio si stringe (es. apertura
  // sidebar). Le colonne ritirate finiscono in una riga di espansione (zero
  // dati persi). Default true: tutte le liste configurabili ne beneficiano
  // (uniformita' UI). La priorita' di ritiro arriva dal catalogo
  // (`ui.lista_colonna.priorita`, esposta da fn_resolve_lista_config).
  responsive: { type: Boolean, default: true },
})

const emit = defineEmits([
  'page',
  'sort',
  'row-click',
  'config-loaded',
])

const { t, te } = useI18n()
const slots = useSlots()

// Stato config (cascata BE) tramite composable per-codice.
const {
  config,
  catalogo,
  dirty,
  loading: configLoading,
  colonneNuove,
  presetAggiornato,
  load,
  ensureCatalogo,
  applyChange,
  save,
  reset,
  ignorePresetUpdate,
} = useListaConfig(props.codice)

// Stato modale di personalizzazione.
const modalVisible = ref(false)

onMounted(async () => {
  const data = await load()
  if (data) emit('config-loaded', data)
})

// Re-fetch se il codice cambia (caso raro: tab switch dinamico).
watch(
  () => props.codice,
  async (newCodice, oldCodice) => {
    if (newCodice && newCodice !== oldCodice) {
      await load()
    }
  },
)

// Colonne renderizzate: dalla config + arricchite del campo_sorgente
// per poter accedere ai dati. Quando il catalogo non e' ancora caricato,
// i metadati estesi (etichetta, formato, ecc.) sono lookup-fallback al
// codice stesso.
const colonneRender = computed(() => {
  const cols = config.value?.colonne ?? []
  const meta = new Map()
  for (const c of catalogo.value?.colonne ?? []) {
    meta.set(c.codice, c)
  }
  return cols
    .filter((c) => c.visibile !== false)
    .map((c) => {
      const m = meta.get(c.codice) || {}
      // Risoluzione header multilingua: se il catalogo dichiara una
      // chiave i18n esistente (`etichetta_i18n_key`), risolviamo via
      // vue-i18n; altrimenti fallback all'`etichetta` letterale del
      // catalogo; ultimo fallback al `codice` (catalogo non ancora
      // caricato — caso teorico oggi che il catalogo e' eager).
      // `te` (translation-exists) evita di mostrare la chiave grezza
      // quando il seed dichiara una key non ancora aggiunta ai locale.
      let header = m.etichetta || c.codice
      if (m.etichetta_i18n_key && te(m.etichetta_i18n_key)) {
        header = t(m.etichetta_i18n_key)
      }
      return {
        codice: c.codice,
        ordine: c.ordine,
        // Peso di ritiro dinamico (packing a somma). Arriva da
        // fn_resolve_lista_config (ui.lista_colonna.priorita). Default 50
        // (mid-pack) coerente col DB se assente.
        priorita: c.priorita ?? 50,
        larghezza: c.larghezza ?? m.larghezza_default ?? null,
        fissata: c.fissata === true,
        esportabile: c.esportabile !== false,
        tipo_colonna: c.tipo_colonna || m.tipo_colonna || 'informazione',
        // Dal catalogo. Se non ancora caricato il fallback al `codice`
        // protegge il primo render; con load-eager non e' piu' raggiungibile.
        etichetta: header,
        campo_sorgente: m.campo_sorgente || c.codice,
        formato: m.formato || null,
        allineamento: m.allineamento || 'left',
        ordinabile: m.ordinabile !== false,
      }
    })
    .sort((a, b) => (a.ordine ?? 0) - (b.ordine ?? 0))
})

// Le colonne tipo 'azione' sono renderizzate separatamente via slot.
// Tutte le altre vanno nelle Column iterabili.
const colonneStandard = computed(() =>
  colonneRender.value.filter((c) => c.tipo_colonna !== 'azione'),
)
// Renderizza la Column "Azioni" solo se la config la dichiara E il caller
// fornisce lo slot — evita celle vuote silenziose se il consumer dimentica
// di passare il template.
const haAzioni = computed(
  () =>
    colonneRender.value.some((c) => c.tipo_colonna === 'azione') &&
    !!slots.actions,
)

// Ritiro dinamico colonne (prop `responsive`). Il composable osserva la
// larghezza reale del contenitore (root della lista) e ritira le colonne a
// priorita' piu' bassa quando la somma delle larghezze supera lo spazio.
const containerRef = ref(null)
const expandedRows = ref({})
const {
  visibleColumns: _responsiveVisible,
  hiddenColumns: _responsiveHidden,
  actionsCompact: _responsiveActionsCompact,
} = useResponsiveColumns(containerRef, colonneStandard, { hasActions: haAzioni })

// Le azioni di riga si comprimono a kebab quando lo spazio si stringe (prima
// leva di recupero, prima di ritirare colonne dati). Passato allo slot
// `actions` come scope `compact` cosi' il caller lo gira a RowActionsMenu.
const actionsCompact = computed(() =>
  props.responsive ? _responsiveActionsCompact.value : false,
)

// Colonne renderizzate come Column dati: tutte (responsive off) o solo le
// visibili dopo il packing.
const colonneVisibili = computed(() =>
  props.responsive ? _responsiveVisible.value : colonneStandard.value,
)
// Colonne ritirate nell'expansion row (solo in modalita' responsive).
const colonneRitirate = computed(() =>
  props.responsive ? _responsiveHidden.value : [],
)

// Niente piu' colonne ritirate (es. sidebar richiusa) -> azzera lo stato
// expansion, altrimenti riallargando le righe gia' aperte riapparirebbero
// espanse (stato fantasma).
watch(
  () => colonneRitirate.value.length,
  (n) => {
    if (n === 0) expandedRows.value = {}
  },
)

// Pagina dimensione effettiva: cascata config BE (preferenza/preset) ->
// fallback PAGINATION.DEFAULT_ROWS. Costante centralizzata in
// core/constants.js: cambiandola li' si aggiorna anche il default qui.
const pageSize = computed(
  () => config.value?.pagina_dimensione ?? PAGINATION.DEFAULT_ROWS,
)
// Offset 0-based per il paginator. Resta a 0 finche' la config non e'
// caricata, cosi' DataTable non "salta" quando arriva pagina_dimensione
// diversa dal default usato dal caller per il primo fetch.
const firstOffset = computed(() =>
  config.value ? (props.page - 1) * pageSize.value : 0,
)

// Eventi DataTable -> il caller decide come gestire (server-side fetch).
// Azzeriamo lo stato expansion su cambio pagina/sort: le chiavi dataKey della
// pagina precedente non hanno senso sulla nuova.
function onPage(event) {
  expandedRows.value = {}
  emit('page', event)
}

function onSort(event) {
  expandedRows.value = {}
  emit('sort', event)
}

function onRowClick(event) {
  // Il click sul toggler dell'expander NON deve propagarsi come row-click
  // (altrimenti il chevron aprirebbe ANCHE il drawer del caller).
  const target = event?.originalEvent?.target
  if (
    target?.closest?.(
      '[data-pc-section="rowtogglebutton"], .p-datatable-row-toggle-button, .p-row-toggler',
    )
  ) {
    return
  }
  emit('row-click', event.data)
}

// Toolbar: apri modale personalizzazione (carica catalogo lazy).
async function openModal() {
  await ensureCatalogo()
  modalVisible.value = true
}

// DEF-2: CTA "Vedi novita'" del banner preset aggiornato → apre la
// modale di personalizzazione. Niente reset del flag qui: il riallineo
// avviene naturalmente al successivo save (lo snapshot si aggiorna a
// `preset.data_update` corrente in `ListaPreferenzaService.upsert`).
async function onSeePresetUpdate() {
  await openModal()
}

// DEF-2: CTA "Ignora" del banner preset aggiornato → POST tombstone +
// reload config (composable). Toast/error handling via useApiHandler.
async function onIgnorePresetUpdate() {
  await ignorePresetUpdate()
}

// Modale -> apply: aggiorna config locale e salva sul server.
async function onApply(payload) {
  applyChange((c) => {
    if (payload.colonne) c.colonne = payload.colonne
  })
  modalVisible.value = false
  await save()
}

async function onReset() {
  modalVisible.value = false
  await reset()
}

// Merge default-pattern + override caller. Lazy/removable-sort/striped/
// scrollable restano fissati in template (non parametrizzabili: regole
// del pattern lista, frontend-standards.md §"Pattern lista").
const effectivePaginatorOptions = computed(() => ({
  ..._DEFAULT_PAGINATOR_OPTIONS,
  ...props.paginatorOptions,
}))

// API esposta al caller. `openModal` permette di trasformare il bottone
// "Personalizza colonne" in un'azione utility del PageActionsBar
// esterno (kebab-compact su touch). `dirty` / `colonneNuove` /
// `presetAggiornato` / `config` per eventuali Tag / Badge che il caller
// mostra nella sua toolbar.
defineExpose({
  config,
  dirty,
  colonneNuove,
  presetAggiornato,
  save,
  reset,
  applyChange,
  openModal,
  ignorePresetUpdate,
})
</script>

<template>
  <div ref="containerRef" class="lista-configurabile">
    <!-- Niente toolbar interna: il caller compone la sua usando
         PageActionsBar standard e integra il bottone "Personalizza" via
         action utility che chiama il metodo `openModal()` esposto da
         questo componente (defineExpose). Tag stato (`dirty`/`config`)
         e badge colonne nuove (`colonneNuove`) sono anch'essi esposti e
         renderizzabili nel suffix della PageActionsBar del caller — su
         touch finiscono nel kebab insieme alle altre azioni. -->

    <!-- DEF-2: banner "preset aggiornato". Visibile solo quando il BE
         segnala che l'admin ha modificato il preset di base dopo lo
         snapshot della preferenza utente (e l'utente non ha ancora
         dismissato). PrimeVue Message severity=info non chiudibile: la
         dismissione esplicita avviene via CTA "Ignora" (tombstone). -->
    <Message
      v-if="presetAggiornato"
      severity="info"
      :closable="false"
      class="lista-preset-aggiornato"
    >
      <div class="lista-preset-aggiornato__row">
        <span class="lista-preset-aggiornato__msg">
          {{ t('lista_config.preset_aggiornato_messaggio') }}
        </span>
        <div class="lista-preset-aggiornato__actions">
          <Button
            severity="info"
            size="small"
            :label="t('lista_config.preset_aggiornato_vedi_novita')"
            icon="pi pi-eye"
            :disabled="configLoading"
            @click="onSeePresetUpdate"
          />
          <Button
            severity="secondary"
            text
            size="small"
            :label="t('lista_config.preset_aggiornato_ignora')"
            :disabled="configLoading"
            @click="onIgnorePresetUpdate"
          />
        </div>
      </div>
    </Message>

    <DataTable
      v-bind="effectivePaginatorOptions"
      :value="rows"
      :loading="loading || configLoading"
      :total-records="total"
      :rows="pageSize"
      :first="firstOffset"
      lazy
      removable-sort
      striped-rows
      scrollable
      scroll-height="flex"
      :class="['app-datatable', { 'app-datatable--responsive': responsive }]"
      :sort-field="sortField"
      :sort-order="sortOrder"
      :selection-mode="selectionMode"
      :data-key="dataKey"
      v-model:expandedRows="expandedRows"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
    >
      <!-- Expander: solo quando il ritiro dinamico ha nascosto colonne.
           Apre la riga di espansione che mostra le colonne ritirate (zero
           dati persi). -->
      <Column
        v-if="colonneRitirate.length > 0"
        expander
        :header="''"
        class="lista-config-expander"
        style="width: 3rem; max-width: 3rem;"
      />

      <Column
        v-for="col in colonneVisibili"
        :key="col.codice"
        :field="col.campo_sorgente"
        :header="col.etichetta"
        :sortable="col.ordinabile"
        :frozen="col.fissata"
        :align-frozen="col.fissata ? 'left' : undefined"
        :exportable="col.esportabile"
        :style="col.larghezza ? `width: ${col.larghezza}px;` : null"
        :body-style="col.allineamento !== 'left' ? `text-align: ${col.allineamento};` : null"
      >
        <template #body="{ data }">
          <CellaConfigurabile
            :col="col"
            :data="data"
            :cell-slot="$slots[`cell-${col.codice}`]"
          />
        </template>
      </Column>

      <Column
        v-if="haAzioni"
        :header="t('common.col_azioni')"
        :exportable="false"
        class="app-col-actions"
      >
        <template #body="{ data }">
          <slot name="actions" :data="data" :compact="actionsCompact" />
        </template>
      </Column>

      <!-- Riga di espansione con le colonne ritirate dinamicamente. Riusa gli
           slot custom `cell-{codice}` del caller (es. Tag stato), cosi' la
           resa e' identica a quella a video. -->
      <template v-if="colonneRitirate.length > 0" #expansion="{ data }">
        <div class="lista-config-expansion">
          <div
            v-for="col in colonneRitirate"
            :key="col.codice"
            class="lista-config-expansion__item"
          >
            <span class="lista-config-expansion__label">{{ col.etichetta }}</span>
            <span class="lista-config-expansion__value">
              <CellaConfigurabile
                :col="col"
                :data="data"
                :cell-slot="$slots[`cell-${col.codice}`]"
              />
            </span>
          </div>
        </div>
      </template>
    </DataTable>

    <ListaColonneModal
      v-model:visible="modalVisible"
      :codice="codice"
      :config="config"
      :catalogo="catalogo"
      :colonne-nuove="colonneNuove"
      :loading="configLoading"
      @apply="onApply"
      @reset="onReset"
    />
  </div>
</template>

<style scoped>
.lista-configurabile {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.lista-preset-aggiornato {
  margin-bottom: 0.5rem;
}

.lista-preset-aggiornato__row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.lista-preset-aggiornato__msg {
  flex: 1 1 auto;
  min-width: 12rem;
}

.lista-preset-aggiornato__actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* Riga di espansione con le colonne ritirate dal packing responsive.
   Griglia label/valore compatta, riusa i colori app. */
.lista-config-expansion {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: 0.35rem 1.25rem;
  padding: 0.5rem 0.75rem 0.75rem;
}

.lista-config-expansion__item {
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
  min-width: 0;
}

.lista-config-expansion__label {
  flex: 0 0 auto;
  font-size: 0.78rem;
  color: var(--app-text-muted);
}

.lista-config-expansion__value {
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--app-table-font-size);
  overflow-wrap: anywhere;
}
</style>
