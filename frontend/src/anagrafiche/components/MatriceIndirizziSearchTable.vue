<script setup>
// Scopo: DataTable matrice indirizzi per ruolo con inline-edit
// su obbligatorio, fallback e attivo. Filtro per tipo ruolo.
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useLookup } from '../../core/composables/useLookup'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { lookupCodici } from '../../core/apiCore'
import { listMatriceIndirizzi, updateMatriceIndirizzo } from '../api/anagrafiche'
import { displayDate } from '../../core/utils/date'
import { defineStore } from 'pinia'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import NewButton from '../../core/components/NewButton.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const { execute } = useApiHandler()

// Store inline (non serve file separato — pattern config tables)
const useMatriceStore = defineStore('anagrafiche-matrice-indirizzi', () => {
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const filters = ref({
    search: '',
    tipo_ruolo_id: null,
    limit: 50,
    offset: 0,
    order_by: 'tipo_ruolo_descrizione',
    order_dir: 'asc'
  })

  async function fetchList() {
    loading.value = true
    try {
      const params = {}
      const f = filters.value
      if (f.search) params.search = f.search
      if (f.tipo_ruolo_id != null) params.tipo_ruolo_id = f.tipo_ruolo_id
      params.limit = f.limit
      params.offset = f.offset
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      const res = await listMatriceIndirizzi(params)
      items.value = res.data.data.results
      totalRecords.value = res.data.data.count
    } finally {
      loading.value = false
    }
  }

  return { items, totalRecords, loading, filters, fetchList }
})

const store = useMatriceStore()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'tipo_ruolo_descrizione'
})

// Lookup filtri
const tipiRuoli = useLookup(() => lookupCodici('config.tipi_ruoli'), { immediate: true })
const tipiIndirizzi = useLookup(() => lookupCodici('config.tipi_indirizzi'), { immediate: true })

const ruoloFilter = ref(null)

function onRuoloChange() {
  store.filters.tipo_ruolo_id = ruoloFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

// Scopo: Opzioni fallback per una riga (tutti i tipi indirizzo tranne il tipo della riga).
function fallbackOptions(row) {
  return tipiIndirizzi.items.value.filter(ti => ti.id !== row.tipo_indirizzo_id)
}

// Scopo: PATCH inline per toggle obbligatorio.
async function toggleObbligatorio(row) {
  const newVal = !row.obbligatorio
  const result = await execute(
    () => updateMatriceIndirizzo(row.id, { obbligatorio: newVal }),
    { successMessage: t('matrice_indirizzi.regola_salvata') }
  )
  if (result !== null) {
    row.obbligatorio = newVal
  }
}

// Scopo: PATCH inline per toggle attivo (con logica valido_al).
async function toggleAttivo(row) {
  const newVal = !row.attivo
  const result = await execute(
    () => updateMatriceIndirizzo(row.id, { attivo: newVal }),
    { successMessage: t('matrice_indirizzi.regola_salvata') }
  )
  if (result !== null) {
    row.attivo = newVal
    // Ricarica per aggiornare valido_al
    store.fetchList()
  }
}

// Scopo: PATCH inline per cambio fallback.
async function changeFallback(row, newFallbackId) {
  const result = await execute(
    () => updateMatriceIndirizzo(row.id, { fallback_tipo_indirizzo_id: newFallbackId || null }),
    { successMessage: t('matrice_indirizzi.regola_salvata') }
  )
  if (result !== null) {
    row.fallback_tipo_indirizzo_id = newFallbackId || null
    // Aggiorna descrizione fallback locale
    const fb = tipiIndirizzi.items.value.find(ti => ti.id === newFallbackId)
    row.fallback_descrizione = fb ? fb.descrizione : null
  }
}

useTabFreshness(store, 'matrice-indirizzi')
onMounted(() => { store.fetchList() })
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('matrice_indirizzi.search_placeholder')"
        />
        <Select
          v-model="ruoloFilter"
          :options="tipiRuoli.items.value"
          :loading="tipiRuoli.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('matrice_indirizzi.filtro_ruolo')"
          show-clear
          @change="onRuoloChange"
        />
      </div>
      <div class="app-page-actions">
        <Button icon="pi pi-refresh" text class="app-reload-btn" v-tooltip.bottom="t('common.reload_list')" @click="reload" />
        <NewButton :tooltip="t('matrice_indirizzi.nuova_regola')" @click="emit('new')" />
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
      <Column field="tipo_ruolo_descrizione" :header="t('matrice_indirizzi.col_ruolo')" sortable style="width: 150px;" />
      <Column field="tipo_indirizzo_descrizione" :header="t('matrice_indirizzi.col_tipo_indirizzo')" sortable style="width: 160px;" />
      <Column field="obbligatorio" :header="t('matrice_indirizzi.col_obbligatorio')" sortable style="width: 100px;">
        <template #body="{ data }">
          <div @click.stop>
            <ToggleSwitch :modelValue="data.obbligatorio" @update:modelValue="toggleObbligatorio(data)" />
          </div>
        </template>
      </Column>
      <Column field="fallback_descrizione" :header="t('matrice_indirizzi.col_fallback')" style="width: 180px;">
        <template #body="{ data }">
          <div @click.stop>
            <Select
              :modelValue="data.fallback_tipo_indirizzo_id"
              @update:modelValue="val => changeFallback(data, val)"
              :options="fallbackOptions(data)"
              option-label="descrizione"
              option-value="id"
              :placeholder="t('matrice_indirizzi.nessun_fallback')"
              show-clear
              class="w-full"
              style="min-width: 140px;"
            />
          </div>
        </template>
      </Column>
      <Column field="attivo" :header="t('matrice_indirizzi.col_attivo')" sortable style="width: 80px;">
        <template #body="{ data }">
          <div @click.stop>
            <ToggleSwitch :modelValue="data.attivo" @update:modelValue="toggleAttivo(data)" />
          </div>
        </template>
      </Column>
      <Column field="valido_dal" :header="t('matrice_indirizzi.col_valido_dal')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
      </Column>
      <Column field="valido_al" :header="t('matrice_indirizzi.col_valido_al')" style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.valido_al) }}</template>
      </Column>
    </DataTable>
  </div>
</template>
