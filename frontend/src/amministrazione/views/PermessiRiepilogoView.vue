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
import { getPermessiRiepilogo, listUnitaOrganizzative } from '../api/amministrazione'
import { listEmittentiFiscali } from '../../core/apiCore'
import { buildFilterSuperAdminOptions, getLivelloSeverity, getLivelloLabel } from '../constants'
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useContrattoFiltriLocali } from '../../core/composables/useContrattoFiltriLocali'

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

// Scopo: il contratto dei filtri di questa pagina — chi sono, che default
//        hanno, il segno che mostrano e «Pulisci filtri». UNA sede: chiave,
//        `rif` e default sulla stessa riga.
// ⭐ L'emittente puo' nascere VALORIZZATO (quando ce n'e' uno solo lo sceglie la
//    pagina, a lettura avvenuta): li' il default dichiarato resta `null`, quindi
//    il numero si vede in BLU e non in grigio. E' la regola D9 — si contano
//    sempre i filtri, default compresi — e il numero resta vero: quell'emittente
//    sta filtrando.
const {
  segno: segnoFiltriPagina,
  azzeraFiltri: pulisciFiltri,
} = useContrattoFiltriLocali({
  emittente_fiscale_id: { rif: emittenteFilter, default: null },
  unita_organizzativa_id: { rif: repartoFilter, default: null },
  super_admin: { rif: superAdminFilter, default: null },
}, { onAzzera: () => applyFilters() })

function applyFilters() {
  fetchData()
}

// Tag stato operatore multi-face: SUPER_ADMIN ha precedenza
// (warn=privilegio elevato), poi disabilitato (danger), poi default.
// ⭐ «Disabilitato» si legge dalla VESTE operatore spenta (`veste_attiva`,
//    2026-10-02, R-DB-1: il ruolo non cambia piu'), o dalla credenziale spenta.
function disabilitato(op) {
  return op.veste_attiva === false || op.is_active === false
}

function getStatoSeverity(op) {
  if (op.is_super_admin) return 'warn'
  if (disabilitato(op)) return 'danger'
  return 'info'
}

function getStatoLabel(op) {
  if (op.is_super_admin) return t('amministrazione.permessi_stato_super_admin')
  if (disabilitato(op)) return t('amministrazione.permessi_stato_disabilitato')
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
      <!-- ⚠️ `:segno` e non `:store`: questa pagina non ha uno store-lista —
           i filtri sono tre ref e la fetch e' locale. E' il ripiego dichiarato
           dal brief per le superfici senza store, e resta l'unica sede del
           conteggio. -->
      <FiltriLista :segno="segnoFiltriPagina" @pulisci="pulisciFiltri">
        <Select
          v-model="emittenteFilter"
          class="app-filter-w-md"
          :options="[{ ragione_sociale: t('amministrazione.permessi_filter_emittente'), id: null }, ...emittenti.items.value]"
          :loading="emittenti.loading.value"
          option-label="ragione_sociale"
          option-value="id"
          :placeholder="t('amministrazione.permessi_filter_emittente')"
          @change="applyFilters"
        />
        <Select
          v-model="repartoFilter"
          class="app-filter-w-md"
          :options="[{ descrizione: t('amministrazione.select_reparto'), id: null }, ...unitaOrg.items.value]"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('amministrazione.permessi_filter_reparto')"
          @change="applyFilters"
        />
        <Select
          v-model="superAdminFilter"
          class="app-filter-w-sm"
          :options="superAdminOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.filter_super_admin_tutti')"
          @change="applyFilters"
        />
      </FiltriLista>
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
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>
