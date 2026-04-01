<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/auth'
import { usePasswordValidation } from '../composables/usePasswordValidation'
import { extractApiError } from '../utils/apiError'
import api from '../api'
import LogoBrand from '../components/LogoBrand.vue'
import Password from 'primevue/password'
import Button from 'primevue/button'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { validateNewPassword } = usePasswordValidation()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const loading = ref(false)

async function handleChangePassword() {
  errorMessage.value = ''
  successMessage.value = ''

  const pwError = validateNewPassword(newPassword.value, confirmPassword.value)
  if (pwError) {
    errorMessage.value = t(pwError)
    return
  }

  loading.value = true
  try {
    const response = await api.post('/auth/change-password/', {
      old_password: oldPassword.value,
      new_password: newPassword.value,
      new_password_confirm: confirmPassword.value,
    })
    // Aggiorna token nello store
    const data = response.data?.data || response.data
    if (data.access && data.refresh) {
      auth.setTokens(data.access, data.refresh)
      auth.passwordChangeRequired = false
      // Ricarica profilo per aggiornare deve_cambiare_password nel profilo
      try { await auth.fetchProfile() } catch { /* non blocca il flusso */ }
    }
    successMessage.value = t('auth.password_changed_success')
    setTimeout(() => router.push(route.query.redirect || '/'), 1500)
  } catch (err) {
    errorMessage.value = extractApiError(err, t('auth.login_error'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <img src="@/assets/images/zeroerp-doodle.jpeg" alt="" class="login-bg" />
    <div class="login-card login-card--large">
      <div class="login-logo">
        <LogoBrand size="large" />
      </div>

      <h2 class="login-title">{{ t('auth.change_password') }}</h2>
      <p v-if="auth.mustChangePassword" class="login-subtitle">
        {{ t('auth.password_change_required') }}
      </p>

      <form @submit.prevent="handleChangePassword" class="login-form login-form--wide">
        <div class="field">
          <label for="old_password">{{ t('auth.old_password') }}</label>
          <Password
            id="old_password"
            v-model="oldPassword"
            :disabled="loading"
            :feedback="false"
            toggleMask
            autocomplete="current-password"
            fluid
          />
        </div>

        <div class="field">
          <label for="new_password">{{ t('auth.new_password') }}
            <i class="pi pi-info-circle password-info-icon" v-tooltip.right="t('auth.password_hint')" />
          </label>
          <Password
            id="new_password"
            v-model="newPassword"
            :disabled="loading"
            :feedback="false"
            toggleMask
            autocomplete="new-password"
            fluid
          />
        </div>

        <div class="field">
          <label for="confirm_password">{{ t('auth.confirm_new_password') }}</label>
          <Password
            id="confirm_password"
            v-model="confirmPassword"
            :disabled="loading"
            :feedback="false"
            toggleMask
            autocomplete="new-password"
            fluid
          />
        </div>

        <div v-if="errorMessage" class="login-error">{{ errorMessage }}</div>
        <div v-if="successMessage" class="login-success">{{ successMessage }}</div>

        <Button
          type="submit"
          :label="t('auth.change_password')"
          :loading="loading"
          :disabled="!oldPassword || !newPassword || !confirmPassword"
          class="auth-submit-btn"
        />
      </form>
    </div>
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
