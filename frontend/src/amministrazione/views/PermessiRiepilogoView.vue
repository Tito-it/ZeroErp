<script setup>
// Scopo: vista riepilogo permessi effettivi (matrice operatori × aree).
// Mostra per ogni operatore attivo il livello effettivo calcolato dal backend
// su ogni area funzionale. Filtri per reparto e ruolo.
import { ref, watch, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useLookup } from '../../core/composables/useLookup'
import { getPermessiRiepilogo, listUnitaOrganizzative, listEmittentiFiscali } from '../api/amministrazione'
import { buildRuoloOptions, getLivelloSeverity, getLivelloLabel, getRuoloSeverity } from '../constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

const { t } = useI18n()
useReadonlyMode('amm_software')

const loading = ref(false)
const aree = ref([])
const operatori = ref([])
let fetchSeq = 0

const repartoFilter = ref(null)
const ruoloFilter = ref(null)
const emittenteFilter = ref(null)
const unitaOrg = useLookup(listUnitaOrganizzative, { immediate: true })
const emittenti = useLookup(listEmittentiFiscali, { immediate: true })
const ruoloOptions = buildRuoloOptions(t, { includeAll: true })

// Se esiste un solo emittente, impostalo come default e carica
const emittentiReady = ref(false)
watch(() => emittenti.items.value, (items) => {
  if (items.length > 0 && !emittentiReady.value) {
    emittentiReady.value = true
    if (items.length === 1) {
      emittenteFilter.value = items[0].id
    }
    fetchData()
  }
}, { immediate: true })

async function fetchData() {
  const seq = ++fetchSeq
  loading.value = true
  try {
    const params = {}
    if (repartoFilter.value) params.unita_organizzativa_id = repartoFilter.value
    if (ruoloFilter.value) params.ruolo_sistema = ruoloFilter.value
    if (emittenteFilter.value) params.emittente_fiscale_id = emittenteFilter.value
    const res = await getPermessiRiepilogo(params)
    if (seq !== fetchSeq) return // risposta obsoleta, scarta
    const data = res.data?.data || {}
    aree.value = data.aree || []
    operatori.value = data.operatori || []
  } finally {
    if (seq === fetchSeq) loading.value = false
  }
}

// fetchData chiamato dal watch emittenti dopo il caricamento lookup

function applyFilters() {
  fetchData()
}

// Colonne dinamiche per aree funzionali
const areaColumns = computed(() =>
  aree.value.map(a => ({
    field: `area_${a.codice}`,
    header: a.descrizione,
    codice: a.codice
  }))
)
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <Select
          v-model="emittenteFilter"
          :options="[{ ragione_sociale: t('amm.permessi_filter_emittente'), id: null }, ...emittenti.items.value]"
          :loading="emittenti.loading.value"
          option-label="ragione_sociale"
          option-value="id"
          :placeholder="t('amm.permessi_filter_emittente')"
          @change="applyFilters"
        />
        <Select
          v-model="repartoFilter"
          :options="[{ descrizione: t('amm.select_reparto'), id: null }, ...unitaOrg.items.value]"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('amm.permessi_filter_reparto')"
          @change="applyFilters"
        />
        <Select
          v-model="ruoloFilter"
          :options="ruoloOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amm.permessi_filter_ruolo')"
          @change="applyFilters"
        />
      </div>
    </div>

    <DataTable
      :value="operatori"
      :loading="loading"
      striped-rows
      scrollable
      scrollHeight="flex"
      removable-sort
      sortField="cognome"
      :sortOrder="1"
      class="app-datatable"
      data-key="auth_user_id"
    >
      <Column field="cognome" :header="t('amm.permessi_col_operatore')" sortable frozen>
        <template #body="{ data }">
          {{ data.cognome }} {{ data.nome }}
        </template>
      </Column>
      <Column field="reparto" :header="t('amm.permessi_col_reparto')" sortable />
      <Column field="ruolo_sistema" :header="t('amm.permessi_col_ruolo')" sortable style="width: 8rem">
        <template #body="{ data }">
          <Tag :value="data.ruolo_sistema" :severity="getRuoloSeverity(data.ruolo_sistema)" />
        </template>
      </Column>
      <Column
        v-for="col in areaColumns"
        :key="col.field"
        :field="col.field"
        :header="col.header"
        style="width: 7rem; text-align: center"
      >
        <template #body="{ data }">
          <Tag
            :value="getLivelloLabel(t, data[col.field])"
            :severity="getLivelloSeverity(data[col.field])"
            class="w-full"
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>
