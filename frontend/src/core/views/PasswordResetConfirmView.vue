<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'
import LogoBrand from '../components/LogoBrand.vue'
import Password from 'primevue/password'
import Button from 'primevue/button'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

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
    const res = await api.get(`/auth/password-reset-validate/${token.value}/`)
    tokenValid.value = res.data?.data?.valid === true
  } catch {
    tokenValid.value = false
  }
})

async function handleConfirm() {
  errorMessage.value = ''
  successMessage.value = ''

  if (newPassword.value.length < 8) {
    errorMessage.value = t('auth.password_too_short')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = t('auth.password_mismatch')
    return
  }

  loading.value = true
  try {
    await api.post('/auth/password-reset-confirm/', {
      token: token.value,
      new_password: newPassword.value,
      new_password_confirm: confirmPassword.value,
    })
    successMessage.value = t('auth.reset_success')
    setTimeout(() => router.push('/login'), 2000)
  } catch (err) {
    const msg = err?.response?.data?.error?.message || t('auth.login_error')
    errorMessage.value = msg
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <img src="@/assets/images/zeroerp-doodle.jpeg" alt="" class="login-bg" />
    <div class="login-card">
      <div class="login-logo">
        <LogoBrand size="large" />
      </div>

      <h2 class="login-title">{{ t('auth.reset_confirm') }}</h2>

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
        <div class="field">
          <label for="new_password">{{ t('auth.new_password') }}</label>
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
          :label="t('auth.reset_confirm')"
          :loading="loading"
          :disabled="!newPassword || !confirmPassword"
          fluid
        />

        <router-link to="/login" class="back-link">
          {{ t('auth.back_to_login') }}
        </router-link>
      </form>
    </div>
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
