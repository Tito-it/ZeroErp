<script setup>
// Scopo: DataTable paginata soggetti con search e filtro tipo.
// Riusabile da: SoggettiView, futuro ricerca soggetti in altri domini.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSoggettiStore } from '../stores/soggetti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useLookup } from '../../core/composables/useLookup'
import { lookupTipiSoggettoDettaglio } from '../../core/apiCore'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import TagList from '../../core/components/TagList.vue'
import NewButton from '../../core/components/NewButton.vue'
import Button from 'primevue/button'

const emit = defineEmits(['new', 'row-click', 'contatti', 'indirizzi', 'conti-bancari'])
const { t } = useI18n()
const store = useSoggettiStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'ragione_sociale_completa'
})

const tipiSoggetto = useLookup(lookupTipiSoggettoDettaglio, { immediate: true })
const tipoFilter = ref(null)

function onTipoChange() {
  store.filters.tipo_soggetto_dettaglio_id = tipoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, 'soggetto')
onMounted(() => { store.fetchList() })
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('soggetti.search_placeholder')"
        />
        <Select
          v-model="tipoFilter"
          :options="tipiSoggetto.items.value"
          :loading="tipiSoggetto.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('soggetti.filtro_tipo')"
          show-clear
          @change="onTipoChange"
        />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('soggetti.nuovo_soggetto')" @click="emit('new')" />
      </div>
    </div>

    <DataTable
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
      <Column field="codice" :header="t('config_panel.col_codice')" sortable style="width: 130px;" />
      <Column field="ragione_sociale_completa" :header="t('soggetti.col_ragione_sociale')" sortable style="width: 180px;" />
      <Column field="codice_fiscale" :header="t('common.id_fiscale')" sortable style="width: 170px;" />
      <Column field="tipo_descrizione" :header="t('soggetti.col_tipo')" sortable style="width: 100px;" />
      <Column field="ruoli" :header="t('soggetti.col_ruoli')" style="width: 240px;">
        <template #body="{ data }">
          <TagList :items="data.ruoli || []" />
        </template>
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
