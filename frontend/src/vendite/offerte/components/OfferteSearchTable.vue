<script setup>
// Scopo: DataTable paginata offerte commerciali con search, filtri
//        stato/utility/data, empty state. Click riga = apre drawer in edit.
//        Pattern allineato a PreventiviList (frontend-standards "Pattern lista").
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'

import AccessoBloccatoPanel from '../../../core/components/AccessoBloccatoPanel.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import PageActionsBar from '../../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../../core/components/RowActionsMenu.vue'
import SearchHint from '../../../core/components/SearchHint.vue'
import UtilityPerRuoloSelect from '../../../core/components/UtilityPerRuoloSelect.vue'
import PdfDocumentiSorgenteDialog from '../../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import OffertaNoteDrawer from './OffertaNoteDrawer.vue'
import { useInjectBlocked } from '../../../core/composables/useReadonlyMode'
import { useSearchTable } from '../../../core/composables/useSearchTable'
import { useTabFreshness } from '../../../core/composables/useTabFreshness'
import { DATE_FORMAT, MANAGE_ICONS, TAB_ENTITIES, TIPO_RUOLO } from '../../../core/constants'
import { displayDate, toDateString } from '../../../core/utils/date'
import { statoOffertaSeverity } from '../../../core/utils/severity'
import { STATI_OFFERTA_SEGNALA_SCADENZA } from '../constants'
import { useOfferteStore } from '../stores/offerte'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useOfferteStore()
const isBlocked = useInjectBlocked()
// `defaultSortField` DEVE corrispondere a un `<Column field="X" sortable>`
// visibile nel template: PrimeVue mostra l'indicatore di sort solo su una
// colonna esistente; se punta a un field "fantasma" il render produce
// artefatti grafici (es. underline doppia sotto le label). Sort default
// per UX: `validita_dal` discendente (offerte con inizio validita' piu'
// recente in cima). Coerente col `store.filters.order_by` di default.
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'validita_dal',
  defaultSortOrder: 'desc',
})

// --- Filtri ---
const statoFilter = ref(store.filters.stato_codice_interno ?? null)
const utilityFilter = ref(store.filters.utility_id ?? null)
const dataDaFilter = ref(
  store.filters.data_da ? new Date(`${store.filters.data_da}T00:00:00`) : null,
)
const dataAlFilter = ref(
  store.filters.data_a ? new Date(`${store.filters.data_a}T00:00:00`) : null,
)
// Toggle "mostra storico revisioni" (negazione del filtro store).
// mostraStorico=ON ⇔ solo_attiva=false. computed get/set per restare
// allineato al filtro reale anche se cambia altrove (reset, logout,
// ripristino sessione): single source of truth = store. Pattern speculare
// a PreventiviList.vue.
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
    tooltip: t('vendite.offerte.nuova_offerta'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

function onStatoChange() {
  store.filters.stato_codice_interno = statoFilter.value
  applyFilters()
}

function onUtilityChange() {
  store.filters.utility_id = utilityFilter.value
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

function onRowClick(event) {
  emit('row-click', event.data)
}

// --- Azioni di riga (PDF + Note) — pattern allineato a contratti/preventivi ---
// `@click.stop` implicito tramite RowActionsMenu (kebab) per non triggerare
// il row-click che apre il drawer.
const pdfDialogVisible = ref(false)
const pdfDialogOfferta = ref(null)
const noteDrawerVisible = ref(false)
const noteDrawerOfferta = ref(null)

function onPdfClick(row) {
  // Documenti PDF disponibili solo dopo l'emissione (la fn DB
  // `genera_documento` richiede l'offerta EMESSA con versione listino
  // fissata). In BOZZA l'azione è disabled (vedi tooltip_lista_disabilitato).
  if (!row || row.stato_codice_interno === 'BOZZA') return
  pdfDialogOfferta.value = row
  pdfDialogVisible.value = true
}

function onNoteClick(row) {
  if (!row?.id) return
  noteDrawerOfferta.value = row
  noteDrawerVisible.value = true
}

// Scopo: costruisce le azioni contestuali di riga per il menu kebab.
// Modifica = click riga. Pattern simmetrico a contratti/preventivi.
function buildRowActions(data) {
  return [
    {
      key: 'documenti-pdf',
      label: t('vendite.offerte.pdf.label_scarica'),
      icon: MANAGE_ICONS.PDF,
      severity: 'primary',
      disabled: data.stato_codice_interno === 'BOZZA',
      tooltip: data.stato_codice_interno === 'BOZZA'
        ? t('vendite.offerte.pdf.tooltip_lista_disabilitato')
        : t('vendite.offerte.pdf.tooltip_lista'),
      command: () => onPdfClick(data),
    },
    {
      key: 'gestisci-note',
      label: t('vendite.offerte.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => onNoteClick(data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.OFFERTA_COMMERCIALE)

// Lista con filtro data_da default anno-1 (frontend-standards "Filtro data
// standard"): auto-load al mount, lo store guard hasFilters considera
// data_da come filtro attivo.
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText
            v-model="searchText"
            :placeholder="t('vendite.offerte.search_placeholder')"
            style="width: 260px;"
          />
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_offerte"
            value-field="codice_interno"
            :placeholder="t('vendite.offerte.filtro_stato')"
            show-clear
            style="width: 160px;"
            @change="onStatoChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.offerte.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <DatePicker
            v-model="dataDaFilter"
            :placeholder="t('common.data_da')"
            :date-format="DATE_FORMAT"
            show-icon
            show-button-bar
            style="width: 150px;"
            @date-select="onDataDaChange"
            @clear-click="onDataDaChange"
          />
          <DatePicker
            v-model="dataAlFilter"
            :placeholder="t('common.data_a')"
            :date-format="DATE_FORMAT"
            show-icon
            show-button-bar
            style="width: 150px;"
            @date-select="onDataAlChange"
            @clear-click="onDataAlChange"
          />
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <ToggleSwitch v-model="mostraStorico" inputId="off-mostra-storico"
              @change="onMostraStoricoChange" />
            <label for="off-mostra-storico" style="font-size: 0.85rem; cursor: pointer;">
              {{ t('vendite.offerte.filtro_mostra_storico') }}
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
        lazy
        removable-sort
        striped-rows
        scrollable
        scroll-height="flex"
        class="app-datatable"
        selection-mode="single"
        data-key="id"
        @page="onPage"
        @sort="onSort"
        @row-click="onRowClick"
      >
        <Column
          field="codice"
          :header="t('vendite.offerte.col_codice')"
          sortable
          style="width: 130px;"
        />
        <Column
          field="revisione_numero"
          :header="t('vendite.offerte.col_revisione')"
          style="width: 60px;"
        />
        <Column
          field="billing_account_display"
          :header="t('vendite.offerte.col_cliente')"
          sortable
          style="min-width: 180px;"
        />
        <Column
          field="ba_codice"
          :header="t('vendite.offerte.col_ba_codice')"
          sortable
          style="width: 120px;"
        />
        <Column
          field="id_fiscale"
          :header="t('vendite.offerte.col_id_fiscale')"
          style="width: 140px;"
        />
        <Column
          field="utility_display"
          :header="t('vendite.offerte.col_utility')"
          sortable
          style="width: 130px;"
        />
        <Column
          field="listino_codice"
          :header="t('vendite.offerte.col_listino')"
          style="width: 140px;"
        >
          <template #body="{ data }">
            {{ data.listino_codice }}
            <span v-if="data.listino_versione_codice" style="color: var(--app-text-muted);">
              · v{{ data.listino_versione_codice }}
            </span>
          </template>
        </Column>
        <Column
          field="validita_dal"
          :header="t('vendite.offerte.col_validita_dal')"
          sortable
          style="width: 110px;"
        >
          <template #body="{ data }">{{ displayDate(data.validita_dal) }}</template>
        </Column>
        <Column
          field="validita_al"
          :header="t('vendite.offerte.col_validita_al')"
          style="width: 110px;"
        >
          <template #body="{ data }">{{ displayDate(data.validita_al) }}</template>
        </Column>
        <Column
          field="data_emissione"
          :header="t('vendite.offerte.col_emissione')"
          sortable
          style="width: 110px;"
        >
          <template #body="{ data }">{{ displayDate(data.data_emissione) }}</template>
        </Column>
        <Column
          field="stato_codice_interno"
          :header="t('vendite.offerte.col_stato')"
          sortable
          style="width: 130px;"
        >
          <template #body="{ data }">
            <Tag
              :value="data.stato_descrizione"
              :severity="statoOffertaSeverity(data.stato_codice_interno)"
            />
            <Tag
              v-if="data.is_scaduta && STATI_OFFERTA_SEGNALA_SCADENZA.includes(data.stato_codice_interno)"
              :value="t('vendite.offerte.badge_scaduta')"
              severity="warn"
              style="margin-left: 0.25rem;"
            />
          </template>
        </Column>
        <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
          <template #body="{ data }">
            <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
          </template>
        </Column>
      </DataTable>

      <!-- Dialog lista PDF per l'offerta selezionata. Riusa il building
           block `PdfDocumentiSorgenteDialog` che incapsula
           `DocumentiGeneratiSorgenteList` (stesso BB usato dal drawer). -->
      <PdfDocumentiSorgenteDialog
        v-model:visible="pdfDialogVisible"
        sorgente-code="OFFERTA_COMMERCIALE"
        :sorgente-id="pdfDialogOfferta?.id ?? null"
        :title="pdfDialogOfferta
          ? t('vendite.offerte.pdf.dialog_title', {
              codice: pdfDialogOfferta.codice,
            })
          : ''"
      />

      <!-- Drawer note offerta: wrapper thin sul BB `NoteDrawer`. Da lista
           le eccezioni non sono pre-caricate (vivono nel detail); il
           select RIGA del NoteDrawer si popola con array vuoto, l'operatore
           può comunque inserire note di testata. Per note di riga è
           preferibile aprire il drawer dal detail offerta. -->
      <OffertaNoteDrawer
        v-if="noteDrawerOfferta?.id"
        v-model:visible="noteDrawerVisible"
        :offerta-id="noteDrawerOfferta.id"
      />
    </template>
  </div>
</template>
