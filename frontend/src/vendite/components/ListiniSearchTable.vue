<script setup>
// Scopo: DataTable paginata listini con search, filtro utility e attivo.
// Row expansion: mostra le versioni del listino sotto la riga (default aperto).
// Pulsanti riga listino: toggle versioni (chiude/apre expansion), test resolver.
// Mini-tabella versioni nell'expansion: + nuova versione, transizioni stato,
// gestione righe prezzo (apre VersioneDrawer dal parent).
import { ref, onMounted, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useListiniStore } from '../stores/listini'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { lookupCodici } from '../../core/apiCore'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { PRICING_ACTIONS } from '../constants'
import { statoVersioneListinoSeverity, statoVersioneVisibile } from '../../core/utils/severity'
import { displayDate } from '../../core/utils/date'
import { deleteVersione, deleteListino } from '../api/listini'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import AlertScadenzeWidget from './AlertScadenzeWidget.vue'
import AttivaVersioneDialog from './AttivaVersioneDialog.vue'
import ChiudiVersioneDialog from './ChiudiVersioneDialog.vue'

const emit = defineEmits([
  'new',
  'row-click',
  'open-righe',
  'open-nuova-versione',
  'open-clona-versione',
  'test-resolver'
])

const { t } = useI18n()
const store = useListiniStore()
const { execute } = useApiHandler()
const isBlocked = useInjectBlocked()
const { confirmDelete } = useConfirmAction()
// Fase 5.F2: TestResolverDialog e' uno strumento DIAGNOSTICO (sviluppatori
// + admin). Non e' azione operativa: gate rigido su SUPER_ADMIN per non
// confondere gli operatori. Future: estendere a un'azione processo dedicata
// se servono ruoli intermedi (es. "supporto pricing").
const auth = useAuthStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'descrizione'
})

const utilityFilter = ref(null)
const tipologiaFilter = ref(null)

// Lookup tipologie listino per il filtro (non filtrato per utility: lista
// completa delle tipologie attive). Cache globale condivisa: ogni re-mount
// del componente (cambio tab, split-view) riusa la stessa fetch.
const tipologiaLookup = useGlobalLookup(
  'config.listini_tipologie',
  () => lookupCodici('config.listini_tipologie'),
  { immediate: true }
)

const attivoFilter = ref(true)
const attivoOptions = [
  { value: null, label: t('amm.stato_all') },
  { value: true, label: t('amm.stato_attivo') },
  { value: false, label: t('amm.stato_inattivo') }
]

// Stato espansione righe (usato come v-model:expandedRows di PrimeVue).
// Ogni volta che la lista listini viene ricaricata, espandiamo tutte le righe
// e pre-carichiamo le versioni in parallelo.
const expandedRows = ref({})
const allRowsExpanded = computed(() =>
  store.items.length > 0 && store.items.every(it => expandedRows.value[it.id])
)

function onUtilityChange() {
  store.filters.utility_id = utilityFilter.value
  applyFilters()
}

function onTipologiaChange() {
  store.filters.tipologia_id = tipologiaFilter.value
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

function collapseAllRows() {
  expandedRows.value = {}
}

async function toggleAllRows() {
  if (allRowsExpanded.value) {
    collapseAllRows()
    return
  }
  expandAllRows()
  await Promise.all(
    store.items
      .filter(it => !store.versioniByListino[it.id])
      .map(it => store.fetchVersioniListino(it.id))
  )
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

// Stato dialog programma chiusura (PATCH valido_al su ATTIVA)
const chiusuraDialogVisible = ref(false)
const chiusuraDialogVersione = ref(null)
const chiusuraDialogListinoId = ref(null)

function onChiudiVersione(versione, listinoId) {
  chiusuraDialogVersione.value = versione
  chiusuraDialogListinoId.value = listinoId
  chiusuraDialogVisible.value = true
}

async function onChiusuraSaved({ listinoId }) {
  await store.invalidateVersioniListino(listinoId)
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

// O3: elimina un listino mai usato (zero versioni).
// Il pulsante e' visibile solo se versioni_count=0; il guard backend
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

// Scopo: azioni standard della toolbar lista. Il componente PageActionsBar
// decide la resa responsive: primaria visibile, utility inline desktop,
// menu compatto su schermi piccoli.
const pageActions = computed(() => [
  {
    key: 'toggle-all-versioni',
    kind: 'utility',
    label: allRowsExpanded.value
      ? t('listini.comprimi_tutte_versioni')
      : t('listini.espandi_tutte_versioni'),
    icon: MANAGE_ICONS.VERSIONI,
    severity: 'info',
    disabled: store.items.length === 0,
    command: toggleAllRows,
  },
  {
    key: 'test-prezzo',
    kind: 'utility',
    label: t('listini.test_prezzo'),
    icon: 'pi pi-calculator',
    severity: 'info',
    // Strumento diagnostico: oltre al SUPER_ADMIN (bypass) lo apriamo a chi
    // puo' fare override manuale del prezzo (azione `prezzo_override_manuale`).
    // Razionale: chi puo' overridere il prezzo deve poter testare cosa propone
    // il listino prima di decidere — gli operatori "puri" senza override non
    // ne hanno bisogno e il pulsante resta nascosto.
    visible: auth.isSuperAdmin || auth.isActionAllowed(PRICING_ACTIONS.OVERRIDE),
    command: () => emit('test-resolver'),
  },
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
    tooltip: t('listini.nuovo_listino'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

// Scopo: azioni di riga del listino (toggle expansion + elimina conditional).
function buildListinoActions(data) {
  return [
    {
      key: 'toggle-versioni',
      label: expandedRows.value[data.id] ? t('listini.nascondi_versioni') : t('listini.mostra_versioni'),
      icon: MANAGE_ICONS.VERSIONI,
      command: () => toggleExpand(data),
    },
    {
      key: 'elimina-listino',
      label: t('listini.elimina_listino'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: !data.versioni_count,
      command: () => onEliminaListino(data),
    },
  ]
}

// Scopo: azioni di riga della versione listino nell'expansion (fino a 6, filtrate per stato visibile).
//        Lo stato visibile e` data-driven: una versione con valido_al < oggi e` trattata
//        come CHIUSA anche se in DB risulta ancora ATTIVA (job notturno non ancora passato).
function buildVersioneActions(ver, listino) {
  const statoVisibile = statoVersioneVisibile(ver)
  const isBozza = statoVisibile === 'BOZZA'
  const isAttiva = statoVisibile === 'ATTIVA'
  return [
    {
      key: 'attiva',
      label: ver.righe_count ? t('listini.attiva') : t('listini.attiva_no_righe'),
      icon: MANAGE_ICONS.PUBLISH,
      severity: 'primary',
      visible: isBozza,
      disabled: !ver.righe_count,
      command: () => onAttivaVersione(ver, listino.id),
    },
    {
      key: 'chiudi',
      label: t('listini.chiudi'),
      icon: MANAGE_ICONS.CLOSE,
      severity: 'warn',
      visible: isAttiva,
      command: () => onChiudiVersione(ver, listino.id),
    },
    {
      key: 'clona',
      label: t('listini.clona_versione'),
      icon: MANAGE_ICONS.CLONE,
      command: () => emit('open-clona-versione', ver, listino),
    },
    {
      key: 'gestisci-righe',
      label: t('listini.gestisci_righe'),
      icon: MANAGE_ICONS.LIST,
      command: () => emit('open-righe', ver, listino),
    },
    {
      key: 'elimina-versione',
      label: t('listini.elimina_versione'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: isBozza,
      command: () => onEliminaVersione(ver, listino),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.LISTINO)

// Dopo ogni assegnazione di items (fetchList completato e preload versioni
// gia' fatto dal store), aggiorna la mappa expandedRows per espandere tutto.
watch(() => store.items, expandAllRows, { flush: 'post' })

onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('listini.search_placeholder')" style="width: 320px;" />
        <UtilityPerRuoloSelect v-model="utilityFilter"
          :placeholder="t('listini.filtro_utility')" :show-clear="true"
          apply-default
          @change="onUtilityChange" style="width: 200px;" />
        <Select v-model="tipologiaFilter" :options="tipologiaLookup.items.value"
          option-label="descrizione" option-value="id"
          :placeholder="t('listini.filtro_tipologia')" :show-clear="true"
          :loading="tipologiaLookup.loading.value"
          @change="onTipologiaChange" class="app-filter-select" />
        <Select v-model="attivoFilter" :options="attivoOptions" option-label="label" option-value="value"
          :placeholder="t('listini.col_attivo')" @change="onAttivoChange" style="width: 120px;" />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #prefix>
          <AlertScadenzeWidget />
        </template>
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
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
      <Column field="utility_descrizione" :header="t('listini.col_utility')" sortable style="width: 150px;">
        <template #body="{ data }">
          <span>{{ data.utility_descrizione || t('listini.commercio') }}</span>
        </template>
      </Column>
      <Column field="tipologia_descrizione" :header="t('listini.col_tipologia')" sortable style="width: 150px;">
        <template #body="{ data }">
          <span>{{ data.tipologia_descrizione || '—' }}</span>
        </template>
      </Column>
      <Column field="versioni_count" :header="t('listini.col_versioni')" style="width: 80px;" />
      <Column field="attivo" :header="t('listini.col_attivo')" style="width: 80px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />
        </template>
      </Column>
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false" frozen alignFrozen="right">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildListinoActions(data)" />
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
            <Button :icon="MANAGE_ICONS.ADD" :label="t('listini.nuova_versione')"
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
            <Column field="codice_versione" :header="t('listini.col_codice_versione')" style="width: 140px;" />
            <Column :header="t('listini.field_valido_dal')" style="width: 110px;">
              <template #body="{ data: ver }">{{ displayDate(ver.valido_dal) }}</template>
            </Column>
            <Column :header="t('listini.field_valido_al')" style="width: 110px;">
              <template #body="{ data: ver }">{{ displayDate(ver.valido_al) || '—' }}</template>
            </Column>
            <Column field="righe_count" :header="t('listini.col_righe')" style="width: 80px;" />
            <Column :header="t('listini.col_stato')" style="width: 90px;">
              <template #body="{ data: ver }">
                <Tag :value="statoVersioneVisibile(ver)" :severity="statoVersioneListinoSeverity(statoVersioneVisibile(ver))" />
              </template>
            </Column>
            <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false" frozen alignFrozen="right">
              <template #body="{ data: ver }">
                <RowActionsMenu :row="ver" :actions="buildVersioneActions(ver, listino)" />
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

    <ChiudiVersioneDialog
      :visible="chiusuraDialogVisible"
      @update:visible="v => chiusuraDialogVisible = v"
      :listino-id="chiusuraDialogListinoId"
      :versione="chiusuraDialogVersione"
      @saved="onChiusuraSaved"
    />
    </template>
  </div>
</template>
