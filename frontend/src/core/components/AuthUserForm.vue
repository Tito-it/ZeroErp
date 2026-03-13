<script setup>
// Scopo: Building block form per credenziali utente (username, email, password).
// Usato nella creazione operatore, admin, e qualsiasi utente con auth.

import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'

const { t } = useI18n()

defineProps({
  form: { type: Object, required: true },
  passwordMatch: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  showPassword: { type: Boolean, default: true }
})
</script>

<template>
  <div class="auth-form">
    <div class="field">
      <label>{{ t('common.username') }} *</label>
      <InputText v-model="form.username" :disabled="disabled" class="w-full" />
    </div>
    <div class="field">
      <label>{{ t('common.email') }} *</label>
      <InputText v-model="form.email" type="email" :disabled="disabled" class="w-full" />
    </div>
    <template v-if="showPassword">
      <div class="field">
        <label>{{ t('common.password') }} *</label>
        <Password v-model="form.password" :disabled="disabled"
          :feedback="false" toggleMask class="w-full" />
      </div>
      <div class="field">
        <label>{{ t('common.password_confirm') }} *</label>
        <Password v-model="form.password_confirm" :disabled="disabled"
          :feedback="false" toggleMask class="w-full"
          :invalid="!passwordMatch" />
        <small v-if="!passwordMatch" class="p-error">
          {{ t('common.password_mismatch') }}
        </small>
      </div>
    </template>
  </div>
</template>

<style scoped>
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.field label {
  font-weight: 600;
  font-size: 0.875rem;
}
</style>
