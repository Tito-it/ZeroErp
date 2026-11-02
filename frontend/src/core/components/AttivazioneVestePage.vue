<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Pagina pubblica di attivazione di una veste (operatore, portale,
// shop), scritta una volta per tutte le porte: le tre pagine erano copie
// (portale e shop identiche a meno dei nomi, l'operatore senza il flusso con
// un clic). Il token arriva dal link dell'email. Due forme, decise dal BE
// sulla credenziale (`requires_password` della verifica):
// - con password: la persona la sceglie (credenziale senza password vera);
// - con un clic: la persona ha gia' una password, qui accende solo la veste.
// ⭐ Dopo un errore si RI-VERIFICA il token invece di dedurre dal codice: il
// codice d'attivazione copre anche la password rifiutata dalla policy, e
// prima quel caso diceva «link non valido» e toglieva il form.
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePasswordValidation } from '../composables/usePasswordValidation'
import { extractApiError } from '../utils/apiError'
import { validaTokenAttivazione, confermaAttivazione } from '../api/attivazioneVeste'
import Password from 'primevue/password'
import Button from 'primevue/button'

const props = defineProps({
  // Una voce di PORTE_ATTIVAZIONE (core/api/attivazioneVeste.js).
  porta: { type: Object, required: true }
})

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
const tokenValid = ref(null) // null = in verifica, true = ok, false = non valido
// In assenza del campo si chiede la password: mostrare un form in piu' e'
// innocuo, saltarlo no.
const requiresPassword = ref(true)

const isCrossFlow = computed(() => !requiresPassword.value)
// Dopo il successo il token e' consumato: un secondo clic ri-verificherebbe
// e sostituirebbe l'esito con «link non valido».
const attivata = computed(() => !!successMessage.value)
// Scopo: Chiave i18n della sezione della porta.
const k = (chiave) => `${props.porta.i18n}.${chiave}`

// Scopo: Verifica il token e fissa la forma della pagina.
async function verificaToken() {
  if (!token.value) {
    tokenValid.value = false
    return
  }
  try {
    const res = await validaTokenAttivazione(props.porta, token.value)
    const data = res.data?.data || {}
    tokenValid.value = data.valid === true
    requiresPassword.value = data.requires_password !== false
  } catch {
    tokenValid.value = false
  }
}

onMounted(verificaToken)

async function handleActivation() {
  errorMessage.value = ''
  successMessage.value = ''

  if (requiresPassword.value) {
    const pwError = validateNewPassword(newPassword.value, confirmPassword.value)
    if (pwError) {
      errorMessage.value = t(pwError)
      return
    }
  }

  loading.value = true
  try {
    await confermaAttivazione(props.porta, {
      token: token.value,
      newPassword: requiresPassword.value ? newPassword.value : '',
      newPasswordConfirm: requiresPassword.value ? confirmPassword.value : ''
    })
    successMessage.value = t(k(isCrossFlow.value ? 'activation_cross_success' : 'activation_success'))
    setTimeout(() => router.push('/login'), 2000)
  } catch (err) {
    // Il token vale ancora? Se no, la pagina lo dice e toglie il form; se
    // si', l'errore e' dell'input (es. password rifiutata) e il form resta.
    await verificaToken()
    if (tokenValid.value) {
      errorMessage.value = extractApiError(err, t('common.error'))
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

      <!-- Token in verifica -->
      <div v-if="tokenValid === null" class="login-form">
        <p class="login-subtitle">{{ t('common.loading') }}</p>
      </div>

      <!-- Token non valido -->
      <div v-else-if="tokenValid === false" class="login-form">
        <div class="login-error">{{ t(k('activation_token_invalid')) }}</div>
        <router-link to="/login" class="back-link">
          {{ t('auth.back_to_login') }}
        </router-link>
      </div>

      <!-- Con un clic: la password c'e' gia' -->
      <form
        v-else-if="isCrossFlow"
        @submit.prevent="handleActivation"
        class="login-form"
      >
        <!-- Esito SOPRA il form, fuori dal flusso (login-esito--sopra), come
             nel login: sotto spingeva il pulsante fuori dal cerchio. -->
        <div v-if="errorMessage" class="login-error login-esito--sopra" role="alert">{{ errorMessage }}</div>
        <div v-if="successMessage" class="login-success login-esito--sopra">{{ successMessage }}</div>

        <p class="login-subtitle">{{ t(k('activation_cross_welcome')) }}</p>

        <Button
          type="submit"
          :label="t(k('activate_cross_btn'))"
          :loading="loading"
          :disabled="attivata"
          class="auth-submit-btn"
        />
      </form>

      <!-- Con password: la persona la sceglie -->
      <form v-else @submit.prevent="handleActivation" class="login-form">
        <!-- Esito SOPRA il form, fuori dal flusso (login-esito--sopra), come
             nel login: sotto spingeva il pulsante fuori dal cerchio. -->
        <div v-if="errorMessage" class="login-error login-esito--sopra" role="alert">{{ errorMessage }}</div>
        <div v-if="successMessage" class="login-success login-esito--sopra">{{ successMessage }}</div>

        <p class="login-subtitle">{{ t(k('activation_welcome')) }}</p>

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
          :label="t(k('activate_btn'))"
          :loading="loading"
          :disabled="attivata || !newPassword || !confirmPassword"
          class="auth-submit-btn"
        />
      </form>
    </div>
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
