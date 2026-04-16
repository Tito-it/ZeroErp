<script setup>
// Scopo: DataTable admin categorie cliente (anagrafiche.categorie_clienti).
//        Pattern UtilitiesTipiRuoloSearchTable. Tabella codice/descrizione
//        classica + flag partecipa_promo + ordinamento + attivo.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCategorieClientiStore } from '../stores/categorieClienti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useCategorieClientiStore()
const isReadonly = useInjectReadonly()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'ordinamento'
})

const attivoFilter = ref(true)
const partecipaPromoFilter = ref(null)

const boolOptions = [
  { value: null, label: t('common.all') },
  { value: true, label: t('common.yes') },
  { value: false, label: t('common.no') }
]

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

function onPartecipaPromoChange() {
  store.filters.partecipa_promo = partecipaPromoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, 'categorie_clienti')
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('amministrazione.categorie_clienti.search_placeholder')"
        />
        <Select
          v-model="partecipaPromoFilter"
          :options="boolOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.categorie_clienti.filter_partecipa_promo')"
          @change="onPartecipaPromoChange"
          style="width: 180px;"
        />
        <Select
          v-model="attivoFilter"
          :options="boolOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('common.attivo')"
          @change="onAttivoChange"
          style="width: 120px;"
        />
      </div>
      <div class="app-page-actions">
        <Button
          icon="pi pi-refresh"
          text
          class="app-reload-btn"
          v-tooltip.bottom="t('common.reload_list')"
          @click="reload"
        />
        <NewButton
          v-if="!isReadonly"
          :tooltip="t('amministrazione.categorie_clienti.new')"
          @click="emit('new')"
        />
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
      <Column
        field="codice"
        :header="t('amministrazione.categorie_clienti.col_codice')"
        sortable
        style="width: 160px;"
      />
      <Column
        field="descrizione"
        :header="t('amministrazione.categorie_clienti.col_descrizione')"
        sortable
        style="min-width: 300px;"
      />
      <Column
        field="ordinamento"
        :header="t('amministrazione.categorie_clienti.col_ordinamento')"
        sortable
        style="width: 120px;"
      />
      <Column
        field="partecipa_promo"
        :header="t('amministrazione.categorie_clienti.col_partecipa_promo')"
        sortable
        style="width: 160px;"
      >
        <template #body="{ data }">
          <Tag
            :value="data.partecipa_promo ? t('common.yes') : t('common.no')"
            :severity="data.partecipa_promo ? 'info' : 'secondary'"
          />
        </template>
      </Column>
      <Column
        field="attivo"
        :header="t('amministrazione.categorie_clienti.col_attivo')"
        sortable
        style="width: 100px;"
      >
        <template #body="{ data }">
          <Tag
            :value="data.attivo ? t('common.active') : t('common.inactive')"
            :severity="data.attivo ? 'success' : 'warn'"
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>
