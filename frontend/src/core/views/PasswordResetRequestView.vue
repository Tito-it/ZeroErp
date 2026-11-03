<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/auth'
import { resolveCanaleLogin } from '../constants'
import { extractApiError } from '../utils/apiError'
import { richiediResetPassword } from '../api/password'
import LinkInformazioni from '../components/LinkInformazioni.vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

const { t } = useI18n()
const auth = useAuthStore()

// Nome utente o email (L-4, D-9): chi entra dal portale o dallo shop
// conosce la sua email, non un nome utente. Lo distingue il backend.
const identificativo = ref('')
const sent = ref(false)
// Cio' che e' stato chiesto davvero: il messaggio di esito parla di
// «email» o di «utente» secondo cio' che la persona ha digitato. Non dice
// niente su chi esiste: le due frasi sono condizionali allo stesso modo.
const chiestoConEmail = ref(false)
const errorMessage = ref('')
const loading = ref(false)

// L'etichetta segue la chiave d'ingresso dell'ultimo canale di login
// (`campoIngresso`, L-4): sulla porta dell'email si chiede l'email; sulla
// porta admin il nome utente o l'email, che il backend accetta entrambi.
const etichettaIdentificativo = computed(() =>
  resolveCanaleLogin(auth.loginChannel).campoIngresso === 'email'
    ? t('auth.reset_email_label')
    : t('auth.reset_identificativo_label')
)
const messaggioInviato = computed(() =>
  chiestoConEmail.value ? t('auth.reset_email_sent') : t('auth.reset_username_sent')
)

async function handleRequest() {
  errorMessage.value = ''
  loading.value = true
  try {
    await richiediResetPassword(identificativo.value)
    // Stessa regola del backend: con una «@» si cerca prima l'email.
    chiestoConEmail.value = identificativo.value.includes('@')
    sent.value = true
  } catch (err) {
    const status = err?.response?.status
    if (status === 429) {
      errorMessage.value = t('auth.too_many_attempts')
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
      <img
        src="@/assets/images/logo-zeroerp.png"
        alt=""
        class="login-logo-bg"
      />

      <template v-if="!sent">
        <form @submit.prevent="handleRequest" class="login-form">
          <!-- Errore SOPRA il campo, fuori dal flusso, come nel login. -->
          <div v-if="errorMessage" class="login-error login-esito--sopra" role="alert">{{ errorMessage }}</div>

          <div class="field">
            <InputText
              id="identificativo"
              v-model="identificativo"
              :disabled="loading"
              :placeholder="etichettaIdentificativo"
              :aria-label="etichettaIdentificativo"
              autocomplete="username"
              fluid
            />
          </div>

          <Button
            type="submit"
            :label="t('auth.reset_request_btn')"
            :loading="loading"
            :disabled="!identificativo"
            class="auth-submit-btn"
          />

          <router-link to="/login" class="back-link">
            {{ t('auth.back_to_login') }}
          </router-link>
        </form>
      </template>

      <template v-else>
        <div class="login-form">
          <div class="login-success">{{ messaggioInviato }}</div>
          <router-link to="/login" class="back-link">
            {{ t('auth.back_to_login') }}
          </router-link>
        </div>
      </template>
    </div>
    <LinkInformazioni />
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
