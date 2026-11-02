<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Scopo: Il secondo fattore di una CREDENZIALE, dal lato dell'amministratore
         (brief sicurezza §3.4-bis, T-4): lo stato, l'obbligo sulla credenziale
         e la disattivazione del device (telefono perso), col motivo. Lo monta
         `CredenzialeAzioni`, nei drawer dell'operatore e degli altri accessi.
  Note: ⭐ Era `OperatoreSecondoFattore` fino al 2026-10-02: il secondo fattore
        e' della credenziale, non della veste operatore, e da quel giorno lo usa
        anche il tab «Altri accessi» (brief-db-be-fe-area-accessi, regola del 2).
        La credenziale e' una: obbligo e device valgono per tutte le porte. Un obbligo che viene da un PROFILO non
        si spegne da qui (si cambia il profilo): l'interruttore dice solo quello
        della credenziale. Disattivare non chiude le sessioni aperte
        (decisione 8). Endpoint riservati al SUPER_ADMIN.
        ⛔ Il PROPRIO device non si disattiva da qui: il backend lo rifiuta
        (senza prova sarebbe la decisione 7 aggirata), e il pulsante non
        c'e'. Si passa dalla pagina «Sicurezza», con un codice.
-->
<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import {
  disattivaSecondoFattoreCredenziale,
  getSecondoFattoreCredenziale,
  impostaObbligoSecondoFattore,
} from '../api/amministrazione'
import { MANAGE_ICONS, STATO_SECONDO_FATTORE, MOTIVO_OBBLIGO_SECONDO_FATTORE } from '../../core/constants'
import { useAuthStore } from '../../stores/auth'
import MotivoDialog from '../../core/components/MotivoDialog.vue'
import Button from 'primevue/button'
import ToggleSwitch from 'primevue/toggleswitch'

const props = defineProps({
  authUserId: { type: Number, required: true },
  readonly: { type: Boolean, default: false },
})

const { t } = useI18n()
// ⚠️ `execute` restituisce GIA' il contenuto dell'envelope (lo stato), non la
//    risposta axios: fino al 2026-10-02 qui si leggeva `res.data.data`, cioe'
//    undefined, e la sezione non compariva mai.
const { execute, loading, campiErrati } = useApiHandler()
const auth = useAuthStore()

const stato = ref(null)
const dialogVisibile = ref(false)
// Cambia a ogni salvataggio dell'obbligo fallito: l'interruttore si
// ri-monta e torna al valore del server (il ToggleSwitch tiene il proprio).
const chiaveObbligo = ref(0)

const attivo = computed(() => stato.value?.stato === STATO_SECONDO_FATTORE.ATTIVO)
const sonoIo = computed(() => auth.user?.utente?.auth_user_id === props.authUserId)
const fraseStato = computed(() =>
  stato.value ? t(`amministrazione.secondo_fattore.stato.${stato.value.stato}`) : ''
)
// L'obbligo che viene da un profilo: l'interruttore non lo spegne, e lo si dice.
const obbligoDalProfilo = computed(() => stato.value?.motivo === MOTIVO_OBBLIGO_SECONDO_FATTORE.PROFILO)

async function carica() {
  const id = props.authUserId
  // Niente stato della credenziale precedente mentre si legge la nuova.
  stato.value = null
  const res = await execute(() => getSecondoFattoreCredenziale(id))
  // Una risposta arrivata dopo il cambio di credenziale non e' la sua.
  if (res && id === props.authUserId) stato.value = res
}

watch(() => props.authUserId, (id) => { if (id) carica() }, { immediate: true })

// Scopo: l'obbligo sulla credenziale, subito (come l'invito: non passa dal Salva).
async function cambiaObbligo(valore) {
  const res = await execute(
    () => impostaObbligoSecondoFattore(props.authUserId, valore),
    { successMessage: t('notifications.save_success') }
  )
  if (res) stato.value = res
  else chiaveObbligo.value++
}

function apriDisattiva() {
  dialogVisibile.value = true
}

async function confermaDisattiva(motivo) {
  const res = await execute(
    () => disattivaSecondoFattoreCredenziale(props.authUserId, motivo),
    { successMessage: t('amministrazione.secondo_fattore.disattivato') }
  )
  if (res) {
    stato.value = res
    dialogVisibile.value = false
  }
}
</script>

<template>
  <div v-if="stato" class="form-field">
    <label>{{ t('amministrazione.secondo_fattore.titolo') }}</label>
    <div class="app-form-inline-toggle">
      <span>{{ fraseStato }}</span>
      <small v-if="attivo" class="app-field-hint">
        {{ t('amministrazione.secondo_fattore.codici_rimasti', { n: stato.codici_recupero_rimasti }) }}
      </small>
    </div>

    <div class="app-form-inline-toggle">
      <ToggleSwitch
        :key="chiaveObbligo"
        :model-value="stato.obbligo_sulla_credenziale"
        input-id="tg-obbligo-secondo-fattore"
        :disabled="readonly || loading"
        @update:model-value="cambiaObbligo"
      />
      <label for="tg-obbligo-secondo-fattore">{{ t('amministrazione.secondo_fattore.obbligo_credenziale') }}</label>
    </div>
    <small v-if="obbligoDalProfilo" class="app-field-hint">
      {{ t('amministrazione.secondo_fattore.obbligo_dal_profilo') }}
    </small>

    <div v-if="attivo && !readonly && !sonoIo">
      <Button
        :label="t('amministrazione.secondo_fattore.disattiva')"
        :icon="MANAGE_ICONS.SICUREZZA_ACCESSO"
        severity="danger"
        outlined size="small"
        @click="apriDisattiva"
      />
    </div>

    <!-- Gesto distruttivo quanto il blocco della credenziale: stessa gravita'
         del pulsante (`danger`), che prima qui mancava. -->
    <MotivoDialog
      v-model:visible="dialogVisibile"
      :header="t('amministrazione.secondo_fattore.disattiva')"
      :label="t('amministrazione.secondo_fattore.motivo')"
      obbligatorio
      :loading="loading"
      :invalid="campiErrati.includes('motivo')"
      :save-label="t('amministrazione.secondo_fattore.disattiva')"
      save-severity="danger"
      @conferma="confermaDisattiva"
    >
      <p>{{ t('amministrazione.secondo_fattore.disattiva_spiegazione') }}</p>
    </MotivoDialog>
  </div>
</template>
