<script setup>
// Scopo: Pannello admin "Accesso Portale + Shop" inserito nei drawer
// cliente/fornitore. Gestisce i REFERENTI di ogni veste non-operatore:
//   - l'elenco dei referenti per tipo (portale, shop), ognuno col suo stato
//     (`script.fn_stato_veste`) e, se accesa ma oggi fuori porta, il fermo
//     (`utilizzabile`, BB `vesteFermaOggi`)
//   - Invita un referente: l'email scritta sopra, un referente in piu' se e'
//     una persona nuova, il reinvio se e' gia' fra i referenti
//   - per referente: Reinvia (invito in volo), Invia di nuovo (spenta o
//     revocata: il nuovo invito toglie il segno, a DB), Disattiva (la revoca,
//     idempotente)
//
// ⭐ Un elenco dal 2026-11-28 (giro 4 del brief-db-accessi-area-clienti, D-M7):
//    un cliente o un fornitore ha piu' referenti, ognuno con la sua veste.
//    Fino ad allora il pannello mostrava una veste per tipo, e le due sezioni
//    erano scritte due volte nel template: ora sono una, ripetuta sui tipi.
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
import { displayDate } from '../../core/utils/date'
import { MANAGE_ICONS, STATO_VESTE, STATUS_ICONS } from '../../core/constants'
import { statoVesteSeverity } from '../../core/utils/severity'
import { vesteFermaOggi } from '../../core/utils/veste'
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
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['stato-cambiato'])

const email = ref('')
const referenti = ref({ portale: [], shop: [] })

const canInvia = computed(
  () => !props.readonly && isEmailValid(email.value) && !loading.value,
)

// Scopo: le sezioni del pannello, una per tipo di veste: `namespace` e' il
//        prefisso delle chiavi i18n (`portale.*`, `shop.*`) e la chiave
//        dell'elenco nella risposta; le due funzioni API sono quelle della
//        veste e dell'entita'. Lo shop solo per i clienti.
const sezioni = computed(() => {
  const cliente = props.entitaTipo === 'cliente'
  const elenco = [{
    namespace: 'portale',
    titleKey: 'portale.accesso_portale_title',
    helpKey: 'portale.accesso_portale_help',
    apiInvito: cliente ? invitaClientePortale : invitaFornitorePortale,
    apiDisattiva: cliente ? disattivaPortaleCliente : disattivaPortaleFornitore,
  }]
  if (cliente) {
    elenco.push({
      namespace: 'shop',
      titleKey: 'shop.accesso_shop_title',
      helpKey: 'shop.accesso_shop_help',
      apiInvito: invitaClienteShop,
      apiDisattiva: disattivaShopCliente,
    })
  }
  return elenco
})

// Scopo: l'email dell'invito parte da quella che propone il BE con lo stato
//        (`email_suggerita`: il primo referente, poi il contatto PRINCIPALE
//        del ruolo, poi quello di default). Non scavalca cio' che l'operatore
//        ha gia' scritto. Dal 2026-11-21: prima la passava il drawer padre
//        (`emailIniziale`), e non arrivava mai.
function proponiEmail(suggerita) {
  if (suggerita && !email.value.trim()) email.value = suggerita
}

// Scopo: Una veste si disattiva quando non e' gia' spenta: accesa, o con un
// invito in volo (spedito o no). Una regola per portale e shop.
const STATI_DISATTIVABILI = [STATO_VESTE.ATTIVO, STATO_VESTE.PENDING, STATO_VESTE.NON_SPEDITO]
const disattivabile = (stato) => STATI_DISATTIVABILI.includes(stato)

// Scopo: Il gesto d'invito sulla veste di un referente. Spenta senza un invito
// in volo (disattivata o revocata) → «Invia invito» (il nuovo invito toglie il
// segno della revoca, a DB); invito in volo → «Reinvia invito»; accesa →
// niente: la persona entra gia'.
const STATI_DA_INVITARE = [STATO_VESTE.DISATTIVO, STATO_VESTE.REVOCATA]
const STATI_DA_REINVIARE = [STATO_VESTE.PENDING, STATO_VESTE.NON_SPEDITO]
const daInvitare = (stato) => STATI_DA_INVITARE.includes(stato)
const daReinviare = (stato) => STATI_DA_REINVIARE.includes(stato)

// ── Load stato all'apertura + dopo ogni mutazione ────────────────

async function loadStato() {
  try {
    const res = props.entitaTipo === 'cliente'
      ? await getStatoAccessiCliente(props.entitaId)
      : await getStatoAccessiFornitore(props.entitaId)
    const data = res?.data?.data || {}
    referenti.value = { portale: data.portale || [], shop: data.shop || [] }
    proponiEmail(data.email_suggerita)
  } catch (err) {
    // Load stato non blocca l'UI: se fallisce l'elenco resta vuoto, e
    // l'invito di un referente resta usabile.
    notify.warn(extractApiError(err, t('portale.stato_load_error')))
  }
}

// Load stato all'apertura + ricarica se il prop `entitaId` cambia
// (panel riusato tra drawer diversi senza remount).
onMounted(() => { if (props.entitaId) loadStato() })
// ⚠️ Un'altra entita' riparte da campo vuoto: l'email della precedente
//    bloccherebbe la proposta della nuova (`proponiEmail` non scavalca).
watch(() => props.entitaId, (newId) => {
  email.value = ''
  if (newId) loadStato()
})

// ── Helper unificato: esegue una API mutante, mostra toast, ricarica
// stato e notifica il parent. `successKey`/`errorKey` sono chiavi i18n;
// `apiCall` e' un thunk che chiama la funzione API con gli argomenti
// gia' legati.
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

// Scopo: Dialog conferma + esecuzione azione generica. `danger` per il
// reinvio e la disattivazione.
function _confirmAndRun({ titleKey, msgKey, msgParams = {}, danger = false, apiCall, successKey, errorKey, invito = false }) {
  confirmAction({
    header: t(titleKey),
    message: t(msgKey, msgParams),
    danger,
    onAccept: () => _runAction({ apiCall, successKey, errorKey, invito }),
  })
}

// Scopo: Conferma invio/reinvio invito a un indirizzo, per una sezione. Le
// chiavi i18n seguono la convenzione `<namespace>.{invio|reinvio}_confirm_*`.
// L'email e' quella scritta sopra (un referente da invitare) o quella del
// referente della riga (il suo invito di nuovo).
function _confirmInvio(sezione, destinatario, { reinvio }) {
  if (!isEmailValid(destinatario)) {
    notify.error(t('portale.email_non_valida'))
    return
  }
  const action = reinvio ? 'reinvio' : 'invio'
  const ns = sezione.namespace
  _confirmAndRun({
    titleKey: `${ns}.${action}_confirm_title`,
    msgKey: `${ns}.${action}_confirm_msg`,
    msgParams: { email: destinatario },
    danger: reinvio,
    apiCall: () => sezione.apiInvito(props.entitaId, { email: destinatario.trim(), reinvio }),
    successKey: reinvio ? `${ns}.invito_reinviato` : `${ns}.invito_inviato`,
    errorKey: `${ns}.invito_errore`,
    invito: true,
  })
}

// Scopo: «Invita un referente»: l'email scritta nel campo. Se e' gia' di un
//        referente di quel tipo, il BE la tratta come il suo reinvio.
const onInvitaReferente = (sezione) => _confirmInvio(sezione, email.value, { reinvio: false })

// Scopo: l'invito di nuovo a un referente della riga, con la sua email.
const onInvitaDiNuovo = (sezione, voce) => _confirmInvio(sezione, voce.email || '', { reinvio: daReinviare(voce.stato) })

// Scopo: Conferma disattivazione della veste di un referente. Dialog sempre
// danger (i token pendenti vengono invalidati). Riattivazione = nuovo invito.
function onDisattiva(sezione, voce) {
  const ns = sezione.namespace
  _confirmAndRun({
    titleKey: `${ns}.disattiva_confirm_title`,
    msgKey: `${ns}.disattiva_confirm_msg`,
    msgParams: { email: voce.email || voce.username || '' },
    danger: true,
    apiCall: () => sezione.apiDisattiva(props.entitaId, voce.identita_id),
    successKey: `${ns}.disattivato_ok`,
    errorKey: `${ns}.disattivato_errore`,
  })
}
</script>

<template>
  <section class="portale-accesso-panel">
    <div class="form-field">
      <label for="portale-email">{{ t('portale.email_destinatario') }}</label>
      <InputText
        id="portale-email"
        v-model="email"
        :disabled="readonly || loading"
        :placeholder="t('portale.email_placeholder')"
      />
    </div>

    <div
      v-for="sezione in sezioni" :key="sezione.namespace"
      class="portale-accesso-sezione"
    >
      <h4>{{ t(sezione.titleKey) }}</h4>
      <p class="portale-accesso-help">{{ t(sezione.helpKey) }}</p>

      <p v-if="!referenti[sezione.namespace].length" class="app-text-muted">
        {{ t('portale.referenti_nessuno') }}
      </p>
      <ul v-else class="portale-accesso-referenti">
        <li v-for="voce in referenti[sezione.namespace]" :key="voce.identita_id">
          <div class="portale-accesso-referente-testa">
            <Tag
              :value="t(`auth.stato_veste.${voce.stato}`)"
              :severity="statoVesteSeverity(voce.stato)"
              :icon="vesteFermaOggi(voce) ? STATUS_ICONS.BLOCCATO : undefined"
            />
            <span class="portale-accesso-user-value">
              {{ voce.username }}
              <span v-if="voce.email" class="portale-accesso-user-email">({{ voce.email }})</span>
            </span>
          </div>
          <small v-if="vesteFermaOggi(voce)" class="app-field-hint">
            {{ t('amministrazione.accessi.veste_ferma_oggi') }}
            <template v-if="voce.valido_dal">
              {{ t('amministrazione.accessi.veste_valida_dal', { quando: displayDate(voce.valido_dal) }) }}
            </template>
            <template v-if="voce.valido_al">
              {{ t('amministrazione.accessi.veste_valida_al', { quando: displayDate(voce.valido_al) }) }}
            </template>
          </small>
          <Message
            v-if="voce.stato === STATO_VESTE.PENDING && voce.token_scade_at"
            severity="info" :closable="false"
          >
            {{ t(`${sezione.namespace}.invito_pending_info`) }}
          </Message>
          <Message
            v-else-if="voce.stato === STATO_VESTE.NON_SPEDITO"
            severity="error" :closable="false"
          >
            {{ t('common.invito_non_spedito_info') }}
          </Message>
          <div v-if="!readonly" class="portale-accesso-actions">
            <Button
              v-if="daInvitare(voce.stato) || daReinviare(voce.stato)"
              :label="t(daReinviare(voce.stato) ? `${sezione.namespace}.btn_reinvia_invito` : `${sezione.namespace}.btn_invia_invito`)"
              :icon="MANAGE_ICONS.INVITA"
              :severity="daReinviare(voce.stato) ? 'warn' : undefined"
              outlined size="small"
              :disabled="loading || !isEmailValid(voce.email || '')"
              :loading="loading"
              @click="onInvitaDiNuovo(sezione, voce)"
            />
            <Button
              v-if="disattivabile(voce.stato)"
              :label="t(`${sezione.namespace}.btn_disattiva`)"
              :icon="MANAGE_ICONS.DISATTIVA"
              severity="danger"
              outlined size="small"
              :disabled="loading"
              :loading="loading"
              @click="onDisattiva(sezione, voce)"
            />
          </div>
        </li>
      </ul>

      <div v-if="!readonly" class="portale-accesso-actions">
        <Button
          :label="t(`${sezione.namespace}.btn_invita_referente`)"
          :icon="MANAGE_ICONS.INVITA"
          :disabled="!canInvia"
          :loading="loading"
          @click="onInvitaReferente(sezione)"
        />
      </div>
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
.portale-accesso-sezione {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.portale-accesso-sezione + .portale-accesso-sezione {
  padding-top: 1rem;
  margin-top: 0.5rem;
  border-top: 1px dashed var(--app-drawer-section-border);
}
.portale-accesso-help {
  font-size: 0.85rem;
  color: var(--app-text-muted);
  margin: 0;
}
.portale-accesso-referenti {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.portale-accesso-referenti > li {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.portale-accesso-referente-testa {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}
.portale-accesso-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.portale-accesso-user-value {
  font-weight: 600;
}
.portale-accesso-user-email {
  font-weight: 400;
  color: var(--app-text-muted);
}
</style>
