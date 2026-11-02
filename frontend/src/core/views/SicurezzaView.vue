<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Scopo: «Sicurezza dell'accesso»: il secondo fattore della PROPRIA credenziale
         (brief sicurezza §3.4-bis, T-4). Configurazione (QR, segreto, codici di
         recupero mostrati una volta, conferma col primo codice), codici nuovi e
         disattivazione dietro un codice. L'avvio della configurazione vuole la
         password: con la sola sessione non si lega un telefono all'accesso. Ci porta il guard del router quando
         il secondo fattore e' obbligatorio e non configurato; ci si arriva anche
         dal menu utente.
  Note: Pagina della famiglia login (fuori da AppLayout): l'errore si mostra
        nella card, non in un toast (frontend-standards, «Regole per il
        developer» punto 2). Con l'obbligo pendente il backend apre solo questi
        endpoint, il profilo e il logout.
-->
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/auth'
import {
  confermaSecondoFattore,
  disattivaSecondoFattore,
  getSecondoFattore,
  registraSecondoFattore,
  rigeneraCodiciRecupero,
} from '../api/secondoFattore'
import { seSessioneChiusaDalFreno } from '../uscitaSessione'
import { extractApiError } from '../utils/apiError'
import { downloadBlob } from '../utils/download'
import { provaSecondoFattore } from '../utils/provaSecondoFattore'
import { STATO_SECONDO_FATTORE as STATO } from '../constants'
import Button from 'primevue/button'
import Password from 'primevue/password'
import CodiceSecondoFattoreInput from '../components/CodiceSecondoFattoreInput.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const stato = ref(null)
// La configurazione appena avviata: QR, segreto e codici, dati UNA volta sola.
const configurazione = ref(null)
// I codici di recupero nuovi, da mostrare una volta (dopo la rigenerazione).
const codiciNuovi = ref(null)
// Quale azione sullo stato ATTIVO si sta compilando: 'codici' | 'disattiva' | null.
const azione = ref(null)
const codice = ref('')
// La password della credenziale, chiesta per avviare la configurazione.
const password = ref('')
const usaRecupero = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const loading = ref(false)

const attivo = computed(() => stato.value?.stato === STATO.ATTIVO)
const fraseMotivo = computed(() =>
  stato.value?.motivo ? t(`auth.secondo_fattore.motivo.${stato.value.motivo}`) : ''
)

// Scopo: esegue una chiamata mostrando l'errore nella card.
async function esegui(chiamata) {
  errorMessage.value = ''
  successMessage.value = ''
  loading.value = true
  try {
    return await chiamata()
  } catch (err) {
    // Il freno sulla password chiude la sessione: si va al login col motivo.
    if (!seSessioneChiusaDalFreno(err)) {
      errorMessage.value = extractApiError(err, t('auth.login_technical_error'))
    }
    return null
  } finally {
    loading.value = false
  }
}

async function caricaStato() {
  const res = await esegui(() => getSecondoFattore())
  if (res) stato.value = res.data.data
}

onMounted(caricaStato)

async function avviaConfigurazione() {
  const res = await esegui(() => registraSecondoFattore(password.value))
  if (!res) return
  configurazione.value = res.data.data
  password.value = ''
  codice.value = ''
  await caricaStato()
}

async function conferma() {
  const res = await esegui(() => confermaSecondoFattore(codice.value))
  if (!res) return
  stato.value = res.data.data
  configurazione.value = null
  codice.value = ''
  successMessage.value = t('auth.secondo_fattore.attivato')
  // L'obbligo e' chiuso: il profilo lo dice, e il guard lascia passare.
  await auth.fetchProfile()
}

async function rigenera() {
  const res = await esegui(() => rigeneraCodiciRecupero(codice.value))
  if (!res) return
  codiciNuovi.value = res.data.data.codici_recupero
  chiudiAzione()
  await caricaStato()
}

async function disattiva() {
  const prova = provaSecondoFattore(codice.value, usaRecupero.value)
  const res = await esegui(() => disattivaSecondoFattore(prova))
  if (!res) return
  stato.value = res.data.data
  chiudiAzione()
  successMessage.value = t('auth.secondo_fattore.disattivato')
  // Con l'obbligo, la pagina resta qui: il guard ci riporta comunque.
  await auth.fetchProfile()
}

function apriAzione(nome) {
  azione.value = nome
  codice.value = ''
  usaRecupero.value = false
  errorMessage.value = ''
  codiciNuovi.value = null
}

function chiudiAzione() {
  azione.value = null
  codice.value = ''
  usaRecupero.value = false
}

// Scopo: i codici di recupero in un file di testo, da conservare.
function scaricaCodici(codici) {
  const testo = `${t('auth.secondo_fattore.file_codici_intestazione')}\n\n${codici.join('\n')}\n`
  downloadBlob(new Blob([testo], { type: 'text/plain;charset=utf-8' }), t('auth.secondo_fattore.file_codici_nome'))
}

function tornaAllApplicazione() {
  router.push(route.query.redirect || '/')
}
</script>

<template>
  <!-- Card rettangolare ad altezza libera, non il cerchio del login: il
       contenuto della configurazione non ci starebbe (auth-pages.css). -->
  <div class="login-page login-page--scorre">
    <img src="@/assets/images/zeroerp-doodle.jpeg" alt="" class="login-bg" />
    <div class="login-card login-card--pagina">

      <div class="login-form login-form--wide">
        <h2 class="login-title">{{ t('auth.secondo_fattore.titolo') }}</h2>
        <p v-if="auth.mustConfigureSecondFactor" class="login-subtitle">
          {{ t('auth.secondo_fattore.obbligo_da_configurare') }} {{ fraseMotivo }}
        </p>

        <div v-if="errorMessage" class="login-error" role="alert">{{ errorMessage }}</div>
        <div v-if="successMessage" class="login-success">{{ successMessage }}</div>

        <template v-if="stato">
          <!-- Non attivo: avvio, poi QR + codici + conferma -->
          <template v-if="!attivo">
            <form v-if="!configurazione" @submit.prevent="avviaConfigurazione" class="secondo-fattore-configurazione">
              <p class="login-subtitle">
                {{ stato.stato === STATO.DA_CONFERMARE
                  ? t('auth.secondo_fattore.configurazione_a_meta')
                  : t('auth.secondo_fattore.spiegazione') }}
              </p>
              <p class="login-subtitle">{{ t('auth.secondo_fattore.chiedi_password') }}</p>
              <div class="field">
                <Password
                  id="password_secondo_fattore"
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
                :label="stato.stato === STATO.DA_CONFERMARE
                  ? t('auth.secondo_fattore.ricomincia')
                  : t('auth.secondo_fattore.configura')"
                :loading="loading"
                :disabled="!password"
                class="auth-submit-btn"
              />
            </form>

            <form v-else @submit.prevent="conferma" class="secondo-fattore-configurazione">
              <p class="login-subtitle">{{ t('auth.secondo_fattore.passo_qr') }}</p>
              <img :src="configurazione.qr_data_uri" :alt="t('auth.secondo_fattore.qr_alt')" class="secondo-fattore-qr" />
              <p class="secondo-fattore-nota">{{ t('auth.secondo_fattore.segreto_manuale') }}</p>
              <code class="secondo-fattore-segreto">{{ configurazione.segreto }}</code>

              <p class="login-subtitle">{{ t('auth.secondo_fattore.passo_codici') }}</p>
              <ul class="secondo-fattore-codici">
                <li v-for="c in configurazione.codici_recupero" :key="c"><code>{{ c }}</code></li>
              </ul>
              <a href="#" class="forgot-link" @click.prevent="scaricaCodici(configurazione.codici_recupero)">
                {{ t('auth.secondo_fattore.scarica_codici') }}
              </a>

              <p class="login-subtitle">{{ t('auth.secondo_fattore.passo_conferma') }}</p>
              <CodiceSecondoFattoreInput v-model:codice="codice" :disabled="loading">
                <Button
                  type="submit"
                  :label="t('auth.secondo_fattore.attiva')"
                  :loading="loading"
                  :disabled="!codice"
                  class="auth-submit-btn"
                />
              </CodiceSecondoFattoreInput>
            </form>
          </template>

          <!-- Attivo: codici nuovi, disattivazione -->
          <template v-else>
            <p class="login-subtitle">
              {{ t('auth.secondo_fattore.stato_attivo', { n: stato.codici_recupero_rimasti }) }}
            </p>

            <template v-if="codiciNuovi">
              <p class="login-subtitle">{{ t('auth.secondo_fattore.codici_nuovi') }}</p>
              <ul class="secondo-fattore-codici">
                <li v-for="c in codiciNuovi" :key="c"><code>{{ c }}</code></li>
              </ul>
              <a href="#" class="forgot-link" @click.prevent="scaricaCodici(codiciNuovi)">
                {{ t('auth.secondo_fattore.scarica_codici') }}
              </a>
            </template>

            <form v-if="azione" @submit.prevent="azione === 'codici' ? rigenera() : disattiva()" class="secondo-fattore-configurazione">
              <p class="login-subtitle">
                {{ azione === 'codici'
                  ? t('auth.secondo_fattore.chiedi_codice_codici')
                  : (usaRecupero ? t('auth.secondo_fattore.chiedi_recupero') : t('auth.secondo_fattore.chiedi_codice_disattiva')) }}
              </p>
              <!-- Il recupero solo per disattivare: i codici nuovi si
                   generano dietro il codice dell'app. -->
              <CodiceSecondoFattoreInput
                v-model:codice="codice"
                v-model:usa-recupero="usaRecupero"
                :consenti-recupero="azione === 'disattiva'"
                :disabled="loading"
              >
                <Button
                  type="submit"
                  :label="azione === 'codici' ? t('auth.secondo_fattore.genera_codici') : t('auth.secondo_fattore.disattiva')"
                  :loading="loading"
                  :disabled="!codice"
                  class="auth-submit-btn"
                />
              </CodiceSecondoFattoreInput>
              <a href="#" class="back-link" @click.prevent="chiudiAzione">{{ t('common.cancel') }}</a>
            </form>

            <template v-else>
              <Button :label="t('auth.secondo_fattore.genera_codici')" class="auth-submit-btn" @click="apriAzione('codici')" />
              <a href="#" class="forgot-link" @click.prevent="apriAzione('disattiva')">
                {{ t('auth.secondo_fattore.disattiva') }}
              </a>
            </template>
          </template>
        </template>

        <a v-if="!auth.mustChangePassword && !auth.mustConfigureSecondFactor" href="#" class="back-link" @click.prevent="tornaAllApplicazione">
          {{ t('auth.account.torna') }}
        </a>
        <a v-else href="#" class="back-link" @click.prevent="auth.logout().then(() => router.push({ name: 'login' }))">
          {{ t('auth.logout') }}
        </a>
      </div>
    </div>
  </div>
</template>

<!-- CSS in assets/auth-pages.css (condiviso tra tutte le view auth) -->
