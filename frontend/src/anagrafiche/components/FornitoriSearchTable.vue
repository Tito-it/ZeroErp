<script setup>
// Scopo: DataTable paginata fornitori con search, filtro stato e attivo.
// Riusabile da: FornitoriView, futuro ricerca fornitori in altri domini.
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFornitoriStore } from '../stores/fornitori'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { displayDate } from '../../core/utils/date'
import { statoFornitoreSeverity } from '../../core/utils/severity'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import SearchHint from '../../core/components/SearchHint.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'

const emit = defineEmits(['new', 'row-click', 'contatti', 'indirizzi', 'conti-bancari'])
const { t } = useI18n()
const store = useFornitoriStore()
const auth = useAuthStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'ragione_sociale_completa'
})

const statoFilter = ref(null)
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
    tooltip: t('fornitori.nuovo_fornitore'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])
function onStatoChange() {
  store.filters.stato_fornitore_id = statoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

// Scopo: azioni di riga del fornitore (sub-drawer anagrafici).
function buildRowActions(data) {
  const contiBlocked = auth.isObjectBlocked('anagrafiche', 'conto_bancario')
  return [
    {
      key: 'contatti',
      label: t('contatto.gestisci_contatti'),
      icon: MANAGE_ICONS.CONTATTI,
      command: () => emit('contatti', data),
    },
    {
      key: 'indirizzi',
      label: t('indirizzo_soggetto.gestisci_indirizzi'),
      icon: MANAGE_ICONS.INDIRIZZI,
      command: () => emit('indirizzi', data),
    },
    {
      key: 'conti-bancari',
      label: t('conti_bancari.gestisci_conti'),
      icon: MANAGE_ICONS.CONTI_BANCARI,
      disabled: contiBlocked,
      command: () => emit('conti-bancari', data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.FORNITORE)
// La lista parte vuota — salvo che arrivi con search precaricata da URL/context.
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('fornitori.search_placeholder')"
        />
        <LookupSelect
          v-model="statoFilter"
          rel="config.stati_fornitore"
          :placeholder="t('fornitori.filtro_stato')"
          show-clear
          @change="onStatoChange"
        />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <!-- Placeholder: nessuna ricerca effettuata -->
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
      scrollHeight="flex"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      selection-mode="single"
      data-key="id"
    >
      <Column field="codice" :header="t('fornitori.col_codice')" sortable style="width: 130px;" />
      <Column field="ragione_sociale_completa" :header="t('fornitori.col_ragione_sociale')" sortable style="width: 200px;" />
      <Column field="codice_fiscale" :header="t('fornitori.col_id_fiscale')" style="width: 160px;">
        <template #body="{ data }">{{ data.partita_iva || data.codice_fiscale }}</template>
      </Column>
      <Column field="modalita_pagamento_desc" :header="t('fornitori.col_modalita_pagamento')" sortable style="width: 150px;" />
      <Column field="stato_descrizione" :header="t('fornitori.col_stato')" sortable style="width: 110px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoFornitoreSeverity(data.stato_codice)" />
        </template>
      </Column>
      <Column field="data_insert" :header="t('fornitori.col_data_insert')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_insert) }}</template>
      </Column>
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
