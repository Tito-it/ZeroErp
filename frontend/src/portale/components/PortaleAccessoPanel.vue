<script setup>
// Scopo: Pannello riutilizzabile "Accesso Portale" inseribile nei drawer
// admin (ClienteDrawer, FornitoreDrawer). Gestisce invio/reinvio dell'invito
// portale via email. Stato UI minimale per MVP: email editabile + pulsante
// invia; dopo la send mostra conferma. Lo stato persistente (invito_inviato
// / attivo) sara' aggiunto in Sprint C4 con endpoint /portale-status/.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { isEmailValid } from '../../core/utils/validators'
import { extractApiError } from '../../core/utils/apiError'
import {
  invitaClientePortale,
  invitaFornitorePortale,
} from '../api/portaleAdminApi'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  // Tipo entita' del drawer ospite: 'cliente' | 'fornitore'.
  entitaTipo: { type: String, required: true, validator: v => ['cliente', 'fornitore'].includes(v) },
  // ID entita' sul backend (billing_account_id per cliente, fornitore.id per fornitore).
  entitaId: { type: [Number, String], required: true },
  // Email suggerita (dal soggetto associato): usata come default editabile.
  emailIniziale: { type: String, default: '' },
  // Mostra come "reinvio" (testo diverso su bottone). Opzionale, MVP non
  // ancora differenzia da stato BE; rimane toggle manuale dell'admin.
  modalitaReinvio: { type: Boolean, default: false },
  // Se true disabilita il pulsante (drawer in sola lettura / readonly).
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['inviato'])

const email = ref(props.emailIniziale)
const esitoInvio = ref(null) // { inviato: true, email: 'a***@b.it', nuovo_utente: true }

watch(
  () => props.emailIniziale,
  (val) => {
    if (val && !email.value) email.value = val
  },
)

const canInvia = computed(
  () => !props.readonly && isEmailValid(email.value) && !loading.value,
)

// Scopo: Normalizza l'email e lancia la richiesta al BE. Distingue invio
// standard da reinvio (reinvio=true invalida i token precedenti).
async function doInvia(reinvio) {
  const fn = props.entitaTipo === 'cliente' ? invitaClientePortale : invitaFornitorePortale
  const res = await execute(
    () => fn(props.entitaId, { email: email.value.trim(), reinvio }),
    {
      successMessage: t(
        reinvio ? 'portale.invito_reinviato' : 'portale.invito_inviato',
      ),
      errorHandler: (err) => {
        notify.error(extractApiError(err, t('portale.invito_errore')))
      },
    },
  )
  if (res !== null) {
    esitoInvio.value = res?.data?.data || res?.data || { inviato: true }
    emit('inviato', esitoInvio.value)
  }
}

// Scopo: Richiede conferma prima di invio standard (generalmente irreversibile
// per l'utente destinatario: riceve email subito).
function onInvia() {
  if (!isEmailValid(email.value)) {
    notify.error(t('portale.email_non_valida'))
    return
  }
  confirmAction({
    title: t('portale.invio_confirm_title'),
    message: t('portale.invio_confirm_msg', { email: email.value }),
    onAccept: () => doInvia(false),
  })
}

// Scopo: Richiede conferma piu' forte per reinvio (invalida token precedenti).
function onReinvia() {
  if (!isEmailValid(email.value)) {
    notify.error(t('portale.email_non_valida'))
    return
  }
  confirmAction({
    title: t('portale.reinvio_confirm_title'),
    message: t('portale.reinvio_confirm_msg', { email: email.value }),
    danger: true,
    onAccept: () => doInvia(true),
  })
}
</script>

<template>
  <section class="portale-accesso-panel">
    <h4>{{ t('portale.accesso_portale_title') }}</h4>
    <p class="portale-accesso-help">
      {{ t('portale.accesso_portale_help') }}
    </p>

    <div class="form-field">
      <label for="portale-email">{{ t('portale.email_destinatario') }}</label>
      <InputText
        id="portale-email"
        v-model="email"
        :disabled="readonly || loading"
        class="w-full"
        :placeholder="t('portale.email_placeholder')"
      />
    </div>

    <div class="portale-accesso-actions">
      <Button
        :label="t('portale.btn_invia_invito')"
        icon="pi pi-envelope"
        :disabled="!canInvia"
        :loading="loading"
        @click="onInvia"
      />
      <Button
        :label="t('portale.btn_reinvia_invito')"
        icon="pi pi-refresh"
        severity="warn"
        outlined
        :disabled="!canInvia"
        @click="onReinvia"
      />
    </div>

    <Message
      v-if="esitoInvio?.inviato"
      severity="success"
      :closable="false"
      class="mt-1"
    >
      {{ t('portale.invito_confermato', { email: esitoInvio.email || '' }) }}
      <span v-if="esitoInvio.nuovo_utente">
        — {{ t('portale.nuovo_utente_creato') }}
      </span>
    </Message>
  </section>
</template>

<style scoped>
.portale-accesso-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--app-drawer-section-border, var(--p-content-border-color));
}
.portale-accesso-help {
  font-size: 0.85rem;
  color: var(--app-text-muted, var(--p-text-muted-color));
  margin: 0;
}
.portale-accesso-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>
