<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/auth'
import { CANALE_LOGIN } from '../constants'
// ChannelSelector importato ma non montato: l'UI attuale e' per soli
// operatori interni (canale ADMIN forzato). Importazione conservata per
// riuso futuro (pagine dedicate portale/shop).
// import ChannelSelector from '../components/ChannelSelector.vue'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
// UI attuale: solo operatori interni. Canale forzato ad ADMIN,
// ignoriamo `auth.loginChannel` persistito (se un utente aveva scelto
// PORTALE/SHOP in passato, qui lo riportiamo a ADMIN). Store e API
// multi-canale restano attivi per future pagine dedicate portale/shop.
const canale = ref(CANALE_LOGIN.ADMIN.key)
const errorMessage = ref('')
const loading = ref(false)

// Mappa codici errore DB → chiavi i18n per messaggi login specifici.
// `E_VESTE_NON_ATTIVA` (§8.3.2) e' il caso "account valido ma senza
// accesso al canale richiesto": mostriamo un messaggio dedicato e
// generico (niente enumeration di quali canali sono attivi).
const ERROR_CODE_MAP = {
  E_UTENTE_DISABILITATO: 'auth.account_disabled',
  E_UTENTE_NON_ATTIVO: 'auth.account_not_active',
  E_UTENTE_SCADUTO: 'auth.account_expired',
  E_VESTE_NON_ATTIVA: 'auth.veste_non_attiva'
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

// Pre-popolazione errorMessage in base a `reason` query (es. session_expired
// passato da api.js → redirectToLogin quando il refresh fallisce o da router
// guard quando i token sono scaduti). Mantiene UX coerente: l'utente vede
// subito perche' e' tornato sul login.
onMounted(() => {
  const reason = route.query.reason
  if (reason === 'session_expired') {
    errorMessage.value = t('auth.session_expired')
  }
})

async function handleLogin() {
  errorMessage.value = ''
  loading.value = true
  try {
    // §8.5.2: la store usa `canale` per scegliere l'endpoint token
    // (/admin/token/ | /portale/token/ | /shop/token/). Default ADMIN.
    await auth.login(username.value, password.value, canale.value)
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
      <img
        src="@/assets/images/logo-zeroerp.png"
        alt=""
        class="login-logo-bg"
      />

      <form @submit.prevent="handleLogin" class="login-form">
        <!-- ChannelSelector nascosto: in questa fase il login e' solo per
             operatori interni. Il canale resta forzato ad ADMIN (store +
             router + api multi-canale restano attivi per future pagine
             dedicate portale/shop). Per riabilitare: reintrodurre il
             componente con v-model="canale". -->
        <!-- <ChannelSelector v-model="canale" :disabled="loading" /> -->

        <div class="field">
          <InputText
            id="username"
            v-model="username"
            :disabled="loading"
            :placeholder="t('auth.username')"
            :aria-label="t('auth.username')"
            autocomplete="username"
            fluid
          />
        </div>

        <div class="field">
          <Password
            id="password"
            v-model="password"
            :disabled="loading"
            :feedback="false"
            toggleMask
            :placeholder="t('auth.password')"
            :aria-label="t('auth.password')"
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
