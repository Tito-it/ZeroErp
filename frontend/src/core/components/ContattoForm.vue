<script setup>
// Scopo: Building block form contatto riutilizzabile.
// Associabile a soggetto, ruolo o utility. Campi adattabili via props.
// Usa useContattoForm per stato e lookup.

import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { isEmailValid } from '../utils/validators'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'

const { t } = useI18n()

// Form reattivo del padre via defineModel: il figlio muta `form.value.xxx`
// (oggetto condiviso per riferimento), senza violare no-mutating-props.
const form = defineModel('form', { type: Object, required: true })

// Validazione real-time @blur per email e PEC
const emailInvalid = ref(false)
const pecInvalid = ref(false)

function onEmailBlur() {
  emailInvalid.value = !!form.value.email?.trim() && !isEmailValid(form.value.email)
}
function onEmailInput() {
  // Reset errore durante la digitazione — rivalidera' su blur
  if (emailInvalid.value) emailInvalid.value = false
}
function onPecBlur() {
  pecInvalid.value = !!form.value.pec?.trim() && !isEmailValid(form.value.pec)
}
function onPecInput() {
  if (pecInvalid.value) pecInvalid.value = false
}

defineProps({
  // Campi che il BACKEND indica come da correggere (envelope `error.fields`).
  // Arrivano dal padre: questo componente non chiama le API da solo.
  campiErrati: { type: Array, default: () => [] },
  tipiContatto: { type: Object, required: true },
  unitaOrganizzative: { type: Object, default: null },
  requireEmail: { type: Boolean, default: false },
  showUO: { type: Boolean, default: true },
  tipoDisabled: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  errors: { type: Array, default: () => [] }
})
</script>

<template>
  <div class="form-grid">
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('anagrafiche.contatto.tipo_contatto') }} *</label>
        <Select
          v-model="form.tipo_contatto_id"
          :options="tipiContatto.items.value"
          :loading="tipiContatto.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('anagrafiche.contatto.select_tipo_contatto')"
          :disabled="disabled || tipoDisabled"
          :invalid="errors.includes('tipo_contatto')"
        />
        <small v-if="errors.includes('tipo_contatto')" class="app-field-error">
          {{ t('validation.campo_obbligatorio') }}
        </small>
      </div>
      <div v-if="showUO && unitaOrganizzative" class="form-field">
        <label>{{ t('anagrafiche.contatto.unita_organizzativa') }}</label>
        <Select
          v-model="form.unita_organizzativa_id"
          :options="unitaOrganizzative.items.value"
          :loading="unitaOrganizzative.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('anagrafiche.contatto.select_unita_organizzativa')"
          :disabled="disabled"
          show-clear
        />
      </div>
    </div>

    <div class="form-field">
      <label>{{ t('anagrafiche.contatto.nominativo') }} *</label>
      <InputText v-model="form.nominativo" :disabled="disabled"
        :invalid="errors.includes('nominativo')" />
      <small v-if="errors.includes('nominativo')" class="app-field-error">
        {{ t('validation.campo_obbligatorio') }}
      </small>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('common.email') }}{{ requireEmail ? ' *' : '' }}</label>
        <InputText v-model="form.email" :disabled="disabled"
          :invalid="emailInvalid || errors.includes('email') || errors.includes('email_format')"
          @blur="onEmailBlur" @input="onEmailInput" />
        <small v-if="emailInvalid || errors.includes('email_format')" class="app-field-error">
          {{ t('validation.email_format') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('common.pec') }}</label>
        <InputText v-model="form.pec" :disabled="disabled"
          :invalid="pecInvalid || errors.includes('pec_format')"
          @blur="onPecBlur" @input="onPecInput" />
        <small v-if="pecInvalid || errors.includes('pec_format')" class="app-field-error">
          {{ t('validation.email_format') }}
        </small>
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('common.telefono') }}</label>
        <InputText v-model="form.telefono" :disabled="disabled" />
      </div>
      <div class="form-field">
        <label>{{ t('anagrafiche.contatto.cellulare') }}</label>
        <InputText v-model="form.cellulare" :disabled="disabled" />
      </div>
    </div>

    <div class="form-field">
      <label>{{ t('anagrafiche.contatto.note') }}</label>
      <Textarea v-model="form.note"
      :invalid="campiErrati.includes('note')" :disabled="disabled" rows="2" />
    </div>
  </div>
</template>

<!-- Stili .form-grid, .form-field, .form-grid-2col definiti in main.css -->
