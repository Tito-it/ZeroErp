<script setup>
// Scopo: DataTable paginata fornitori con search, filtro stato e attivo.
// Riusabile da: FornitoriView, futuro ricerca fornitori in altri domini.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFornitoriStore } from '../stores/fornitori'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { displayDate } from '../../core/utils/date'
import { statoFornitoreSeverity } from '../../core/utils/severity'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'

const emit = defineEmits(['new', 'row-click', 'contatti', 'indirizzi', 'conti-bancari'])
const { t } = useI18n()
const store = useFornitoriStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'ragione_sociale_completa'
})

const statoFilter = ref(null)
function onStatoChange() {
  store.filters.stato_fornitore_id = statoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, 'fornitore')
// La lista parte vuota — salvo che arrivi con search precaricata da URL/context.
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})
</script>

<template>
  <div class="app-tab-content">
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
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('fornitori.nuovo_fornitore')" @click="emit('new')" />
      </div>
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
      <Column :header="t('soggetti.col_azioni')" style="width: 80px;" :exportable="false">
        <template #body="{ data }">
          <div style="display: flex; gap: 0.25rem;">
            <Button icon="pi pi-id-card" text rounded size="small" class="app-action-btn"
              v-tooltip.top="t('contatto.gestisci_contatti')"
              @click.stop="emit('contatti', data)" />
            <Button icon="pi pi-map-marker" text rounded size="small" class="app-action-btn"
              v-tooltip.top="t('indirizzo_soggetto.gestisci_indirizzi')"
              @click.stop="emit('indirizzi', data)" />
            <Button icon="pi pi-wallet" text rounded size="small" class="app-action-btn"
              v-tooltip.top="t('conti_bancari.gestisci_conti')"
              @click.stop="emit('conti-bancari', data)" />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</template>
