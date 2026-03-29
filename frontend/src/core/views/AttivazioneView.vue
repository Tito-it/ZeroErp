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
  // Valida token invito (riuso endpoint validate con tipo diverso — il backend
  // accetta qualsiasi tipo su validate, controlla il DB)
  // Per semplicita' assumiamo il token valido se presente (il backend verifichera' al submit)
  tokenValid.value = true
})

async function handleActivation() {
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
    await api.post('/auth/attivazione/', {
      token: token.value,
      new_password: newPassword.value,
      new_password_confirm: confirmPassword.value,
    })
    successMessage.value = t('auth.activation_success')
    setTimeout(() => router.push('/login'), 2000)
  } catch (err) {
    const code = err?.response?.data?.error?.code
    if (code === 'E_TOKEN') {
      errorMessage.value = t('auth.activation_token_invalid')
      tokenValid.value = false
    } else {
      errorMessage.value = err?.response?.data?.error?.message || t('auth.login_error')
    }
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

      <h2 class="login-title">{{ t('auth.activation') }}</h2>

      <!-- Token invalido -->
      <div v-if="tokenValid === false" class="login-form">
        <div class="login-error">{{ t('auth.activation_token_invalid') }}</div>
        <router-link to="/login" class="back-link">
          {{ t('auth.back_to_login') }}
        </router-link>
      </div>

      <!-- Form attivazione -->
      <form v-else @submit.prevent="handleActivation" class="login-form">
        <p class="login-subtitle">{{ t('auth.activation_welcome') }}</p>

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
          :label="t('auth.activate_btn')"
          :loading="loading"
          :disabled="!newPassword || !confirmPassword"
          fluid
        />
      </form>
    </div>
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
