<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Scopo: Il secondo fattore di un operatore, dal lato dell'amministratore
         (brief sicurezza §3.4-bis, T-4), nella scheda dati del drawer
         operatore: lo stato, l'obbligo sulla CREDENZIALE e la disattivazione
         del device (telefono perso), col motivo.
  Note: La credenziale e' una: obbligo e device valgono per tutte le porte, non
        per la sola veste di operatore. Un obbligo che viene da un PROFILO non
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
  disattivaSecondoFattoreOperatore,
  getSecondoFattoreOperatore,
  impostaObbligoSecondoFattore,
} from '../api/amministrazione'
import { MANAGE_ICONS, STATO_SECONDO_FATTORE, MOTIVO_OBBLIGO_SECONDO_FATTORE } from '../../core/constants'
import { useAuthStore } from '../../stores/auth'
import AppDialog from '../../core/components/AppDialog.vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
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
const motivo = ref('')
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
  // Niente stato dell'operatore precedente mentre si legge il nuovo.
  stato.value = null
  const res = await execute(() => getSecondoFattoreOperatore(id))
  // Una risposta arrivata dopo il cambio di operatore non e' la sua.
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
  motivo.value = ''
  dialogVisibile.value = true
}

async function confermaDisattiva() {
  const res = await execute(
    () => disattivaSecondoFattoreOperatore(props.authUserId, motivo.value),
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

    <AppDialog
      v-model:visible="dialogVisibile"
      :header="t('amministrazione.secondo_fattore.disattiva')"
      width="sm"
      :loading="loading"
      :save-disabled="!motivo.trim()"
      :save-label="t('amministrazione.secondo_fattore.disattiva')"
      @save="confermaDisattiva"
      @cancel="dialogVisibile = false"
    >
      <p>{{ t('amministrazione.secondo_fattore.disattiva_spiegazione') }}</p>
      <div class="form-field">
        <label for="motivo-disattiva">{{ t('amministrazione.secondo_fattore.motivo') }} *</label>
        <InputText
          id="motivo-disattiva"
          v-model="motivo"
          :invalid="campiErrati.includes('motivo')"
          fluid
        />
      </div>
    </AppDialog>
  </div>
</template>
