<script setup>
// Scopo: vista riepilogo permessi effettivi (matrice operatori × aree).
// Mostra per ogni operatore attivo il livello effettivo calcolato dal backend
// su ogni area funzionale. Filtri multi-face (Fase 7): reparto,
// SUPER_ADMIN tri-state (tutti/solo super/escludi super), emittente.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { useLookup } from '../../core/composables/useLookup'
import { getPermessiRiepilogo, listUnitaOrganizzative, listEmittentiFiscali } from '../api/amministrazione'
import { buildFilterSuperAdminOptions, getLivelloSeverity, getLivelloLabel } from '../constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)

const loading = ref(false)
const aree = ref([])
const operatori = ref([])
let fetchSeq = 0

const repartoFilter = ref(null)
const superAdminFilter = ref(null)
const emittenteFilter = ref(null)
const unitaOrg = useLookup(listUnitaOrganizzative, { immediate: true })
const emittenti = useLookup(listEmittentiFiscali, { immediate: true })
const superAdminOptions = buildFilterSuperAdminOptions(t)

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
    if (superAdminFilter.value != null) params.is_super_admin = superAdminFilter.value
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

function applyFilters() {
  fetchData()
}

// Tag stato operatore multi-face: SUPER_ADMIN ha precedenza
// (warn=privilegio elevato), poi DISABILITATO (danger), poi default.
function getStatoSeverity(op) {
  if (op.is_super_admin) return 'warn'
  if (op.ruolo_applicativo === 'DISABILITATO' || op.is_active === false) return 'danger'
  return 'info'
}

function getStatoLabel(op) {
  if (op.is_super_admin) return t('amministrazione.permessi_stato_super_admin')
  if (op.ruolo_applicativo === 'DISABILITATO' || op.is_active === false) return t('amministrazione.permessi_stato_disabilitato')
  return t('amministrazione.permessi_stato_operatore')
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
          :options="[{ ragione_sociale: t('amministrazione.permessi_filter_emittente'), id: null }, ...emittenti.items.value]"
          :loading="emittenti.loading.value"
          option-label="ragione_sociale"
          option-value="id"
          :placeholder="t('amministrazione.permessi_filter_emittente')"
          @change="applyFilters"
        />
        <Select
          v-model="repartoFilter"
          :options="[{ descrizione: t('amministrazione.select_reparto'), id: null }, ...unitaOrg.items.value]"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('amministrazione.permessi_filter_reparto')"
          @change="applyFilters"
        />
        <Select
          v-model="superAdminFilter"
          :options="superAdminOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.filter_super_admin_tutti')"
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
      <Column field="cognome" :header="t('amministrazione.permessi_col_operatore')" sortable frozen>
        <template #body="{ data }">
          {{ data.cognome }} {{ data.nome }}
        </template>
      </Column>
      <Column field="reparto" :header="t('amministrazione.permessi_col_reparto')" sortable />
      <Column field="is_super_admin" :header="t('amministrazione.permessi_col_stato')" sortable style="width: 9rem">
        <template #body="{ data }">
          <Tag :value="getStatoLabel(data)" :severity="getStatoSeverity(data)" />
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
