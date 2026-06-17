<script setup>
// Scopo: Tab "Flussi" della scheda pratica — SOLA LETTURA.
// Due liste informative:
//   1) Flussi istanziati della pratica (stato, esito, sequenza, scadenza);
//   2) Step del percorso ancora da completare (roadmap residua).
// Creazione ed esecuzione dei flussi NON vivono qui: avvengono nel percorso
// template-driven della dashboard (PraticaPercorso + FlussoDrawer), unica
// sorgente di verita'. La vecchia creazione di "flusso generico" (senza
// template) e le azioni avvia/completa inline sono state rimosse (fuori modello).
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listFlussi, fetchPercorso } from '../api/pratiche-api'
import { displayDate } from '../../core/utils/date'
import { statoFlussoSeverity } from '../../core/utils/severity'
import { STATO_FLUSSO, RAMO_STEP } from '../../core/constants'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'

const { t } = useI18n()

const props = defineProps({
  praticaId: { type: Number, required: true },
})

const flussi = ref([])
const percorso = ref([])
const loading = ref(false)

async function loadAll() {
  if (!props.praticaId) return
  loading.value = true
  try {
    const [resFlussi, resPercorso] = await Promise.all([
      listFlussi(props.praticaId),
      fetchPercorso(props.praticaId),
    ])
    flussi.value = resFlussi.data.data.results || []
    percorso.value = resPercorso.data.data.results || []
  } finally {
    loading.value = false
  }
}

// Step del percorso ancora da completare: non esiste un'istanza COMPLETATO e
// lo step e' ancora percorribile (escludo il ramo morto di un bivio, che non
// sara' eseguito). Include "da creare" (flusso_id null) e in corso/da eseguire.
// Vista "cosa resta da fare", complementare alla lista flussi.
const stepNonEseguiti = computed(() =>
  percorso.value.filter(
    s => s.stato_codice_interno !== STATO_FLUSSO.COMPLETATO && s.ramo !== RAMO_STEP.RAMO_CHIUSO,
  ),
)

watch(() => props.praticaId, (id) => { if (id) loadAll() }, { immediate: true })
</script>

<template>
  <div class="pratica-flussi-tab">
    <!-- Lista 1: flussi istanziati (sola lettura) -->
    <h4 class="pratica-flussi-titolo">{{ t('pratiche.flussi_titolo') }}</h4>
    <DataTable
      :value="flussi"
      :loading="loading"
      striped-rows
      class="app-datatable"
      data-key="id"
    >
      <Column field="sequenza" :header="t('pratiche.flusso_col_seq')" style="width: 60px;" />
      <Column field="template_flusso_descrizione" :header="t('pratiche.flusso_col_template')" style="width: 180px;">
        <template #body="{ data }">
          {{ data.template_flusso_descrizione || t('pratiche.flusso_generico') }}
        </template>
      </Column>
      <Column field="stato_codice_interno" :header="t('pratiche.col_stato')" style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione || data.stato_codice_interno" :severity="statoFlussoSeverity(data.stato_codice_interno)" />
        </template>
      </Column>
      <Column field="esito" :header="t('pratiche.flusso_col_esito')" style="width: 100px;">
        <template #body="{ data }">
          <span v-if="data.esito" class="text-color-secondary">{{ data.esito }}</span>
        </template>
      </Column>
      <Column field="data_scadenza" :header="t('pratiche.col_data_scadenza')" style="width: 100px;">
        <template #body="{ data }">{{ displayDate(data.data_scadenza) }}</template>
      </Column>
      <template #empty>
        <div class="text-center text-color-secondary p-3">{{ t('pratiche.flussi_vuoti') }}</div>
      </template>
    </DataTable>

    <!-- Lista 2: step del percorso ancora da completare (sola lettura) -->
    <h4 class="pratica-flussi-titolo">{{ t('pratiche.flussi_step_da_completare') }}</h4>
    <DataTable
      :value="stepNonEseguiti"
      :loading="loading"
      striped-rows
      class="app-datatable"
      data-key="template_flusso_id"
    >
      <Column field="sequenza" :header="t('pratiche.flusso_col_seq')" style="width: 60px;" />
      <Column field="template_flusso_codice" :header="t('pratiche.flusso_col_template')" style="width: 180px;">
        <template #body="{ data }">
          {{ data.template_flusso_descrizione || data.template_flusso_codice }}
        </template>
      </Column>
      <Column :header="t('pratiche.col_stato')" style="width: 120px;">
        <template #body="{ data }">
          <Tag
            v-if="data.flusso_id"
            :value="data.stato_descrizione || data.stato_codice_interno"
            :severity="statoFlussoSeverity(data.stato_codice_interno)"
          />
          <Tag v-else :value="t('pratiche.percorso_da_creare')" severity="secondary" />
        </template>
      </Column>
      <template #empty>
        <div class="text-center text-color-secondary p-3">{{ t('pratiche.flussi_step_tutti_completati') }}</div>
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
.pratica-flussi-titolo {
  margin: 0.75rem 0 0.4rem;
}
.pratica-flussi-titolo:first-child {
  margin-top: 0;
}
</style>
