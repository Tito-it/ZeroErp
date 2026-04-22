<script setup>
// Scopo: DataTable paginata soggetti con search e filtro tipo.
// Riusabile da: SoggettiView, futuro ricerca soggetti in altri domini.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSoggettiStore } from '../stores/soggetti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useLookup } from '../../core/composables/useLookup'
import { lookupTipiSoggettoDettaglio } from '../../core/apiCore'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import TagList from '../../core/components/TagList.vue'
import NewButton from '../../core/components/NewButton.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'

const emit = defineEmits(['new', 'row-click', 'contatti', 'indirizzi', 'conti-bancari'])
const { t } = useI18n()
const store = useSoggettiStore()
const auth = useAuthStore()
const isBlocked = useInjectBlocked()
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

// Scopo: azioni di riga del soggetto (sub-drawer anagrafici).
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

useTabFreshness(store, TAB_ENTITIES.SOGGETTO)
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
        <ReadonlyBadge />
        <ReloadButton @click="reload" />
        <NewButton :tooltip="t('soggetti.nuovo_soggetto')" @click="emit('new')" />
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
      <Column field="codice" :header="t('config_panel.col_codice')" sortable style="width: 130px;" />
      <Column field="ragione_sociale_completa" :header="t('soggetti.col_ragione_sociale')" sortable style="width: 180px;" />
      <Column field="codice_fiscale" :header="t('common.id_fiscale')" sortable style="width: 170px;" />
      <Column field="tipo_descrizione" :header="t('soggetti.col_tipo')" sortable style="width: 100px;" />
      <Column field="ruoli" :header="t('soggetti.col_ruoli')" style="width: 240px;">
        <template #body="{ data }">
          <TagList :items="data.ruoli || []" />
        </template>
      </Column>
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
