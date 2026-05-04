<script setup>
// Scopo: Sezione integrazione preventivo — push commessa (fatturazione), genera pratica, pratiche collegate.
// Visibile solo per preventivi in stato ACCETTATO. La pratica e' opzionale: il preventivo puo'
// essere eseguito anche senza pratica (fatturazione diretta via commessa).
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { usePreventiviStore } from '../stores/preventivi'
import { statoPraticaSeverity } from '../../../core/utils/severity'
import { displayDate } from '../../../core/utils/date'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const { t } = useI18n()
const store = usePreventiviStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  preventivoId: { type: Number, required: true }
})

const statoFatturazione = ref(null)
const pratiche = ref([])
const loadingFatt = ref(false)
const loadingPratiche = ref(false)

// Scopo: Carica stato fatturazione e pratiche collegate.
async function loadIntegrazione() {
  if (!props.preventivoId) return
  loadingFatt.value = true
  loadingPratiche.value = true
  try {
    statoFatturazione.value = await store.loadStatoFatturazione(props.preventivoId)
  } finally {
    loadingFatt.value = false
  }
  try {
    pratiche.value = await store.loadPratiche(props.preventivoId)
  } finally {
    loadingPratiche.value = false
  }
}

watch(() => props.preventivoId, loadIntegrazione, { immediate: true })

// Scopo: Push preventivo in commessa per fatturazione.
function onPushCommessa() {
  confirmAction({
    message: t('preventivi.conferma_push_commessa'),
    onAccept: async () => {
      const result = await execute(
        () => store.inviaACommessa(props.preventivoId),
        { successMessage: t('preventivi.push_commessa_ok') }
      )
      if (result !== null) await loadIntegrazione()
    }
  })
}

defineExpose({ loadIntegrazione })
</script>

<template>
  <div class="form-grid">
    <!-- Stato fatturazione -->
    <h4 style="margin: 0;">{{ t('preventivi.section_fatturazione') }}</h4>

    <div v-if="statoFatturazione" style="display: flex; gap: 1rem; flex-wrap: wrap; align-items: center;">
      <div class="form-field" style="flex: 0 0 auto;">
        <label>{{ t('preventivi.fatt_totale_righe') }}</label>
        <span>{{ statoFatturazione.totale_righe ?? '-' }}</span>
      </div>
      <div class="form-field" style="flex: 0 0 auto;">
        <label>{{ t('preventivi.fatt_in_commessa') }}</label>
        <span>{{ statoFatturazione.righe_in_commessa ?? '-' }}</span>
      </div>
      <div class="form-field" style="flex: 0 0 auto;">
        <label>{{ t('preventivi.fatt_fatturate') }}</label>
        <span>{{ statoFatturazione.righe_fatturate ?? '-' }}</span>
      </div>
    </div>
    <div v-else-if="!loadingFatt" style="color: var(--text-color-secondary); font-style: italic;">
      {{ t('preventivi.fatt_non_disponibile') }}
    </div>

    <Button icon="pi pi-send" :label="t('preventivi.push_commessa')" severity="info" size="small"
      :loading="loading" @click="onPushCommessa" style="align-self: flex-start;" />

    <!-- Pratiche collegate (opzionale) -->
    <h4 style="margin: 1rem 0 0;">{{ t('preventivi.section_pratiche') }}</h4>
    <p style="margin: 0; font-size: 0.85rem; color: var(--text-color-secondary);">
      {{ t('preventivi.pratiche_opzionali') }}
    </p>

    <DataTable v-if="pratiche.length" :value="pratiche" striped-rows size="small"
      class="app-datatable" scrollable scrollHeight="150px" data-key="id">
      <Column field="pratica_codice" :header="t('preventivi.pratica_codice')" style="width: 120px;" />
      <Column field="stato_descrizione" :header="t('preventivi.pratica_stato')" style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoPraticaSeverity(data.stato_codice_interno)" />
        </template>
      </Column>
      <Column field="tipo_prestazione_descrizione" :header="t('preventivi.pratica_tipo')" style="min-width: 160px;" />
      <Column field="data_apertura" :header="t('preventivi.pratica_data')" style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_apertura) }}</template>
      </Column>
    </DataTable>
    <div v-else-if="!loadingPratiche" style="color: var(--text-color-secondary); font-style: italic;">
      {{ t('preventivi.nessuna_pratica') }}
    </div>
  </div>
</template>
