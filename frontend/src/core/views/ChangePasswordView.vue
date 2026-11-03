<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/auth'
import { usePasswordValidation } from '../composables/usePasswordValidation'
import { seSessioneChiusaDalFreno } from '../uscitaSessione'
import { extractApiError } from '../utils/apiError'
import LinkInformazioni from '../components/LinkInformazioni.vue'
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

function tornaAllApplicazione() {
  router.push(route.query.redirect || '/')
}

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
    await auth.cambiaPassword({
      oldPassword: oldPassword.value,
      newPassword: newPassword.value,
      newPasswordConfirm: confirmPassword.value,
    })
    successMessage.value = t('auth.password_changed_success')
    setTimeout(tornaAllApplicazione, 1500)
  } catch (err) {
    // Il freno sulla password chiude la sessione: si va al login col motivo.
    if (!seSessioneChiusaDalFreno(err)) {
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
    <div class="login-card login-card--large">
      <img
        src="@/assets/images/logo-zeroerp.png"
        alt=""
        class="login-logo-bg"
      />

      <form @submit.prevent="handleChangePassword" class="login-form login-form--wide">
        <!-- Esito SOPRA il form, fuori dal flusso (login-esito--sopra), come
             nel login: sotto spingeva il pulsante fuori dal cerchio. Il
             sottotitolo sta DENTRO il form, cosi' l'esito sale sopra di lui
             invece di coprirlo. -->
        <div v-if="errorMessage" class="login-error login-esito--sopra" role="alert">{{ errorMessage }}</div>
        <div v-if="successMessage" class="login-success login-esito--sopra">{{ successMessage }}</div>

        <p v-if="auth.mustChangePassword" class="login-subtitle">
          {{ t('auth.password_change_required') }}
        </p>

        <div class="field">
          <Password
            id="old_password"
            v-model="oldPassword"
            :disabled="loading"
            :feedback="false"
            toggleMask
            :placeholder="t('auth.old_password')"
            :aria-label="t('auth.old_password')"
            autocomplete="current-password"
            fluid
          />
        </div>

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
          :label="t('auth.change_password')"
          :loading="loading"
          :disabled="!oldPassword || !newPassword || !confirmPassword"
          class="auth-submit-btn"
        />

        <!-- Arrivati di propria iniziativa (scheda utente) si torna indietro;
             con l'obbligo pendente no: il guard riporterebbe qui. -->
        <a v-if="!auth.mustChangePassword" href="#" class="back-link" @click.prevent="tornaAllApplicazione">
          {{ t('auth.account.torna') }}
        </a>
      </form>
    </div>
    <LinkInformazioni />
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
