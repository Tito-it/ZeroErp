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
          fluid
        />
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--app-content-bg);
}

.login-card {
  width: 100%;
  max-width: 380px;
  padding: 2.5rem 2rem;
  border-radius: var(--app-login-card-radius);
  background: var(--app-login-card-bg);
  border: 1px solid var(--app-login-card-border);
}

.login-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 2rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.field label {
  font-size: var(--app-font-size-sm);
  font-weight: 500;
  color: var(--p-text-muted-color);
}

.login-error {
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  background: var(--app-login-error-bg);
  color: var(--app-login-error-color);
  font-size: var(--app-font-size-sm);
  text-align: center;
}
</style>
