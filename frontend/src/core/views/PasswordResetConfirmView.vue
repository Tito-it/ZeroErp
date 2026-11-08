<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePasswordValidation } from '../composables/usePasswordValidation'
import { extractApiError } from '../utils/apiError'
import { validaTokenResetPassword, confermaResetPassword } from '../api/password'
import LinkInformazioni from '../components/LinkInformazioni.vue'
import Password from 'primevue/password'
import Button from 'primevue/button'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { validateNewPassword } = usePasswordValidation()

const token = ref(route.params.token || '')
const newPassword = ref('')
const confirmPassword = ref('')
const errorMessage = ref('')
const successMessage = ref('')
const loading = ref(false)
const tokenValid = ref(null) // null = loading, true = ok, false = invalid

onMounted(async () => {
  if (!token.value) {
    tokenValid.value = false
    return
  }
  try {
    const res = await validaTokenResetPassword(token.value)
    tokenValid.value = res.data?.data?.valid === true
  } catch {
    tokenValid.value = false
  }
})

async function handleConfirm() {
  errorMessage.value = ''
  successMessage.value = ''

  const pwError = validateNewPassword(newPassword.value, confirmPassword.value)
  if (pwError) {
    errorMessage.value = t(pwError)
    return
  }

  loading.value = true
  try {
    await confermaResetPassword({
      token: token.value,
      newPassword: newPassword.value,
      newPasswordConfirm: confirmPassword.value,
    })
    successMessage.value = t('auth.reset_success')
    setTimeout(() => router.push('/login'), 2000)
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
    <div class="login-card">
      <img
        src="@/assets/images/logo-zeroerp.png"
        alt=""
        class="login-logo-bg"
      />

      <!-- Token in validazione -->
      <div v-if="tokenValid === null" class="login-form">
        <p class="login-subtitle">{{ t('common.loading') }}</p>
      </div>

      <!-- Token invalido -->
      <div v-else-if="!tokenValid" class="login-form">
        <div class="login-error">{{ t('auth.reset_token_invalid') }}</div>
        <router-link to="/password-reset" class="back-link">
          {{ t('auth.reset_request_btn') }}
        </router-link>
        <router-link to="/login" class="back-link">
          {{ t('auth.back_to_login') }}
        </router-link>
      </div>

      <!-- Form nuova password -->
      <form v-else @submit.prevent="handleConfirm" class="login-form">
        <!-- Esito SOPRA i campi, fuori dal flusso (login-esito--sopra), come
             nel login: sotto spingeva il pulsante fuori dal cerchio. -->
        <div v-if="errorMessage" class="login-error login-esito--sopra" role="alert">{{ errorMessage }}</div>
        <div v-if="successMessage" class="login-success login-esito--sopra">{{ successMessage }}</div>

        <div class="field">
          <Password
            id="new_password"
            v-model="newPassword"
            :disabled="loading"
            :feedback="false"
            toggleMask
            :placeholder="t('auth.new_password')"
            :aria-label="t('auth.new_password')"
            autocomplete="new-password"
            fluid
          />
        </div>

        <div class="field">
          <Password
            id="confirm_password"
            v-model="confirmPassword"
            :disabled="loading"
            :feedback="false"
            toggleMask
            :placeholder="t('auth.confirm_new_password')"
            :aria-label="t('auth.confirm_new_password')"
            autocomplete="new-password"
            fluid
          />
        </div>

        <Button
          type="submit"
          :label="t('auth.reset_confirm')"
          :loading="loading"
          :disabled="!newPassword || !confirmPassword"
          class="auth-submit-btn"
        />

        <router-link to="/login" class="back-link">
          {{ t('auth.back_to_login') }}
        </router-link>
      </form>
    </div>
    <LinkInformazioni />
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
