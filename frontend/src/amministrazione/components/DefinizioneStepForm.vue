<script setup>
// Form inline (create/edit) dei campi CORE di uno step di workflow (FE-3.2,
// anello BE 3). Campi: codice, descrizione, direzione, obbligatorio,
// modalita_esito, esito_default. La `sequenza` NON e' qui: si gestisce col
// riordino ▲▼ nella tabella (per il create la passa il chiamante via
// `next-sequenza`). I campi avanzati (handler/azione_ui/chiude_pratica) sono
// fuori scope (anelli BE dedicati).
//
// Mirror leggero delle invarianti di coerenza (il DB resta l'autorita', guard
// `trgfn_template_flussi_guard_modalita_esito`):
//   Inv3 — DOMINIO ⇒ esito_default VIETATO → campo nascosto, valore forzato a null;
//   Inv1 — AUTOMATICO/CONTESTUALE ⇒ esito_default OBBLIGATORIO;
//   Inv4 — AUTOMATICO/CONTESTUALE ⇒ esito_default deve essere un verdetto
//          (`selezionabile_operatore` = is_verdetto) → opzioni filtrate.
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookup } from '../../core/composables/useLookup'
import {
  STEP_DIREZIONE,
  STEP_MODALITA_ESITO,
  STEP_MODALITA_CON_ESITO_DEFAULT,
} from '../../core/constants'
import { createStep, updateStep } from '../api/definizioniWorkflow'
import { fetchLookupCodici } from '../../core/composables/useLookupCodici'

const props = defineProps({
  definizioneId: { type: Number, required: true },
  // Step da editare; null in create.
  step: { type: Object, default: null },
  // Sequenza suggerita per il nuovo step (max+10), usata solo in create.
  nextSequenza: { type: Number, default: 0 },
})
const emit = defineEmits(['saved', 'cancel'])

const { t } = useI18n()
const { execute, campiErrati } = useApiHandler()

const isEdit = computed(() => !!props.step?.id)
const saving = ref(false)

const form = reactive({
  codice: '',
  descrizione: '',
  direzione: 'INTERNA',
  obbligatorio: false,
  modalita_esito: 'MANUALE',
  esito_default: null,
})

// Sincronizza il form allo step in ingresso (edit) o ai default (create).
watch(
  () => props.step,
  (s) => {
    form.codice = s?.codice ?? ''
    form.descrizione = s?.descrizione ?? ''
    form.direzione = s?.direzione ?? 'INTERNA'
    form.obbligatorio = s?.obbligatorio ?? false
    form.modalita_esito = s?.modalita_esito ?? 'MANUALE'
    form.esito_default = s?.esito_default ?? null
  },
  { immediate: true },
)

const direzioneOptions = computed(() =>
  STEP_DIREZIONE.map((v) => ({ value: v, label: t(`amministrazione.definizioni_workflow.ed_direzione_${v}`) })),
)
const modalitaOptions = computed(() =>
  STEP_MODALITA_ESITO.map((v) => ({ value: v, label: t(`amministrazione.definizioni_workflow.ed_modalita_${v}`) })),
)

// Catalogo esiti (config.esiti_flussi_pratiche): value = codice_interno.
const esiti = useLookup(fetchLookupCodici('config.esiti_flussi_pratiche'), { immediate: true })

const esitoObbligatorio = computed(() => STEP_MODALITA_CON_ESITO_DEFAULT.includes(form.modalita_esito))
const mostraEsitoDefault = computed(() => form.modalita_esito !== 'DOMINIO')
const esitoOptions = computed(() => {
  const rows = esitoObbligatorio.value
    ? esiti.items.value.filter((e) => e.selezionabile_operatore)
    : esiti.items.value
  return rows.map((e) => ({ value: e.codice_interno, label: e.descrizione }))
})

// Inv3: su DOMINIO l'esito_default e' vietato → azzera. Al cambio modalita, se
// l'esito corrente non e' piu' fra le opzioni ammesse, lo si pulisce — ma solo
// a lookup caricato, per non azzerare un valore valido prima del fetch esiti.
watch(
  () => form.modalita_esito,
  () => {
    if (!mostraEsitoDefault.value) {
      form.esito_default = null
    } else if (
      esiti.loaded.value &&
      form.esito_default &&
      !esitoOptions.value.some((o) => o.value === form.esito_default)
    ) {
      form.esito_default = null
    }
  },
)

const canSave = computed(() => {
  if (!form.codice.trim() || !form.descrizione.trim()) return false
  if (esitoObbligatorio.value && !form.esito_default) return false
  return true
})

async function handleSave() {
  const payload = {
    codice: form.codice.trim(),
    descrizione: form.descrizione.trim(),
    direzione: form.direzione,
    obbligatorio: form.obbligatorio,
    modalita_esito: form.modalita_esito,
    esito_default: mostraEsitoDefault.value ? form.esito_default || null : null,
  }
  if (!isEdit.value) payload.sequenza = props.nextSequenza

  saving.value = true
  try {
    const apiCall = isEdit.value
      ? () => updateStep(props.definizioneId, props.step.id, payload)
      : () => createStep(props.definizioneId, payload)
    const res = await execute(apiCall, {
      successMessage: t(isEdit.value ? 'amministrazione.definizioni_workflow.ed_msg_step_salvato' : 'amministrazione.definizioni_workflow.ed_msg_step_creato'),
    })
    if (res !== null) {
      const stepId = res?.step_id ?? props.step?.id ?? null
      emit('saved', stepId)
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <div class="step-form__grid">
      <div class="form-field">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_codice') }} *</label>
        <InputText v-model="form.codice" :disabled="isEdit"
          :invalid="campiErrati.includes('codice')"
        />
        <small v-if="isEdit" class="step-form__hint">{{ t('amministrazione.definizioni_workflow.ed_codice_immutabile') }}</small>
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_direzione') }}</label>
        <Select
          v-model="form.direzione"
          :options="direzioneOptions"
          option-label="label"
          option-value="value"
        />
      </div>
      <div class="form-field step-form__full">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_descrizione') }} *</label>
        <Textarea v-model="form.descrizione" rows="2" auto-resize 
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_modalita_esito') }}</label>
        <Select
          v-model="form.modalita_esito"
          :options="modalitaOptions"
          option-label="label"
          option-value="value"
        />
      </div>
      <div v-if="mostraEsitoDefault" class="form-field">
        <label>
          {{ t('amministrazione.definizioni_workflow.ed_esito_default') }}
          <span v-if="esitoObbligatorio">*</span>
        </label>
        <Select
          v-model="form.esito_default"
          :options="esitoOptions"
          option-label="label"
          option-value="value"
          :loading="esiti.loading.value"
          :placeholder="t('amministrazione.definizioni_workflow.ed_esito_default_placeholder')"
          :show-clear="!esitoObbligatorio"
        />
      </div>
      <div class="form-field step-form__toggle">
        <label>{{ t('amministrazione.definizioni_workflow.ed_col_obbligatorio_full') }}</label>
        <ToggleSwitch v-model="form.obbligatorio"
          :invalid="campiErrati.includes('obbligatorio')"
        />
      </div>
    </div>

    <div class="step-form__actions">
      <Button
        :label="t('common.cancel')"
        severity="secondary"
        text
        @click="emit('cancel')"
      />
      <Button
        :label="t('common.save')"
        :disabled="!canSave"
        :loading="saving"
        @click="handleSave"
      />
    </div>
  </div>
</template>

<style scoped>
.step-form__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem 1rem;
}

.step-form__full {
  grid-column: 1 / -1;
}

.step-form__toggle {
  align-self: end;
}

.step-form__hint {
  color: var(--app-text-muted);
  font-size: var(--app-font-size-sm);
}

.step-form__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
</style>
