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
// `E_CREDENZIALE_BLOCCATA`: blocco deciso dall'amministratore, vale su
// tutte le porte e non scade da solo (config.credenziali).
// `E_UTENTE_BLOCCATO`: freno sulla sola coppia credenziale + provenienza. E'
// una frase chiusa (i minuti restano nel contesto del DB): la frase del DB
// non porta nessun dato in piu', e la chiave i18n e' tradotta.
const ERROR_CODE_MAP = {
  E_UTENTE_DISABILITATO: 'auth.account_disabled',
  E_UTENTE_NON_ATTIVO: 'auth.account_not_active',
  E_UTENTE_SCADUTO: 'auth.account_expired',
  E_VESTE_NON_ATTIVA: 'auth.veste_non_attiva',
  E_CREDENZIALE_BLOCCATA: 'auth.credential_locked',
  E_UTENTE_BLOCCATO: 'auth.account_locked'
}

// Rifiuti per cui si mostra la frase del DB (`message`), perche' porta un
// dato che la chiave i18n non ha; la chiave e' il ripiego se manca.
// `E_LOGIN_ATTESA` porta i secondi da aspettare.
// ⛔ Non `detail`: per questi codici porta la CAUSA del catalogo («Dopo molti
// tentativi…»), senza il numero. Verificato sull'envelope vero, 2026-09-25
// (test_login_credenziale_db).
const MESSAGGIO_DB_CON_DATO = {
  E_LOGIN_ATTESA: 'auth.login_wait'
}

function resolveLoginError(err) {
  const status = err?.response?.status
  // Throttle IP: troppe richieste all'endpoint, qualunque credenziale.
  // ⚠️ Per questo i rifiuti della credenziale sono 403 e non 429: qui il 429
  // si intercetta PRIMA di leggere il codice.
  if (status === 429) return t('auth.too_many_attempts')
  const data = err?.response?.data
  const code = data?.error?.code
  const ripiego = code && MESSAGGIO_DB_CON_DATO[code]
  if (ripiego) return data?.error?.message || t(ripiego)
  const i18nKey = code && ERROR_CODE_MAP[code]
  if (i18nKey) return t(i18nKey)
  // Token request fallito (401) → credenziali errate
  if (status === 401) return t('auth.login_error')
  // Guasto (es. provenienza non ricavabile, E_AUTH_CHIAMATA_NON_VALIDA) o
  // nessuna risposta (rete, server spento): non e' ne' una password
  // sbagliata ne' un «accesso negato», e dirlo manderebbe a cercare la cosa
  // sbagliata
  if (!status || status >= 500) return t('auth.login_technical_error')
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

        <!-- Errore SOPRA i campi, fuori dal flusso (login-error--sopra): nel
             flusso spingeva in basso pulsante e «Password dimenticata». -->
        <div v-if="errorMessage" class="login-error login-error--sopra" role="alert">
          {{ errorMessage }}
        </div>

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
