<script setup>
// Scopo: Dialog condiviso per SOSPENDERE o RIATTIVARE una pratica con data/ora
// inserita manualmente (anche retroattiva). Precaricato con l'ora attuale.
// Pattern feedback_dialog_cambio_stato_dati_processo: la transizione richiede
// dati di processo (data/ora effettiva, motivo) non presenti nella testata →
// dialog dedicato invece dell'azione diretta. Usato dai pulsanti Sospendi/
// Riattiva della DrawerActionsBar pratica.
//
// La difesa sulle date e' a DB: l'EXCLUDE ex_sospensioni_no_overlap rifiuta i
// periodi sovrapposti (409 E_SOSPENSIONE_OVERLAP), il guard a10 le date future
// (422 E_SOSPENSIONE_DATA_FUTURA). useApiHandler.execute() mostra il messaggio
// del backend come toast; qui niente validazione di dominio duplicata.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePraticheStore } from '../stores/pratiche'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { toTimestampString, toDateString, istanteComeOraAziendale, oraAziendaleComeIstante, adesso } from '../../core/utils/date'
import AppDialog from '../../core/components/AppDialog.vue'
import Textarea from 'primevue/textarea'
import DatePicker from 'primevue/datepicker'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'
import { DATE_FORMAT } from '../../core/constants'

const { t } = useI18n()
const store = usePraticheStore()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  // 'sospendi' | 'riattiva'
  mode: { type: String, default: 'sospendi' },
  praticaId: { type: Number, default: null },
})

const emit = defineEmits(['update:visible', 'saved'])

const isSospendi = computed(() => props.mode === 'sospendi')

// Form: data_inizio/data_fine precaricati ad adesso; motivo solo in sospensione.
const motivo = ref('')
const dataInizio = ref(null)
const dataFine = ref(null)
const dataRiattivazionePrevista = ref(null)
// Tetto del DatePicker = momento di apertura (no date future, mirror del guard
// DB a10). Fissato all'apertura per non ricostruire `new Date()` a ogni render.
const maxDate = ref(null)

// All'apertura: reset + precarica ora attuale nel campo pertinente al modo.
// ⭐ L'ora che l'operatore legge e digita e' quella dell'AZIENDA, non del PC
//    (T-1, F-4): il DatePicker porta l'orologio dell'azienda nei campi locali
//    (`istanteComeOraAziendale`) e al salvataggio si torna all'istante
//    (`oraAziendaleComeIstante`).
watch(() => props.visible, (open) => {
  if (!open) return
  const now = istanteComeOraAziendale(adesso())
  maxDate.value = now
  motivo.value = ''
  dataRiattivazionePrevista.value = null
  if (isSospendi.value) {
    dataInizio.value = now
    dataFine.value = null
  } else {
    dataFine.value = now
    dataInizio.value = null
  }
})

const header = computed(() =>
  isSospendi.value ? t('pratiche.sosp_dialog_sospendi') : t('pratiche.sosp_dialog_riattiva'),
)
const saveLabel = computed(() =>
  isSospendi.value ? t('pratiche.azione_sospendi') : t('pratiche.azione_riattiva'),
)

const canSave = computed(() => {
  if (!props.praticaId) return false
  return isSospendi.value
    ? !!(motivo.value && motivo.value.trim()) && !!dataInizio.value
    : !!dataFine.value
})

async function onSave() {
  if (!canSave.value) return
  const action = isSospendi.value
    ? () => store.sospendi(props.praticaId, {
        motivo: motivo.value.trim(),
        data_inizio: toTimestampString(oraAziendaleComeIstante(dataInizio.value)),
        data_riattivazione_prevista: toDateString(dataRiattivazionePrevista.value),
      })
    : () => store.riattiva(props.praticaId, {
        data_fine: toTimestampString(oraAziendaleComeIstante(dataFine.value)),
      })
  const successMessage = isSospendi.value
    ? t('pratiche.sosp_sospesa_ok')
    : t('pratiche.sosp_riattivata_ok')
  const result = await execute(action, { successMessage })
  if (result !== null) {
    emit('saved', result)
    emit('update:visible', false)
  }
}

function onCancel() {
  emit('update:visible', false)
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ motivo: motivo.value, dataInizio: dataInizio.value, dataFine: dataFine.value, dataRiattivazionePrevista: dataRiattivazionePrevista.value }), { visibile: () => props.visible })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="props.visible"
    :header="header"
    width="sm"
    :loading="loading"
    :save-disabled="!canSave"
    :save-label="saveLabel"
    @update:visible="v => emit('update:visible', v)"
    @save="onSave"
    @cancel="onCancel"
  >
    <div class="form-grid">
      <!-- Sospensione: motivo + data/ora inizio + (opz.) riattivazione prevista -->
      <template v-if="isSospendi">
        <div class="form-field">
          <label>{{ t('pratiche.sosp_motivo') }} *</label>
          <Textarea v-model="motivo" rows="3" auto-resize
            :placeholder="t('pratiche.sosp_motivo_placeholder')" />
        </div>
        <div class="form-field">
          <label>{{ t('pratiche.sosp_data_inizio') }} *</label>
          <DatePicker v-model="dataInizio" show-time hour-format="24"
            :date-format="DATE_FORMAT" show-icon :max-date="maxDate" />
          <small class="app-text-muted">{{ t('pratiche.sosp_data_hint') }}</small>
        </div>
        <div class="form-field">
          <label>{{ t('pratiche.sosp_riattivazione_prevista') }}</label>
          <DatePicker v-model="dataRiattivazionePrevista"
            :date-format="DATE_FORMAT" show-icon show-button-bar />
          <small class="app-text-muted">{{ t('pratiche.sosp_prevista_hint') }}</small>
        </div>
      </template>

      <!-- Riattivazione: solo data/ora fine -->
      <template v-else>
        <div class="form-field">
          <label>{{ t('pratiche.sosp_data_fine') }} *</label>
          <DatePicker v-model="dataFine" show-time hour-format="24"
            :date-format="DATE_FORMAT" show-icon :max-date="maxDate" />
          <small class="app-text-muted">{{ t('pratiche.sosp_data_hint') }}</small>
        </div>
      </template>
    </div>
  </AppDialog>
</template>
