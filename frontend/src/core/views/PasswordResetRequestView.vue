<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { extractApiError } from '../utils/apiError'
import api from '../api'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

const { t } = useI18n()

const username = ref('')
const sent = ref(false)
const errorMessage = ref('')
const loading = ref(false)

async function handleRequest() {
  errorMessage.value = ''
  loading.value = true
  try {
    await api.post('/auth/password-reset-request/', { username: username.value })
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
          <div class="field">
            <InputText
              id="username"
              v-model="username"
              :disabled="loading"
              :placeholder="t('auth.reset_username_label')"
              :aria-label="t('auth.reset_username_label')"
              autocomplete="username"
              fluid
            />
          </div>

          <div v-if="errorMessage" class="login-error">{{ errorMessage }}</div>

          <Button
            type="submit"
            :label="t('auth.reset_request_btn')"
            :loading="loading"
            :disabled="!username"
            class="auth-submit-btn"
          />

          <router-link to="/login" class="back-link">
            {{ t('auth.back_to_login') }}
          </router-link>
        </form>
      </template>

      <template v-else>
        <div class="login-form">
          <div class="login-success">{{ t('auth.reset_username_sent') }}</div>
          <router-link to="/login" class="back-link">
            {{ t('auth.back_to_login') }}
          </router-link>
        </div>
      </template>
    </div>
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
