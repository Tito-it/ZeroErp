<script setup>
// Scopo: Building block form per credenziali utente (username, email, password).
// Usato nella creazione operatore, admin, e qualsiasi utente con auth.

import { useI18n } from 'vue-i18n'
import { ref, watch } from 'vue'
import { isEmailValid } from '../utils/validators'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'

const { t } = useI18n()
const emailInvalid = ref(false)

// Form reattivo del padre via defineModel: il figlio muta `form.value.xxx`
// (oggetto condiviso per riferimento), senza violare no-mutating-props.
const form = defineModel('form', { type: Object, required: true })
defineProps({
  passwordMatch: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  showPassword: { type: Boolean, default: true }
})

watch(
  () => form.value.email,
  (value) => {
    if (!value) emailInvalid.value = false
  }
)

// Scopo: Applica il validator email condiviso come feedback UX sul campo auth.
function validateEmail(form) {
  emailInvalid.value = !!form.email?.trim() && !isEmailValid(form.email)
}

// Scopo: Rimuove lo stato errore mentre l'utente corregge il campo.
function clearEmailInvalid() {
  if (emailInvalid.value) emailInvalid.value = false
}
</script>

<template>
  <div class="form-grid">
    <div class="form-field">
      <label>{{ t('common.username') }} *</label>
      <InputText v-model="form.username" :disabled="disabled" />
    </div>
    <div class="form-field">
      <label>{{ t('common.email') }} *</label>
      <InputText v-model="form.email" type="email" :disabled="disabled"
        :invalid="emailInvalid"
        @blur="validateEmail(form)"
        @input="clearEmailInvalid" />
      <small v-if="emailInvalid" class="app-field-error">
        {{ t('validation.email_format') }}
      </small>
    </div>
    <div v-if="showPassword" class="form-row-inline">
      <div class="form-field" style="flex: 1;">
        <label>{{ t('common.password') }} *</label>
        <Password v-model="form.password" :disabled="disabled"
          :feedback="false" toggleMask />
      </div>
      <div class="form-field" style="flex: 1;">
        <label>{{ t('common.password_confirm') }} *</label>
        <Password v-model="form.password_confirm" :disabled="disabled"
          :feedback="false" toggleMask 
          :invalid="!passwordMatch" />
        <small v-if="!passwordMatch" class="p-error">
          {{ t('common.password_mismatch') }}
        </small>
      </div>
    </div>
  </div>
</template>

<!-- Stili .form-grid e .form-field definiti in main.css -->
