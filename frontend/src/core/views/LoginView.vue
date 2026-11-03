<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/auth'
import { CANALE_LOGIN, resolveCanaleLogin } from '../constants'
import { FRASE_MOTIVO_USCITA } from '../sessione'
import { useNotify } from '../composables/useNotify'
import { extractApiErrorCode } from '../utils/apiError'
import { provaSecondoFattore } from '../utils/provaSecondoFattore'
import CodiceSecondoFattoreInput from '../components/CodiceSecondoFattoreInput.vue'
import LinkInformazioni from '../components/LinkInformazioni.vue'
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

// La chiave d'ingresso: nome utente o email, secondo il canale.
const identificativo = ref('')
const password = ref('')
// UI attuale: solo operatori interni. Canale forzato ad ADMIN,
// ignoriamo `auth.loginChannel` persistito (se un utente aveva scelto
// PORTALE/SHOP in passato, qui lo riportiamo a ADMIN). Store e API
// multi-canale restano attivi per future pagine dedicate portale/shop.
const canale = ref(CANALE_LOGIN.ADMIN.key)
// L'etichetta del primo campo segue la chiave d'ingresso del canale
// (`campoIngresso`, L-4): il nome utente per ADMIN, l'email per PORTALE e
// SHOP. ⛔ Mai fissa: la store manda il campo del canale, e un'etichetta
// «Username» sulla porta dell'email chiederebbe la cosa sbagliata.
const etichettaIngresso = computed(() =>
  resolveCanaleLogin(canale.value).campoIngresso === 'email' ? t('common.email') : t('auth.username')
)
const errorMessage = ref('')
const loading = ref(false)
const notify = useNotify()

// Il secondo passo (secondo fattore attivo, brief sicurezza §3.4-bis): la
// password giusta porta una SFIDA, e la scheda chiede il codice dell'app o un
// codice di recupero. `sfida` vuota = si e' al passo della password.
const sfida = ref('')
const codice = ref('')
const usaRecupero = ref(false)

// Mappa codici errore DB → chiavi i18n per messaggi login specifici.
// `E_VESTE_NON_ATTIVA` (§8.3.2) e' il caso "account valido ma senza
// accesso al canale richiesto": mostriamo un messaggio dedicato e
// generico (niente enumeration di quali canali sono attivi).
// `E_CREDENZIALE_BLOCCATA`: blocco deciso dall'amministratore, vale su
// tutte le porte e non scade da solo (config.credenziali).
// Una veste fuori dalle sue date ha l'esito di una spenta: niente codici
// per le date (`E_UTENTE_NON_ATTIVO`/`E_UTENTE_SCADUTO` ritirati il
// 2026-10-07, brief-db-veste-utilizzabile D-4).
const ERROR_CODE_MAP = {
  E_UTENTE_DISABILITATO: 'auth.account_disabled',
  E_VESTE_NON_ATTIVA: 'auth.veste_non_attiva',
  E_CREDENZIALE_BLOCCATA: 'auth.credential_locked',
  // Il secondo passo: il codice sbagliato, gia' usato, di recupero non valido.
  E_TOTP_CODICE_NON_VALIDO: 'auth.secondo_fattore.codice_non_valido',
  E_TOTP_PASSO_GIA_USATO: 'auth.secondo_fattore.codice_gia_usato',
  E_TOTP_RECOVERY_NON_VALIDO: 'auth.secondo_fattore.recupero_non_valido',
  E_TOTP_SFIDA_NON_VALIDA: 'auth.secondo_fattore.sfida_scaduta'
}

// Rifiuti per cui si mostra la frase del DB (`message`), perche' porta un
// dato che la chiave i18n non ha; la chiave e' il ripiego se manca.
// `E_LOGIN_ATTESA` porta i secondi da aspettare; `E_UTENTE_BLOCCATO` (il
// freno sulla sola coppia credenziale + provenienza) i minuti, dal
// `20260925-52` — prima era una frase chiusa e stava in ERROR_CODE_MAP.
// ⛔ Non `detail`: per questi codici porta la CAUSA del catalogo («Dopo molti
// tentativi…»), senza il numero. Verificato sull'envelope vero, 2026-09-25
// (test_login_credenziale_db).
const MESSAGGIO_DB_CON_DATO = {
  E_LOGIN_ATTESA: 'auth.login_wait',
  E_UTENTE_BLOCCATO: 'auth.account_locked'
}

// Al secondo passo, i rifiuti che chiudono la sfida: scaduta, o la credenziale
// bloccata (dall'amministratore o dal freno, che il secondo passo ricontrolla).
// Restare sul campo del codice farebbe riprovare una sfida ormai inutile.
const RIFIUTI_CHE_CHIUDONO_LA_SFIDA = new Set([
  'E_TOTP_SFIDA_NON_VALIDA',
  'E_CREDENZIALE_BLOCCATA',
  'E_UTENTE_BLOCCATO',
  'E_LOGIN_ATTESA'
])

function resolveLoginError(err) {
  const status = err?.response?.status
  // Throttle IP: troppe richieste all'endpoint, qualunque credenziale.
  // ⚠️ Per questo i rifiuti della credenziale sono 403 e non 429: qui il 429
  // si intercetta PRIMA di leggere il codice.
  if (status === 429) return t('auth.too_many_attempts')
  const data = err?.response?.data
  const code = extractApiErrorCode(err)
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

// Pre-popolazione errorMessage in base a `reason` query: il motivo per cui
// l'applicazione ha riportato al login (`MOTIVO_USCITA` in `core/sessione`:
// rinnovo fallito, logout da un'altra scheda). Mantiene UX coerente: l'utente
// vede subito perche' e' tornato sul login. Motivo sconosciuto: nessuna frase.
onMounted(() => {
  const chiave = FRASE_MOTIVO_USCITA[route.query.reason]
  if (chiave) {
    errorMessage.value = t(chiave)
  }
})

// Scopo: dopo l'accesso, dove andare. Gli obblighi li gestisce il guard del
//        router; il cambio password resta esplicito come prima.
function dopoAccesso() {
  if (auth.mustChangePassword) {
    router.push('/change-password')
    return
  }
  router.push(route.query.redirect || '/')
}

async function handleLogin() {
  errorMessage.value = ''
  loading.value = true
  try {
    // §8.5.2: la store usa `canale` per scegliere l'endpoint token
    // (/admin/token/ | /portale/token/ | /shop/token/). Default ADMIN.
    const esito = await auth.login(identificativo.value, password.value, canale.value)
    if (esito?.secondoPasso) {
      sfida.value = esito.sfida
      // La password non serve piu': non resta in memoria durante il codice.
      password.value = ''
      codice.value = ''
      usaRecupero.value = false
      return
    }
    dopoAccesso()
  } catch (err) {
    errorMessage.value = resolveLoginError(err)
  } finally {
    loading.value = false
  }
}

// Scopo: il secondo passo. Una sfida scaduta (o presentata da un'altra
//        postazione) si rifiuta col suo messaggio e riporta alla password.
async function handleSecondoPasso() {
  errorMessage.value = ''
  loading.value = true
  try {
    const { codiciRecuperoRimasti } = await auth.completaSecondoPasso(
      sfida.value, provaSecondoFattore(codice.value, usaRecupero.value)
    )
    if (codiciRecuperoRimasti !== null) {
      notify.warn(t('auth.secondo_fattore.recupero_rimasti', { n: codiciRecuperoRimasti }))
    }
    dopoAccesso()
  } catch (err) {
    errorMessage.value = resolveLoginError(err)
    if (RIFIUTI_CHE_CHIUDONO_LA_SFIDA.has(extractApiErrorCode(err))) tornaAllaPassword(false)
  } finally {
    loading.value = false
  }
}

// Scopo: torna al passo della password (annulla, sfida scaduta, credenziale bloccata).
function tornaAllaPassword(azzeraMessaggio = true) {
  sfida.value = ''
  codice.value = ''
  password.value = ''
  if (azzeraMessaggio) errorMessage.value = ''
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

      <!-- Secondo passo: il codice dell'app di autenticazione, o un codice
           di recupero. -->
      <form v-if="sfida" @submit.prevent="handleSecondoPasso" class="login-form">
        <div v-if="errorMessage" class="login-error login-esito--sopra" role="alert">
          {{ errorMessage }}
        </div>
        <p class="login-subtitle">
          {{ usaRecupero ? t('auth.secondo_fattore.chiedi_recupero') : t('auth.secondo_fattore.chiedi_codice') }}
        </p>
        <CodiceSecondoFattoreInput
          id="codice"
          v-model:codice="codice"
          v-model:usa-recupero="usaRecupero"
          consenti-recupero
          :disabled="loading"
          autofocus
        >
          <Button
            type="submit"
            :label="t('auth.secondo_fattore.verifica')"
            :loading="loading"
            :disabled="!codice"
            class="auth-submit-btn"
          />
        </CodiceSecondoFattoreInput>
        <a href="#" class="back-link" @click.prevent="tornaAllaPassword()">
          {{ t('auth.back_to_login') }}
        </a>
      </form>

      <form v-else @submit.prevent="handleLogin" class="login-form">
        <!-- ChannelSelector nascosto: in questa fase il login e' solo per
             operatori interni. Il canale resta forzato ad ADMIN (store +
             router + api multi-canale restano attivi per future pagine
             dedicate portale/shop). Per riabilitare: reintrodurre il
             componente con v-model="canale". -->
        <!-- <ChannelSelector v-model="canale" :disabled="loading" /> -->

        <!-- Errore SOPRA i campi, fuori dal flusso (login-esito--sopra): nel
             flusso spingeva in basso pulsante e «Password dimenticata». -->
        <div v-if="errorMessage" class="login-error login-esito--sopra" role="alert">
          {{ errorMessage }}
        </div>

        <div class="field">
          <InputText
            id="identificativo"
            v-model="identificativo"
            :disabled="loading"
            :placeholder="etichettaIngresso"
            :aria-label="etichettaIngresso"
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
          :disabled="!identificativo || !password"
          class="auth-submit-btn"
        />

        <router-link to="/password-reset" class="forgot-link">
          {{ t('auth.forgot_password') }}
        </router-link>
      </form>
    </div>
    <LinkInformazioni />
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
