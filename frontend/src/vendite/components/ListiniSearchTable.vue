<script setup>
// Scopo: DataTable paginata listini con search, filtro dominio e attivo.
// Row expansion: mostra le versioni del listino sotto la riga (default aperto).
// Pulsanti riga listino: toggle versioni (chiude/apre expansion), associazioni.
// Mini-tabella versioni nell'expansion: + nuova versione, transizioni stato,
// gestione righe prezzo (apre VersioneDrawer dal parent).
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useListiniStore } from '../stores/listini'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { MANAGE_ICONS } from '../../core/constants'
import { dominioListinoSeverity, statoVersioneListinoSeverity } from '../../core/utils/severity'
import { displayDate } from '../../core/utils/date'
import { changeVersioneStato, deleteVersione, deleteListino } from '../api/listini'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'
import AttivaVersioneDialog from './AttivaVersioneDialog.vue'

const emit = defineEmits([
  'new',
  'row-click',
  'open-associazioni',
  'open-righe',
  'open-nuova-versione',
  'open-clona-versione',
  'test-resolver'
])

const { t } = useI18n()
const store = useListiniStore()
const { execute } = useApiHandler()
const { confirmDelete } = useConfirmAction()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'descrizione'
})

const dominioFilter = ref(null)
const dominioOptions = [
  { value: null, label: t('common.all') },
  { value: 'UTILITY', label: t('listini.dominio_utility') },
  { value: 'COMMERCIO', label: t('listini.dominio_commercio') }
]

const attivoFilter = ref(true)
const boolOptions = [
  { value: null, label: t('common.all') },
  { value: true, label: t('common.yes') },
  { value: false, label: t('common.no') }
]

// Stato espansione righe (usato come v-model:expandedRows di PrimeVue).
// Ogni volta che la lista listini viene ricaricata, espandiamo tutte le righe
// e pre-carichiamo le versioni in parallelo.
const expandedRows = ref({})

function onDominioChange() {
  store.filters.dominio = dominioFilter.value
  applyFilters()
}

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

// Espande tutte le righe correntemente in lista. Il preload delle versioni
// viene gia' fatto dallo store dentro fetchList; qui ci limitiamo a mappare
// gli id correnti come "espansi" per il v-model:expandedRows di PrimeVue.
function expandAllRows() {
  const map = {}
  store.items.forEach(it => { map[it.id] = true })
  expandedRows.value = map
}

// Toggle expansion di una singola riga (usato dal pulsante "versioni" della riga).
// Il fetch lazy serve per i casi in cui il preload del store e' fallito o
// quando l'utente collassa-riapre senza cambiare pagina.
async function toggleExpand(listino) {
  const next = { ...expandedRows.value }
  if (next[listino.id]) {
    delete next[listino.id]
    expandedRows.value = next
  } else {
    next[listino.id] = true
    expandedRows.value = next
    if (!store.versioniByListino[listino.id]) {
      await store.fetchVersioniListino(listino.id)
    }
  }
}

// Stato dialog conferma attivazione (D3) — dichiarato prima delle funzioni
// che lo referenziano per evitare TDZ in caso di chiamata sincrona durante setup.
const attivaDialogVisible = ref(false)
const attivaDialogVersione = ref(null)
const attivaDialogListinoId = ref(null)

// Transizione ATTIVA -> CHIUSA: nessun auto-close, esegue diretto.
async function onChiudiVersione(versione, listinoId) {
  const result = await execute(
    () => changeVersioneStato(listinoId, versione.id, { stato: 'CHIUSA' }),
    { successMessage: t('listini.stato_aggiornato') }
  )
  if (result !== null) {
    await store.invalidateVersioniListino(listinoId)
  }
}

// Transizione BOZZA -> ATTIVA: passa per dialog di conferma con preview
// auto-close (D3). Il dialog chiama dry_run prima della conferma reale.
function onAttivaVersione(versione, listinoId) {
  attivaDialogVersione.value = versione
  attivaDialogListinoId.value = listinoId
  attivaDialogVisible.value = true
}

async function onAttivaConfirmed({ listinoId }) {
  await store.invalidateVersioniListino(listinoId)
}

// O2: elimina una versione in stato BOZZA con conferma utente.
function onEliminaVersione(versione, listino) {
  confirmDelete(versione.codice_versione, async () => {
    const result = await execute(
      () => deleteVersione(listino.id, versione.id),
      { successMessage: t('listini.versione_eliminata') },
    )
    if (result !== null) {
      await store.invalidateVersioniListino(listino.id)
      await store.fetchList()
    }
  })
}

// O3: elimina un listino mai usato (zero versioni, zero associazioni).
// Il pulsante e' visibile solo se entrambi i counts sono 0; il guard backend
// e' la fonte di verita' (un check FE serve solo a ridurre i click sbagliati).
function onEliminaListino(listino) {
  confirmDelete(listino.codice, async () => {
    const result = await execute(
      () => deleteListino(listino.id),
      { successMessage: t('listini.listino_eliminato') },
    )
    if (result !== null) {
      await store.fetchList()
    }
  })
}

useTabFreshness(store, 'listino')

// Dopo ogni assegnazione di items (fetchList completato e preload versioni
// gia' fatto dal store), aggiorna la mappa expandedRows per espandere tutto.
watch(() => store.items, expandAllRows, { flush: 'post' })

onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('listini.search_placeholder')" />
        <Select v-model="dominioFilter" :options="dominioOptions" option-label="label" option-value="value"
          :placeholder="t('listini.filtro_dominio')" @change="onDominioChange" style="width: 150px;" />
        <Select v-model="attivoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" style="width: 120px;" />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-calculator" text severity="info"
          v-tooltip.bottom="t('listini.test_prezzo')" @click="emit('test-resolver')" />
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('listini.nuovo_listino')" @click="emit('new')" />
      </div>
    </div>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      v-model:expandedRows="expandedRows"
      v-bind="paginatorProps"
      lazy removable-sort striped-rows scrollable scrollHeight="flex"
      class="app-datatable"
      @page="onPage" @sort="onSort" @row-click="onRowClick"
      selection-mode="single" data-key="id"
    >
      <Column field="codice" :header="t('listini.col_codice')" sortable style="width: 140px;" />
      <Column field="descrizione" :header="t('listini.col_descrizione')" sortable style="min-width: 200px;" />
      <Column field="dominio" :header="t('listini.col_dominio')" sortable style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.dominio" :severity="dominioListinoSeverity(data.dominio)" />
        </template>
      </Column>
      <Column field="versioni_count" :header="t('listini.col_versioni')" style="width: 80px;" />
      <Column field="associazioni_count" :header="t('listini.col_associazioni')" style="width: 90px;" />
      <Column field="attivo" :header="t('listini.col_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
      <Column :header="t('listini.col_gestione')" style="width: 130px;" frozen alignFrozen="right">
        <template #body="{ data }">
          <div class="flex gap-1" @click.stop>
            <Button :icon="MANAGE_ICONS.VERSIONI" text rounded size="small"
              class="app-manage-btn"
              v-tooltip.bottom="expandedRows[data.id] ? t('listini.nascondi_versioni') : t('listini.mostra_versioni')"
              @click="toggleExpand(data)" />
            <Button :icon="MANAGE_ICONS.ASSOCIAZIONI" text rounded size="small"
              class="app-manage-btn" v-tooltip.bottom="t('listini.tab_associazioni')"
              @click="emit('open-associazioni', data)" />
            <Button v-if="!data.versioni_count && !data.associazioni_count"
              icon="pi pi-trash" text rounded size="small" class="app-delete-btn"
              v-tooltip.bottom="t('listini.elimina_listino')"
              @click="onEliminaListino(data)" />
          </div>
        </template>
      </Column>

      <template #expansion="{ data: listino }">
        <div class="app-row-expansion">
          <div class="app-row-expansion__header">
            <span class="app-row-expansion__title">
              <i class="pi pi-arrow-turn-down-right"></i>
              <i :class="MANAGE_ICONS.VERSIONI"></i>
              {{ t('listini.tab_versioni') }} ({{ store.versioniByListino[listino.id]?.length ?? 0 }})
            </span>
            <Button icon="pi pi-plus" :label="t('listini.nuova_versione')"
              text size="small" class="app-action-btn"
              @click.stop="emit('open-nuova-versione', listino)" />
          </div>

          <div v-if="!store.versioniByListino[listino.id]" class="app-loading">
            <i class="pi pi-spin pi-spinner" />
          </div>
          <div v-else-if="store.versioniByListino[listino.id].length === 0" class="app-empty-state">
            <i class="pi pi-history" />
            <p>{{ t('listini.nessuna_versione_inline') }}</p>
          </div>
          <DataTable v-else
            :value="store.versioniByListino[listino.id]"
            class="app-datatable app-datatable--inner"
            striped-rows data-key="id"
          >
            <Column :header="t('listini.col_stato')" style="width: 90px;">
              <template #body="{ data: ver }">
                <Tag :value="ver.stato" :severity="statoVersioneListinoSeverity(ver.stato)" />
              </template>
            </Column>
            <Column field="codice_versione" :header="t('listini.col_codice_versione')" style="width: 140px;" />
            <Column :header="t('listini.field_valido_dal')" style="width: 110px;">
              <template #body="{ data: ver }">{{ displayDate(ver.valido_dal) }}</template>
            </Column>
            <Column :header="t('listini.field_valido_al')" style="width: 110px;">
              <template #body="{ data: ver }">{{ displayDate(ver.valido_al) || '—' }}</template>
            </Column>
            <Column field="righe_count" :header="t('listini.col_righe')" style="width: 80px;" />
            <Column :header="t('listini.col_gestione')" style="width: 140px;" frozen alignFrozen="right">
              <template #body="{ data: ver }">
                <div class="flex gap-1" @click.stop>
                  <Button v-if="ver.stato === 'BOZZA'" icon="pi pi-check-circle"
                    text rounded size="small" class="app-action-btn"
                    v-tooltip.bottom="t('listini.attiva')"
                    @click="onAttivaVersione(ver, listino.id)" />
                  <Button v-if="ver.stato === 'ATTIVA'" icon="pi pi-lock"
                    text rounded size="small" severity="warn"
                    v-tooltip.bottom="t('listini.chiudi')"
                    @click="onChiudiVersione(ver, listino.id)" />
                  <Button icon="pi pi-copy" text rounded size="small"
                    class="app-manage-btn"
                    v-tooltip.bottom="t('listini.clona_versione')"
                    @click="emit('open-clona-versione', ver, listino)" />
                  <Button icon="pi pi-list" text rounded size="small"
                    class="app-manage-btn"
                    v-tooltip.bottom="t('listini.gestisci_righe')"
                    @click="emit('open-righe', ver, listino)" />
                  <Button v-if="ver.stato === 'BOZZA'" icon="pi pi-trash"
                    text rounded size="small" class="app-delete-btn"
                    v-tooltip.bottom="t('listini.elimina_versione')"
                    @click="onEliminaVersione(ver, listino)" />
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
      </template>
    </DataTable>

    <AttivaVersioneDialog
      :visible="attivaDialogVisible"
      @update:visible="v => attivaDialogVisible = v"
      :listino-id="attivaDialogListinoId"
      :versione="attivaDialogVersione"
      @confirmed="onAttivaConfirmed"
    />
  </div>
</template>

