<script setup>
// Scopo: DataTable paginata preventivi vendita con search, filtri stato/data, empty state.
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreventiviStore } from '../stores/preventivi'
import { useSearchTable } from '../../../core/composables/useSearchTable'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { statoPreventiveSeverity } from '../../../core/utils/severity'
import { displayDate, toDateString } from '../../../core/utils/date'
import { formatCurrency } from '../../../core/utils/format'
import { DATE_FORMAT, MANAGE_ICONS, TAB_ENTITIES } from '../../../core/constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import SearchHint from '../../../core/components/SearchHint.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import PdfDocumentiSorgenteDialog from '../../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = usePreventiviStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'data',
  defaultSortOrder: 'desc'
})

// --- Filtri ---
const statoFilter = ref(null)
const dataDaFilter = ref(store.filters.data_da ? new Date(store.filters.data_da + 'T00:00:00') : null)
const dataAlFilter = ref(null)
// Toggle "mostra storico revisioni": negazione del filtro store
// (mostraStorico=ON ⇔ solo_attiva=false). computed get/set per
// restare allineato al filtro reale anche se cambia altrove (reset, logout,
// ripristino sessione): single source of truth = store.
const mostraStorico = computed({
  get: () => !store.filters.solo_attiva,
  set: (val) => { store.filters.solo_attiva = !val },
})
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
    tooltip: t('preventivi.nuovo_preventivo'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

function onStatoChange() {
  store.filters.stato = statoFilter.value
  applyFilters()
}

function onDataDaChange() {
  store.filters.data_da = dataDaFilter.value ? toDateString(dataDaFilter.value) : null
  applyFilters()
}

function onDataAlChange() {
  store.filters.data_a = dataAlFilter.value ? toDateString(dataAlFilter.value) : null
  applyFilters()
}

// Il setter del computed scrive gia' lo store; qui basta triggerare la fetch.
function onMostraStoricoChange() {
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

// ── PDF dialog (azione di riga) ──
// Apertura di un dialog popup con la lista PDF generati per il preventivo.
// Il pulsante e' disabilitato in stato DRAFT (nessun PDF persistito).
// Click `@click.stop` per non triggerare il row-click che apre il drawer.
const pdfDialogVisible = ref(false)
const pdfDialogPreventivo = ref(null)

function onPdfClick(row) {
  if (!row || row.stato_codice_interno === 'DRAFT') return
  pdfDialogPreventivo.value = row
  pdfDialogVisible.value = true
}

useTabFreshness(store, TAB_ENTITIES.PREVENTIVO)

// Lista preventivi: ha filtro data_da con default anno-1 (frontend-standards
// "Filtro data standard"), quindi auto-load al mount. Lo store guard
// hasFilters considera data_da come filtro attivo: non rischiamo di tirar
// giu' "tutti i preventivi senza limiti" perche' il default e' di per se'
// un filtro temporale.
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('preventivi.search_placeholder')" style="width: 260px;" />
        <LookupSelect v-model="statoFilter" rel="config.stati_doc_preventivi" value-field="codice_interno"
          :placeholder="t('preventivi.filtro_stato')" show-clear @change="onStatoChange" style="width: 160px;" />
        <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
          :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
          @date-select="onDataDaChange" @clear-click="onDataDaChange" />
        <DatePicker v-model="dataAlFilter" :placeholder="t('common.data_a')"
          :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
          @date-select="onDataAlChange" @clear-click="onDataAlChange" />
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <ToggleSwitch v-model="mostraStorico" inputId="prev-mostra-storico"
            @change="onMostraStoricoChange" />
          <label for="prev-mostra-storico" style="font-size: 0.85rem; cursor: pointer;">
            {{ t('preventivi.filtro_mostra_storico') }}
          </label>
        </div>
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <SearchHint v-if="!store.hasSearched && !store.loading" />

    <DataTable
      v-show="store.hasSearched || store.loading"
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy removable-sort striped-rows scrollable scrollHeight="flex"
      class="app-datatable"
      @page="onPage" @sort="onSort" @row-click="onRowClick"
      selection-mode="single" data-key="id"
    >
      <Column field="numero" :header="t('preventivi.col_numero')" sortable style="width: 130px;" />
      <Column field="rev" :header="t('preventivi.col_rev')" style="width: 60px;" />
      <Column field="data" :header="t('preventivi.col_data')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data) }}</template>
      </Column>
      <Column field="cliente_denominazione" :header="t('preventivi.col_cliente')" sortable style="min-width: 180px;" />
      <Column field="billing_account_codice" :header="t('preventivi.col_ba')" sortable style="width: 120px;" />
      <Column field="id_fiscale" :header="t('preventivi.col_id_fiscale')" style="width: 140px;" />
      <Column field="utility_descrizione" :header="t('preventivi.col_utility')" sortable style="width: 110px;" />
      <Column field="istanza_utility_codice" :header="t('preventivi.col_istanza')" sortable style="width: 130px;" />
      <Column field="totale_documento" :header="t('preventivi.col_totale')" style="width: 130px;">
        <template #body="{ data }">{{ formatCurrency(data.totale_documento) }}</template>
      </Column>
      <Column field="validita_al" :header="t('preventivi.col_validita')" style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.validita_al) }}</template>
      </Column>
      <Column field="stato_codice_interno" :header="t('preventivi.col_stato')" sortable style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione"
            :severity="statoPreventiveSeverity(data.stato_codice_interno)" />
        </template>
      </Column>
      <Column :header="''" class="app-col-actions" style="width: 60px;">
        <template #body="{ data }">
          <!-- Azione PDF: disabilitata in DRAFT (nessun PDF persistito).
               click.stop per non innescare il row-click che apre il drawer. -->
          <Button
            icon="pi pi-file-pdf"
            text
            rounded
            size="small"
            class="app-pdf-btn"
            :disabled="data.stato_codice_interno === 'DRAFT'"
            v-tooltip.top="data.stato_codice_interno === 'DRAFT'
              ? t('preventivi.pdf.tooltip_lista_disabilitato')
              : t('preventivi.pdf.tooltip_lista')"
            @click.stop="onPdfClick(data)"
          />
        </template>
      </Column>
    </DataTable>

    <!-- Dialog lista PDF per il preventivo selezionato. Riusa il
         building block `PdfDocumentiSorgenteDialog` che incapsula
         `DocumentiGeneratiSorgenteList` (stesso usato dal drawer). -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialogVisible"
      sorgente-code="PREVENTIVO"
      :sorgente-id="pdfDialogPreventivo?.id ?? null"
      :title="pdfDialogPreventivo
        ? t('preventivi.pdf.dialog_title', {
            numero: pdfDialogPreventivo.numero,
          })
        : ''"
    />
    </template>
  </div>
</template>
