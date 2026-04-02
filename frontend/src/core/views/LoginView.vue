<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/auth'
import LogoBrand from '../components/LogoBrand.vue'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const errorMessage = ref('')
const loading = ref(false)

// Mappa codici errore DB → chiavi i18n per messaggi login specifici
const ERROR_CODE_MAP = {
  E_UTENTE_DISABILITATO: 'auth.account_disabled',
  E_UTENTE_NON_ATTIVO: 'auth.account_not_active',
  E_UTENTE_SCADUTO: 'auth.account_expired'
}

function resolveLoginError(err) {
  const status = err?.response?.status
  // Throttle IP: troppi tentativi
  if (status === 429) return t('auth.too_many_attempts')
  const data = err?.response?.data
  const code = data?.error?.code
  // Blocco per utente: mostra minuti rimanenti dal messaggio DB
  if (code === 'E_UTENTE_BLOCCATO') {
    const msg = data?.error?.detail || data?.error?.message || ''
    return msg || t('auth.account_locked')
  }
  const i18nKey = code && ERROR_CODE_MAP[code]
  if (i18nKey) return t(i18nKey)
  // Token request fallito (401) → credenziali errate; altrimenti generico
  if (!status || status === 401) return t('auth.login_error')
  return t('auth.access_denied')
}

async function handleLogin() {
  errorMessage.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    // Se deve cambiare password, redirect forzato
    if (auth.mustChangePassword) {
      router.push('/change-password')
      return
    }
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (err) {
    errorMessage.value = resolveLoginError(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <img
      src="@/assets/images/zeroerp-doodle.jpeg"
      alt=""
      class="login-bg"
    />
    <div class="login-card">
      <div class="login-logo">
        <LogoBrand size="large" />
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="field">
          <label for="username">{{ t('auth.username') }}</label>
          <InputText
            id="username"
            v-model="username"
            :disabled="loading"
            autocomplete="username"
            fluid
          />
        </div>

        <div class="field">
          <label for="password">{{ t('auth.password') }}</label>
          <Password
            id="password"
            v-model="password"
            :disabled="loading"
            :feedback="false"
            toggleMask
            autocomplete="current-password"
            fluid
          />
        </div>

        <div v-if="errorMessage" class="login-error">
          {{ errorMessage }}
        </div>

        <Button
          type="submit"
          :label="t('auth.login')"
          :loading="loading"
          :disabled="!username || !password"
          class="auth-submit-btn"
        />

        <router-link to="/password-reset" class="forgot-link">
          {{ t('auth.forgot_password') }}
        </router-link>
      </form>
    </div>
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
