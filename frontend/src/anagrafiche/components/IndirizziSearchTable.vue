<script setup>
// Scopo: DataTable indirizzi dettaglio con ricerca, filtro comune e CRUD.
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useIndirizziStore } from '../stores/indirizzi'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import ComuneAutocomplete from '../../core/components/ComuneAutocomplete.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import AttivoTag from '../../core/components/AttivoTag.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useIndirizziStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, { defaultSortField: 'indirizzo_normalizzato' })

const comuneFilter = ref(null)
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
    tooltip: t('indirizzi.nuovo_indirizzo'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

useTabFreshness(store, TAB_ENTITIES.INDIRIZZO)
// La lista parte vuota — salvo che arrivi con search precaricata da URL/context.
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})

function onComuneChange(id) {
  comuneFilter.value = id
  store.filters.comune_id = id
  applyFilters()
}

function onRowClick(event) {
  emit('row-click', event.data)
}
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('indirizzi.search_indirizzo')"
        />
        <ComuneAutocomplete
          :model-value="comuneFilter"
          @update:model-value="onComuneChange"
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
      data-key="indirizzo_dettaglio_id"
    >
      <Column field="indirizzo_normalizzato" :header="t('indirizzi.col_indirizzo')" sortable />
      <Column field="descrizione_comune" :header="t('indirizzi.col_comune')" sortable />
      <Column field="provincia" :header="t('indirizzi.col_provincia')" sortable />
      <Column field="cap" :header="t('indirizzi.col_cap')" sortable />
      <Column field="attivo" :header="t('indirizzi.col_attivo')" sortable>
        <template #body="{ data }">
          <AttivoTag :active="data.attivo" :active-label="t('indirizzi.attivo')" :inactive-label="t('indirizzi.non_attivo')" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
