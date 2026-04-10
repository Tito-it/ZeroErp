<script setup>
// Scopo: DataTable paginata clienti con search, filtro utility e stato.
// Riusabile da: ClientiView, futuro ricerca clienti in altri domini.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClientiStore } from '../stores/clienti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { MANAGE_ICONS, TIPO_RUOLO } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { statoClienteSeverity } from '../../core/utils/severity'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'

const emit = defineEmits(['new', 'row-click', 'contatti', 'indirizzi', 'conti-bancari'])
const { t } = useI18n()
const store = useClientiStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'ragione_sociale_completa'
})

// Filtri
const utilityFilter = ref(null)
const statoFilter = ref(null)

function onUtilityChange() {
  store.filters.utility_id = utilityFilter.value
  applyFilters()
}

function onStatoChange() {
  store.filters.stato_cliente_id = statoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

// Scopo: Mostra data sospensione o riattivazione (l'ultima in ordine cronologico).
function dataSospRiatt(row) {
  const sosp = row.data_sospensione
  const riatt = row.data_riattivazione
  if (!sosp && !riatt) return null
  if (sosp && !riatt) return { label: 'clienti.col_sospeso_il', date: sosp }
  if (!sosp && riatt) return { label: 'clienti.col_riattivato_il', date: riatt }
  return sosp > riatt
    ? { label: 'clienti.col_sospeso_il', date: sosp }
    : { label: 'clienti.col_riattivato_il', date: riatt }
}

useTabFreshness(store, 'cliente')
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
          :placeholder="t('clienti.search_placeholder')"
        />
        <UtilityPerRuoloSelect
          v-model="utilityFilter"
          :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
          :placeholder="t('clienti.filtro_utility')"
          show-clear
          @change="onUtilityChange"
        />
        <LookupSelect
          v-model="statoFilter"
          rel="config.stati_cliente"
          :placeholder="t('clienti.filtro_stato')"
          show-clear
          @change="onStatoChange"
        />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('clienti.nuovo_cliente')" @click="emit('new')" />
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
      <Column field="soggetto_codice" :header="t('clienti.col_cd_soggetto')" sortable style="width: 140px;" />
      <Column field="ba_codice" :header="t('clienti.col_ba_codice')" sortable style="width: 140px;" />
      <Column field="ragione_sociale_completa" :header="t('clienti.col_ragione_sociale')" sortable style="width: 180px;" />
      <Column field="codice_fiscale" :header="t('clienti.col_id_fiscale')" sortable style="width: 160px;">
        <template #body="{ data }">{{ data.codice_fiscale || data.partita_iva }}</template>
      </Column>
      <Column field="utility_descrizione" :header="t('clienti.col_utility')" sortable style="width: 130px;" />
      <Column field="stato_descrizione" :header="t('clienti.col_stato')" sortable style="width: 110px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoClienteSeverity(data.stato_codice)" />
        </template>
      </Column>
      <Column field="data_attivazione" :header="t('clienti.col_data_attivazione')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_attivazione) }}</template>
      </Column>
      <Column field="data_chiusura" :header="t('clienti.col_data_chiusura')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_chiusura) }}</template>
      </Column>
      <Column :header="t('clienti.col_sosp_riatt')" style="width: 130px;">
        <template #body="{ data }">
          <span v-if="data.data_sospensione || data.data_riattivazione">
            <small class="text-color-secondary">{{ t(dataSospRiatt(data).label) }}</small><br>
            {{ displayDate(dataSospRiatt(data).date) }}
          </span>
        </template>
      </Column>
      <Column :header="t('soggetti.col_azioni')" style="width: 80px;" :exportable="false">
        <template #body="{ data }">
          <div style="display: flex; gap: 0.25rem;">
            <Button :icon="MANAGE_ICONS.CONTATTI" text rounded size="small" class="app-manage-btn"
              v-tooltip.top="t('contatto.gestisci_contatti')"
              @click.stop="emit('contatti', data)" />
            <Button :icon="MANAGE_ICONS.INDIRIZZI" text rounded size="small" class="app-manage-btn"
              v-tooltip.top="t('indirizzo_soggetto.gestisci_indirizzi')"
              @click.stop="emit('indirizzi', data)" />
            <Button :icon="MANAGE_ICONS.CONTI_BANCARI" text rounded size="small" class="app-manage-btn"
              v-tooltip.top="t('conti_bancari.gestisci_conti')"
              @click.stop="emit('conti-bancari', data)" />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</template>
