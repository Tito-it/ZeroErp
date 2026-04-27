<script setup>
// Scopo: DataTable paginata matrice tipi_ruolo x tipi_indirizzo con search e filtri.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTipiRuoloTipiIndirizzoStore } from '../stores/tipiRuoloTipiIndirizzo'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectReadonly, useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import NewButton from '../../core/components/NewButton.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useTipiRuoloTipiIndirizzoStore()
const isReadonly = useInjectReadonly()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'tipo_ruolo_descrizione'
})

useTabFreshness(store, TAB_ENTITIES.TIPI_RUOLO_TIPI_INDIRIZZO)

const tipoRuoloFilter = ref(store.filters.tipo_ruolo_id)
const tipoIndirizzoFilter = ref(store.filters.tipo_indirizzo_id)
const attivoFilter = ref(store.filters.attivo)

const attivoOptions = [
  { value: true, label: t('common.attivo') },
  { value: false, label: t('common.non_attivo') }
]

function onTipoRuoloChange() {
  store.filters.tipo_ruolo_id = tipoRuoloFilter.value
  applyFilters()
}
function onTipoIndirizzoChange() {
  store.filters.tipo_indirizzo_id = tipoIndirizzoFilter.value
  applyFilters()
}
function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

onMounted(() => { if (!store.hasSearched) store.fetchList() })
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('amministrazione.matrice_indirizzi_ruoli.search_placeholder')"
          @keydown.enter="applyFilters" />
        <LookupSelect v-model="tipoRuoloFilter" rel="config.tipi_ruoli"
          :placeholder="t('amministrazione.matrice_indirizzi_ruoli.filter_tipo_ruolo')"
          show-clear @change="onTipoRuoloChange" />
        <LookupSelect v-model="tipoIndirizzoFilter" rel="config.tipi_indirizzi"
          :placeholder="t('amministrazione.matrice_indirizzi_ruoli.filter_tipo_indirizzo')"
          show-clear @change="onTipoIndirizzoChange" />
        <Select v-model="attivoFilter" :options="attivoOptions" option-label="label" option-value="value"
          :placeholder="t('common.tutti')" show-clear @change="onAttivoChange" />
      </div>
      <div class="app-page-actions">
        <ReadonlyBadge />
        <ReloadButton @click="reload" />
        <NewButton v-if="!isReadonly" :tooltip="t('amministrazione.matrice_indirizzi_ruoli.new_row')" @click="emit('new')" />
      </div>
    </div>

    <DataTable :value="store.items" :loading="store.loading" lazy :totalRecords="store.totalRecords"
      v-bind="paginatorProps" @page="onPage" @sort="onSort"
      striped-rows scrollable scrollHeight="flex" class="app-datatable"
      data-key="id" @row-click="e => emit('row-click', e.data)">
      <template #empty>
        <div class="app-empty-state">{{ t('common.empty_list') }}</div>
      </template>

      <Column field="tipo_ruolo_codice" :header="t('amministrazione.matrice_indirizzi_ruoli.col_tipo_ruolo_codice')" sortable style="width: 120px;" />
      <Column field="tipo_ruolo_descrizione" :header="t('amministrazione.matrice_indirizzi_ruoli.col_tipo_ruolo_descrizione')" sortable style="min-width: 180px;" />
      <Column field="tipo_indirizzo_codice" :header="t('amministrazione.matrice_indirizzi_ruoli.col_tipo_indirizzo_codice')" sortable style="width: 120px;" />
      <Column field="tipo_indirizzo_descrizione" :header="t('amministrazione.matrice_indirizzi_ruoli.col_tipo_indirizzo_descrizione')" sortable style="min-width: 180px;" />
      <Column field="obbligatorio" :header="t('amministrazione.matrice_indirizzi_ruoli.col_obbligatorio')" style="width: 110px;">
        <template #body="{ data }">
          <Tag :value="data.obbligatorio ? t('common.yes') : t('common.no')"
            :severity="data.obbligatorio ? 'warn' : 'secondary'" />
        </template>
      </Column>
      <Column field="fallback_codice" :header="t('amministrazione.matrice_indirizzi_ruoli.col_fallback')" style="width: 140px;">
        <template #body="{ data }">
          {{ data.fallback_codice || '—' }}
        </template>
      </Column>
      <Column field="attivo" :header="t('amministrazione.matrice_indirizzi_ruoli.col_attivo')" sortable style="width: 100px;">
        <template #body="{ data }">
          <Tag :value="data.attivo ? t('common.attivo') : t('common.non_attivo')"
            :severity="data.attivo ? 'success' : 'danger'" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>
