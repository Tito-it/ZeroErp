<script setup>
// Scopo: Pagina pubblica attivazione account shop customer (B1 §13.7).
// Token via link email (/attivazione-shop/:token). Simmetrica ad
// AttivazionePortaleView con due flow:
// - INVITO (token_type=INVITO_SHOP, requires_password=true): form
//   con scelta password (primo accesso shop di un utente email-nuovo).
// - CROSS (token_type=ATTIVAZIONE_SHOP_CROSS, requires_password=false):
//   conferma one-click — l'utente ha gia' una password (operatore o
//   altra veste portale), qui attiva solo la nuova veste shop.
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePasswordValidation } from '../../core/composables/usePasswordValidation'
import { extractApiError, extractApiErrorCode } from '../../core/utils/apiError'
import { validateShopToken, attivaShop } from '../api/shopAuth'
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

// Contract: `token_type` + `requires_password` letti da validate.
// `requires_password=true` -> INVITO (form password), `false` -> CROSS
// (one-click). Fallback conservativo a `true` in assenza del campo
// (BE pre-§13.7): mantiene il comportamento storico del flow INVITO.
const tokenType = ref(null)
const requiresPassword = ref(true)

const isCrossFlow = computed(() => !requiresPassword.value)

onMounted(async () => {
  if (!token.value) {
    tokenValid.value = false
    return
  }
  try {
    const res = await validateShopToken(token.value)
    const data = res.data?.data || {}
    tokenValid.value = data.valid === true
    tokenType.value = data.token_type ?? null
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
    await attivaShop({
      token: token.value,
      // In flow CROSS `newPassword` e' vuoto: `attivaShop` omette i
      // campi password dal payload (no rumore semantico BE-side).
      newPassword: requiresPassword.value ? newPassword.value : '',
      newPasswordConfirm: requiresPassword.value ? confirmPassword.value : '',
    })
    successMessage.value = t(
      isCrossFlow.value
        ? 'shop.activation_cross_success'
        : 'shop.activation_success'
    )
    // Redirect al login con canale shop pre-selezionato (lo store auth
    // gia' persiste loginChannel; qui assumiamo che il LoginView sappia
    // di mostrare il canale shop selezionato). Il timeout consente di
    // leggere il messaggio di successo prima del redirect.
    setTimeout(() => router.push('/login'), 2000)
  } catch (err) {
    const code = extractApiErrorCode(err)
    if (code === 'E_ATTIVAZIONE_SHOP' || code === 'E_TOKEN') {
      errorMessage.value = t('shop.activation_token_invalid')
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

      <h2 class="login-title">{{ t('shop.activation_title') }}</h2>

      <!-- Token in validazione -->
      <div v-if="tokenValid === null" class="login-form">
        <p class="login-subtitle">{{ t('common.loading') }}</p>
      </div>

      <!-- Token invalido -->
      <div v-else-if="tokenValid === false" class="login-form">
        <div class="login-error">{{ t('shop.activation_token_invalid') }}</div>
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
        <p class="login-subtitle">{{ t('shop.activation_cross_welcome') }}</p>

        <div v-if="errorMessage" class="login-error">{{ errorMessage }}</div>
        <div v-if="successMessage" class="login-success">{{ successMessage }}</div>

        <Button
          type="submit"
          :label="t('shop.activate_cross_btn')"
          :loading="loading"
          class="auth-submit-btn"
        />
      </form>

      <!-- Flow INVITO: form scelta password -->
      <form v-else @submit.prevent="handleActivation" class="login-form">
        <p class="login-subtitle">{{ t('shop.activation_welcome') }}</p>

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
          :label="t('shop.activate_btn')"
          :loading="loading"
          :disabled="!newPassword || !confirmPassword"
          class="auth-submit-btn"
        />
      </form>
    </div>
  </div>
</template>

<!-- CSS condiviso con AttivazionePortaleView via auth-pages.css -->
