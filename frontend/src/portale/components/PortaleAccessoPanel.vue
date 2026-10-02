<script setup>
// Scopo: Pannello admin "Accesso Portale + Shop" inserito nei drawer
// cliente/fornitore. Gestisce ciclo di vita completo delle vesti
// non-operatore:
//   - Invia / Reinvia invito (email + branching INVITO/CROSS lato BE)
//   - Visualizza stato (NESSUNO / PENDING / NON_SPEDITO / ATTIVO / DISATTIVO)
//   - Disattiva (soft revoke, idempotente)
//
// La sezione "Shop" e' visibile solo per clienti (`entitaTipo='cliente'`).
// I fornitori non accedono allo shop B2C consumer.
//
// Stato caricato all'apertura via `getStatoAccessi*` + ricaricato dopo
// ogni mutazione (invio, reinvio, disattiva) per mantenere coerenza UI.

import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useEsitoInvito } from '../../core/composables/useEsitoInvito'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { isEmailValid } from '../../core/utils/validators'
import { extractApiError } from '../../core/utils/apiError'
import { MANAGE_ICONS, STATO_VESTE } from '../../core/constants'
import { statoVesteSeverity } from '../../core/utils/severity'
import {
  disattivaPortaleCliente,
  disattivaPortaleFornitore,
  disattivaShopCliente,
  getStatoAccessiCliente,
  getStatoAccessiFornitore,
  invitaClientePortale,
  invitaClienteShop,
  invitaFornitorePortale,
} from '../api/portaleAdminApi'

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { notificaEsitoInvito } = useEsitoInvito()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  entitaTipo: { type: String, required: true, validator: v => ['cliente', 'fornitore'].includes(v) },
  entitaId: { type: [Number, String], required: true },
  emailIniziale: { type: String, default: '' },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['stato-cambiato'])

const email = ref(props.emailIniziale)
const statoPortale = ref({ stato: STATO_VESTE.NESSUNO, invito_inviato_at: null, token_scade_at: null, username: null, email: null })
const statoShop = ref({ stato: STATO_VESTE.NESSUNO, invito_inviato_at: null, token_scade_at: null, username: null, email: null })

const showShopActions = computed(() => props.entitaTipo === 'cliente')
const canInvia = computed(
  () => !props.readonly && isEmailValid(email.value) && !loading.value,
)

watch(
  () => props.emailIniziale,
  (val) => { if (val && !email.value) email.value = val },
)

// Il colore dello stato di una veste: BB `statoVesteSeverity` (sede unica,
// la usa anche la lista «Altri accessi» dell'amministrazione).

// Scopo: Una veste si disattiva quando esiste e non e' gia' spenta: accesa,
// o con un invito in volo (spedito o no). Una regola per portale e shop.
const STATI_DISATTIVABILI = [STATO_VESTE.ATTIVO, STATO_VESTE.PENDING, STATO_VESTE.NON_SPEDITO]
const disattivabile = (stato) => STATI_DISATTIVABILI.includes(stato)

// ── Load stato all'apertura + dopo ogni mutazione ────────────────

async function loadStato() {
  try {
    const res = props.entitaTipo === 'cliente'
      ? await getStatoAccessiCliente(props.entitaId)
      : await getStatoAccessiFornitore(props.entitaId)
    const data = res?.data?.data || {}
    statoPortale.value = data.portale || { stato: STATO_VESTE.NESSUNO }
    statoShop.value = data.shop || { stato: STATO_VESTE.NESSUNO }
  } catch (err) {
    // Load stato non blocca l'UI: se fallisce mostriamo stato ignoto,
    // i pulsanti azione restano comunque usabili.
    notify.warn(extractApiError(err, t('portale.stato_load_error')))
  }
}

// Load stato all'apertura + ricarica se il prop `entitaId` cambia
// (panel riusato tra drawer diversi senza remount).
onMounted(() => { if (props.entitaId) loadStato() })
watch(() => props.entitaId, (newId) => { if (newId) loadStato() })

// ── Helper unificato: esegue una API mutante, mostra toast, ricarica
// stato e notifica il parent. `successKey`/`errorKey` sono chiavi i18n;
// `apiCall` e' un thunk che chiama la funzione API con gli argomenti
// gia' legati. Unifica la vecchia coppia _doInvio / _doDisattiva.
// `invito`: la risposta porta `inviato` (l'email e' partita?), e il toast lo
// sceglie `notificaEsitoInvito` invece del successo fisso (F-3).
async function _runAction({ apiCall, successKey, errorKey, invito = false }) {
  const res = await execute(apiCall, {
    successMessage: invito ? null : t(successKey),
    errorHandler: (err) => {
      notify.error(extractApiError(err, t(errorKey)))
    },
  })
  if (res !== null) {
    if (invito) notificaEsitoInvito(res, t(successKey))
    await loadStato()
    emit('stato-cambiato')
  }
}

// Scopo: Dialog conferma + esecuzione azione generica. `dangerKey` se
// valorizzato, il dialog e' rosso (usato per reinvio e disattivazione).
function _confirmAndRun({ titleKey, msgKey, msgParams = {}, danger = false, apiCall, successKey, errorKey, invito = false }) {
  confirmAction({
    header: t(titleKey),
    message: t(msgKey, msgParams),
    danger,
    onAccept: () => _runAction({ apiCall, successKey, errorKey, invito }),
  })
}

// Scopo: Conferma invio/reinvio invito per un namespace (portale|shop).
// Pre-valida email, poi delega al helper generico. Le chiavi i18n
// seguono convenzione `<namespace>.{invio|reinvio}_confirm_title/msg`.
function _confirmInvio({ reinvio, namespace, apiFn }) {
  if (!isEmailValid(email.value)) {
    notify.error(t('portale.email_non_valida'))
    return
  }
  const action = reinvio ? 'reinvio' : 'invio'
  _confirmAndRun({
    titleKey: `${namespace}.${action}_confirm_title`,
    msgKey: `${namespace}.${action}_confirm_msg`,
    msgParams: { email: email.value },
    danger: reinvio,
    apiCall: () => apiFn(props.entitaId, { email: email.value.trim(), reinvio }),
    successKey: reinvio ? `${namespace}.invito_reinviato` : `${namespace}.invito_inviato`,
    errorKey: `${namespace}.invito_errore`,
    invito: true,
  })
}

// Scopo: Conferma disattivazione veste per un namespace. Dialog sempre
// danger (operazione irreversibile lato email: i token pendenti vengono
// invalidati). Riattivazione = nuovo invito (flow implicito lato BE).
function _confirmDisattiva({ namespace, apiFn }) {
  _confirmAndRun({
    titleKey: `${namespace}.disattiva_confirm_title`,
    msgKey: `${namespace}.disattiva_confirm_msg`,
    danger: true,
    apiCall: () => apiFn(props.entitaId),
    successKey: `${namespace}.disattivato_ok`,
    errorKey: `${namespace}.disattivato_errore`,
  })
}

// Wrapper specifici — risolvono la fn API corretta in base a entitaTipo.
const _apiInvitoPortale = () => props.entitaTipo === 'cliente'
  ? invitaClientePortale
  : invitaFornitorePortale
const _apiDisattivaPortale = () => props.entitaTipo === 'cliente'
  ? disattivaPortaleCliente
  : disattivaPortaleFornitore

const onInvia = () => _confirmInvio({ reinvio: false, namespace: 'portale', apiFn: _apiInvitoPortale() })
const onReinvia = () => _confirmInvio({ reinvio: true, namespace: 'portale', apiFn: _apiInvitoPortale() })
const onInviaShop = () => _confirmInvio({ reinvio: false, namespace: 'shop', apiFn: invitaClienteShop })
const onReinviaShop = () => _confirmInvio({ reinvio: true, namespace: 'shop', apiFn: invitaClienteShop })

const onDisattivaPortale = () => _confirmDisattiva({ namespace: 'portale', apiFn: _apiDisattivaPortale() })
const onDisattivaShop = () => _confirmDisattiva({ namespace: 'shop', apiFn: disattivaShopCliente })
</script>

<template>
  <section class="portale-accesso-panel">
    <h4>
      {{ t('portale.accesso_portale_title') }}
      <Tag
        :value="t(`auth.stato_veste.${statoPortale.stato}`)"
        :severity="statoVesteSeverity(statoPortale.stato)"
        class="portale-accesso-stato-tag"
      />
    </h4>
    <p class="portale-accesso-help">
      {{ t('portale.accesso_portale_help') }}
    </p>

    <!-- Utente collegato: visibile quando esiste un auth_user collegato
         (stato != NESSUNO). Mostra username + email per il troubleshooting. -->
    <div v-if="statoPortale.username" class="portale-accesso-user-info">
      <span class="portale-accesso-user-label">{{ t('portale.accessi_web.user') }}</span>
      <span class="portale-accesso-user-value">
        {{ statoPortale.username }}
        <span v-if="statoPortale.email" class="portale-accesso-user-email">
          ({{ statoPortale.email }})
        </span>
      </span>
    </div>

    <div class="form-field">
      <label for="portale-email">{{ t('portale.email_destinatario') }}</label>
      <InputText
        id="portale-email"
        v-model="email"
        :disabled="readonly || loading"
        :placeholder="t('portale.email_placeholder')"
      />
    </div>

    <div class="portale-accesso-actions">
      <!-- Invia: NESSUNO / DISATTIVO. Reinvia: PENDING / NON_SPEDITO / ATTIVO. -->
      <Button
        v-if="statoPortale.stato === STATO_VESTE.NESSUNO || statoPortale.stato === STATO_VESTE.DISATTIVO"
        :label="t('portale.btn_invia_invito')"
        :icon="MANAGE_ICONS.INVITA"
        :disabled="!canInvia"
        :loading="loading"
        @click="onInvia"
      />
      <Button
        v-else
        :label="t('portale.btn_reinvia_invito')"
        :icon="MANAGE_ICONS.INVITA"
        severity="warn"
        outlined
        :disabled="!canInvia"
        :loading="loading"
        @click="onReinvia"
      />
      <!-- Disattiva: visibile per ATTIVO, PENDING o NON_SPEDITO. -->
      <Button
        v-if="disattivabile(statoPortale.stato)"
        :label="t('portale.btn_disattiva')"
        :icon="MANAGE_ICONS.DISATTIVA"
        severity="danger"
        outlined
        :disabled="readonly || loading"
        :loading="loading"
        @click="onDisattivaPortale"
      />
    </div>

    <Message
      v-if="statoPortale.stato === STATO_VESTE.PENDING && statoPortale.token_scade_at"
      severity="info"
      :closable="false"
      class="mt-1"
    >
      {{ t('portale.invito_pending_info') }}
    </Message>
    <Message
      v-else-if="statoPortale.stato === STATO_VESTE.NON_SPEDITO"
      severity="error"
      :closable="false"
      class="mt-1"
    >
      {{ t('common.invito_non_spedito_info') }}
    </Message>

    <!-- Sezione Shop Customer (§13.7): solo per clienti. -->
    <div v-if="showShopActions" class="portale-accesso-shop">
      <h4>
        {{ t('shop.accesso_shop_title') }}
        <Tag
          :value="t(`auth.stato_veste.${statoShop.stato}`)"
          :severity="statoVesteSeverity(statoShop.stato)"
          class="portale-accesso-stato-tag"
        />
      </h4>
      <p class="portale-accesso-help">
        {{ t('shop.accesso_shop_help') }}
      </p>
      <div v-if="statoShop.username" class="portale-accesso-user-info">
        <span class="portale-accesso-user-label">{{ t('portale.accessi_web.user') }}</span>
        <span class="portale-accesso-user-value">
          {{ statoShop.username }}
          <span v-if="statoShop.email" class="portale-accesso-user-email">
            ({{ statoShop.email }})
          </span>
        </span>
      </div>
      <div class="portale-accesso-actions">
        <Button
          v-if="statoShop.stato === STATO_VESTE.NESSUNO || statoShop.stato === STATO_VESTE.DISATTIVO"
          :label="t('shop.btn_invia_invito')"
          :icon="MANAGE_ICONS.INVITA"
          :disabled="!canInvia"
          :loading="loading"
          @click="onInviaShop"
        />
        <Button
          v-else
          :label="t('shop.btn_reinvia_invito')"
          :icon="MANAGE_ICONS.INVITA"
          severity="warn"
          outlined
          :disabled="!canInvia"
          :loading="loading"
          @click="onReinviaShop"
        />
        <Button
          v-if="disattivabile(statoShop.stato)"
          :label="t('shop.btn_disattiva')"
          :icon="MANAGE_ICONS.DISATTIVA"
          severity="danger"
          outlined
          :disabled="readonly || loading"
          :loading="loading"
          @click="onDisattivaShop"
        />
      </div>
      <Message
        v-if="statoShop.stato === STATO_VESTE.PENDING && statoShop.token_scade_at"
        severity="info"
        :closable="false"
        class="mt-1"
      >
        {{ t('shop.invito_pending_info') }}
      </Message>
      <Message
        v-else-if="statoShop.stato === STATO_VESTE.NON_SPEDITO"
        severity="error"
        :closable="false"
        class="mt-1"
      >
        {{ t('common.invito_non_spedito_info') }}
      </Message>
    </div>
  </section>
</template>

<style scoped>
.portale-accesso-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--app-drawer-section-border);
}
.portale-accesso-help {
  font-size: 0.85rem;
  color: var(--app-text-muted);
  margin: 0;
}
.portale-accesso-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.portale-accesso-shop {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 1rem;
  margin-top: 0.5rem;
  border-top: 1px dashed var(--app-drawer-section-border);
}
.portale-accesso-stato-tag {
  margin-left: 0.5rem;
  vertical-align: middle;
  font-size: 0.75rem;
}
.portale-accesso-user-info {
  font-size: 0.85rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.portale-accesso-user-label {
  color: var(--app-text-muted);
}
.portale-accesso-user-value {
  font-weight: 600;
}
.portale-accesso-user-email {
  font-weight: 400;
  color: var(--app-text-muted);
}
</style>
