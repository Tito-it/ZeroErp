<script setup>
// Scopo: Pagina pubblica attivazione account portale. Il token arriva via
// link email (/attivazione-portale/:token). Layout simmetrico ad
// AttivazioneView per operatore, ma con branching §8.4.2 per due flow:
// - INVITO (token_type=INVITO_PORTALE, requires_password=true): form
//   con scelta password (primo accesso di un utente email-nuovo).
// - CROSS (token_type=ATTIVAZIONE_PORTALE_CROSS, requires_password=false):
//   conferma one-click — l'utente ha gia' una password sulla veste
//   operatore o altra veste portale, qui attiva solo la nuova veste.
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePasswordValidation } from '../../core/composables/usePasswordValidation'
import { extractApiError, extractApiErrorCode } from '../../core/utils/apiError'
import { validateInvitoPortaleToken, attivaPortale } from '../api/portaleAuth'
import LogoBrand from '../../core/components/LogoBrand.vue'
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

// §8.4.2 contract: `token_type` + `requires_password` letti da validate.
// `requires_password=true` → INVITO (form password), `false` → CROSS
// (one-click). Fallback conservativo a `true` in assenza del campo
// (BE pre-§8.4.2): mantiene il comportamento storico.
const tokenType = ref(null)
const requiresPassword = ref(true)

const isCrossFlow = computed(() => !requiresPassword.value)

onMounted(async () => {
  if (!token.value) {
    tokenValid.value = false
    return
  }
  try {
    const res = await validateInvitoPortaleToken(token.value)
    const data = res.data?.data || {}
    tokenValid.value = data.valid === true
    tokenType.value = data.token_type ?? null
    // Se il BE risponde senza `requires_password` (es. BE legacy),
    // assumiamo true per sicurezza — mostriamo comunque il form.
    requiresPassword.value = data.requires_password !== false
  } catch {
    tokenValid.value = false
  }
})

async function handleActivation() {
  errorMessage.value = ''
  successMessage.value = ''

  // Valida la password solo nel flow INVITO.
  if (requiresPassword.value) {
    const pwError = validateNewPassword(newPassword.value, confirmPassword.value)
    if (pwError) {
      errorMessage.value = t(pwError)
      return
    }
  }

  loading.value = true
  try {
    await attivaPortale({
      token: token.value,
      // In flow CROSS `newPassword` e' vuoto: `attivaPortale` omette
      // i campi password dal payload (no rumore semantico BE-side).
      newPassword: requiresPassword.value ? newPassword.value : '',
      newPasswordConfirm: requiresPassword.value ? confirmPassword.value : '',
    })
    successMessage.value = t(
      isCrossFlow.value
        ? 'portale.activation_cross_success'
        : 'portale.activation_success'
    )
    setTimeout(() => router.push('/login'), 2000)
  } catch (err) {
    const code = extractApiErrorCode(err)
    if (code === 'E_ATTIVAZIONE_PORTALE' || code === 'E_TOKEN') {
      errorMessage.value = t('portale.activation_token_invalid')
      tokenValid.value = false
    } else {
      errorMessage.value = extractApiError(err, t('auth.login_error'))
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

      <h2 class="login-title">{{ t('portale.activation_title') }}</h2>

      <!-- Token in validazione -->
      <div v-if="tokenValid === null" class="login-form">
        <p class="login-subtitle">{{ t('common.loading') }}</p>
      </div>

      <!-- Token invalido -->
      <div v-else-if="tokenValid === false" class="login-form">
        <div class="login-error">{{ t('portale.activation_token_invalid') }}</div>
        <router-link to="/login" class="back-link">
          {{ t('auth.back_to_login') }}
        </router-link>
      </div>

      <!-- Flow CROSS: one-click, no password -->
      <form
        v-else-if="isCrossFlow"
        @submit.prevent="handleActivation"
        class="login-form"
      >
        <p class="login-subtitle">{{ t('portale.activation_cross_welcome') }}</p>

        <div v-if="errorMessage" class="login-error">{{ errorMessage }}</div>
        <div v-if="successMessage" class="login-success">{{ successMessage }}</div>

        <Button
          type="submit"
          :label="t('portale.activate_cross_btn')"
          :loading="loading"
          class="auth-submit-btn"
        />
      </form>

      <!-- Flow INVITO: form scelta password -->
      <form v-else @submit.prevent="handleActivation" class="login-form">
        <p class="login-subtitle">{{ t('portale.activation_welcome') }}</p>

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
          :label="t('portale.activate_btn')"
          :loading="loading"
          :disabled="!newPassword || !confirmPassword"
          class="auth-submit-btn"
        />
      </form>
    </div>
  </div>
</template>

<!-- CSS condiviso con /core/views/AttivazioneView.vue via auth-pages.css -->
