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
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { PAGINATION } from '../constants'
import { useListaConfig } from '../composables/useListaConfig'
import { displayDate, displayTimestamp } from '../utils/date'
import { formatCurrency, formatNumber } from '../utils/format'
import ListaColonneModal from './ListaColonneModal.vue'

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
})

const emit = defineEmits([
  'page',
  'sort',
  'row-click',
  'config-loaded',
])

const { t } = useI18n()
const slots = useSlots()

// Stato config (cascata BE) tramite composable per-codice.
const {
  config,
  catalogo,
  dirty,
  loading: configLoading,
  colonneNuove,
  load,
  ensureCatalogo,
  applyChange,
  save,
  reset,
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
      return {
        codice: c.codice,
        ordine: c.ordine,
        larghezza: c.larghezza ?? m.larghezza_default ?? null,
        fissata: c.fissata === true,
        esportabile: c.esportabile !== false,
        tipo_colonna: c.tipo_colonna || m.tipo_colonna || 'informazione',
        // Dal catalogo (potrebbe non essere caricato al primo render).
        etichetta: m.etichetta || c.codice,
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

// Scopo: Formatter built-in da `formato`. Il caller puo' sovrascrivere
//        completamente via slot dinamico cell-{codice}.
function defaultFormat(value, formato) {
  if (value == null) return ''
  switch (formato) {
    case 'date_short':
      return displayDate(value)
    case 'datetime':
      return displayTimestamp(value)
    case 'currency_eur':
      return formatCurrency(value)
    case 'number':
      return formatNumber(value)
    case 'percent_2':
      return formatNumber(value, { minimumFractionDigits: 2 }) + ' %'
    case 'yesno':
      return value ? t('common.yes') : t('common.no')
    default:
      return String(value)
  }
}

// Eventi DataTable -> il caller decide come gestire (server-side fetch).
function onPage(event) {
  emit('page', event)
}

function onSort(event) {
  emit('sort', event)
}

function onRowClick(event) {
  emit('row-click', event.data)
}

// Toolbar: apri modale personalizzazione (carica catalogo lazy).
async function openModal() {
  await ensureCatalogo()
  modalVisible.value = true
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

// Esposto al caller per eventuale bottone export custom.
defineExpose({ config, dirty, save, reset, applyChange })
</script>

<template>
  <div class="lista-configurabile">
    <div class="lista-toolbar">
      <div class="lista-toolbar-left">
        <slot name="filters" />
      </div>
      <div class="lista-toolbar-right">
        <Tag
          v-if="dirty"
          :value="t('lista_config.stato_temporanea')"
          severity="warning"
          v-tooltip.bottom="t('lista_config.stato_temporanea_tooltip')"
        />
        <Tag
          v-else-if="config"
          :value="t('lista_config.stato_salvata')"
          severity="success"
        />
        <Button
          icon="pi pi-cog"
          text
          rounded
          :badge="colonneNuove > 0 ? String(colonneNuove) : null"
          badge-severity="info"
          v-tooltip.bottom="t('lista_config.personalizza_colonne')"
          @click="openModal"
        />
        <slot name="actions-extra" />
      </div>
    </div>

    <DataTable
      :value="rows"
      :loading="loading || configLoading"
      :total-records="total"
      :rows="pageSize"
      :first="firstOffset"
      paginator
      lazy
      removable-sort
      striped-rows
      scrollable
      scroll-height="flex"
      class="app-datatable"
      :sort-field="sortField"
      :sort-order="sortOrder"
      :selection-mode="selectionMode"
      :data-key="dataKey"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
    >
      <Column
        v-for="col in colonneStandard"
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
          <slot
            :name="`cell-${col.codice}`"
            :data="data"
            :value="data[col.campo_sorgente]"
            :col="col"
          >
            {{ defaultFormat(data[col.campo_sorgente], col.formato) }}
          </slot>
        </template>
      </Column>

      <Column
        v-if="haAzioni"
        :header="t('common.col_azioni')"
        :exportable="false"
        class="app-col-actions"
      >
        <template #body="{ data }">
          <slot name="actions" :data="data" />
        </template>
      </Column>
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
  gap: 0.5rem;
}
.lista-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.25rem 0;
}
.lista-toolbar-left,
.lista-toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
</style>
