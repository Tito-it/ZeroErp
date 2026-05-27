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
        <label>{{ t('contatto.tipo_contatto') }} *</label>
        <Select
          v-model="form.tipo_contatto_id"
          :options="tipiContatto.items.value"
          :loading="tipiContatto.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('contatto.select_tipo_contatto')"
          :disabled="disabled || tipoDisabled"
          :invalid="errors.includes('tipo_contatto')"
          class="w-full"
        />
        <small v-if="errors.includes('tipo_contatto')" class="app-field-error">
          {{ t('validation.campo_obbligatorio') }}
        </small>
      </div>
      <div v-if="showUO && unitaOrganizzative" class="form-field">
        <label>{{ t('contatto.unita_organizzativa') }}</label>
        <Select
          v-model="form.unita_organizzativa_id"
          :options="unitaOrganizzative.items.value"
          :loading="unitaOrganizzative.loading.value"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('contatto.select_unita_organizzativa')"
          :disabled="disabled"
          show-clear
          class="w-full"
        />
      </div>
    </div>

    <div class="form-field">
      <label>{{ t('contatto.nominativo') }} *</label>
      <InputText v-model="form.nominativo" :disabled="disabled" class="w-full"
        :invalid="errors.includes('nominativo')" />
      <small v-if="errors.includes('nominativo')" class="app-field-error">
        {{ t('validation.campo_obbligatorio') }}
      </small>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('common.email') }}{{ requireEmail ? ' *' : '' }}</label>
        <InputText v-model="form.email" :disabled="disabled" class="w-full"
          :invalid="emailInvalid || errors.includes('email') || errors.includes('email_format')"
          @blur="onEmailBlur" @input="onEmailInput" />
        <small v-if="emailInvalid || errors.includes('email_format')" class="app-field-error">
          {{ t('validation.email_format') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('common.pec') }}</label>
        <InputText v-model="form.pec" :disabled="disabled" class="w-full"
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
        <InputText v-model="form.telefono" :disabled="disabled" class="w-full" />
      </div>
      <div class="form-field">
        <label>{{ t('contatto.cellulare') }}</label>
        <InputText v-model="form.cellulare" :disabled="disabled" class="w-full" />
      </div>
    </div>

    <div class="form-field">
      <label>{{ t('contatto.note') }}</label>
      <Textarea v-model="form.note" :disabled="disabled" rows="2" class="w-full" />
    </div>
  </div>
</template>

<!-- Stili .form-grid, .form-field, .form-grid-2col definiti in main.css -->
