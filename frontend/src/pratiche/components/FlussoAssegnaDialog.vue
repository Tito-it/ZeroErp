<script setup>
// Scopo: Dialog di assegnazione di un flusso a un reparto e/o a un operatore.
// Policy reparto-first: si sceglie prima il reparto, poi (opzionale) un operatore
// di quel reparto. Entrambi svuotabili → de-assegnazione. Il dialog rappresenta
// lo stato completo di assegnazione: alla conferma invia entrambe le chiavi
// (null incluso), così il BE applica reparto e operatore in un colpo.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { assegnaFlusso, fetchOperatoriReparto } from '../api/pratiche-api'
import AppDialog from '../../core/components/AppDialog.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Select from 'primevue/select'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

const { t } = useI18n()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  praticaId: { type: Number, default: null },
  flussoId: { type: Number, default: null },
  // Valori correnti per il pre-fill del dialog.
  currentRisorsaId: { type: Number, default: null },
  currentUnitaId: { type: Number, default: null },
})

const emit = defineEmits(['update:visible', 'saved'])

const repartoId = ref(null)
const operatoreId = ref(null)
const operatoriOptions = ref([])
const operatoriLoading = ref(false)

// Scopo: Carica gli operatori del reparto selezionato (picker filtrato).
async function loadOperatori(unitaId) {
  if (!unitaId) { operatoriOptions.value = []; return }
  operatoriLoading.value = true
  try {
    const res = await fetchOperatoriReparto(unitaId)
    operatoriOptions.value = res.data.data.results
  } finally {
    operatoriLoading.value = false
  }
}

// Pre-fill all'apertura: reparto + operatore correnti del flusso.
watch(() => props.visible, async (val) => {
  if (!val) return
  repartoId.value = props.currentUnitaId ?? null
  operatoreId.value = props.currentRisorsaId ?? null
  await loadOperatori(repartoId.value)
})

// Cambio reparto: azzera l'operatore (non è più garantito appartenga al nuovo
// reparto) e ricarica le opzioni.
function onRepartoChange(val) {
  operatoreId.value = null
  loadOperatori(val)
}

async function onSave() {
  const result = await execute(
    () => assegnaFlusso(props.praticaId, props.flussoId, {
      unita_organizzativa_id: repartoId.value ?? null,
      risorsa_umana_id: operatoreId.value ?? null,
    }),
    { successMessage: t('pratiche.flusso_assegnato') },
  )
  if (result !== null) {
    emit('saved')
    emit('update:visible', false)
  }
}

function onCancel() {
  emit('update:visible', false)
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ repartoId: repartoId.value, operatoreId: operatoreId.value }), { visibile: () => props.visible })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="props.visible"
    :header="t('pratiche.flusso_assegna')"
    width="sm"
    :loading="loading"
    :save-label="t('common.save')"
    @update:visible="val => emit('update:visible', val)"
    @save="onSave"
    @cancel="onCancel"
  >
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('pratiche.flusso_reparto') }}</label>
        <LookupSelect
          v-model="repartoId"
          rel="config.unita_organizzative"
          show-clear
          :placeholder="t('pratiche.flusso_reparto_placeholder')"
          @update:modelValue="onRepartoChange"
        />
      </div>
      <div class="form-field">
        <label>{{ t('pratiche.flusso_assegnatario') }}</label>
        <Select
          v-model="operatoreId"
          :options="operatoriOptions"
          :loading="operatoriLoading"
          option-label="display"
          option-value="id"
          show-clear
          :disabled="!repartoId"
          :placeholder="repartoId
            ? t('pratiche.flusso_assegnatario_placeholder')
            : t('pratiche.flusso_assegnatario_scegli_reparto')"
        />
      </div>
    </div>
  </AppDialog>
</template>
