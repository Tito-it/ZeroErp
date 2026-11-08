<script setup>
// Scopo: Drawer creazione/modifica account email SMTP (admin only).
// Configura host/port/TLS/credenziali + email mittente/reply-to.
// In edit: pulsante test connessione gated su capability backend
// `can_test`/`test_reason` (Fase 6). Mostra Tag con ultimo esito test
// (last_test_outcome) quando disponibile. La password non viene
// re-inviata in edit se vuota (preserva quella corrente).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { displayTimestamp } from '../../core/utils/date'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Password from 'primevue/password'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import AppDrawer from '../../core/components/AppDrawer.vue'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { useEmailAccountsStore } from '../stores/emailAccounts'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { testEmailAccount } from '../api/amministrazione'



const props = defineProps({
  visible: Boolean,
  mode: String,
  accountId: Number
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const { t } = useI18n()
const store = useEmailAccountsStore()
const isReadonly = useInjectReadonly()
const { execute, loading: saving, campiErrati } = useApiHandler()
const { success, error: notifyError } = useNotify()

// Defaults form: estratti come costante per evitare duplicazione tra branch
// edit/create del watch. I valori SMTP cablati (587/TLS) sono temporanei,
// vanno rimossi quando il BE espone form-defaults dedicato (Fase 3 del WIP
// frontend amm-software, sezione A11).
const DEFAULT_FORM = Object.freeze({
  codice: '',
  descrizione: '',
  smtp_host: '',
  smtp_port: 587,
  smtp_use_tls: true,
  smtp_use_ssl: false,
  smtp_username: '',
  smtp_password: '',
  email_from: '',
  email_reply_to: '',
  unita_organizzativa_id: null,
  attivo: true,
})

const form = ref({ ...DEFAULT_FORM })
// Modifiche non salvate: fotografia all'apertura (anche in creazione), e
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })
const testLoading = ref(false)

const isEdit = computed(() => props.mode === 'edit')
const canSave = computed(() => {
  if (isReadonly.value) return false
  const f = form.value
  return f.codice?.trim() && f.descrizione?.trim() && f.email_from?.trim()
})

// Capability test connessione: arrivano dal BE (Fase 6) come parte del detail.
// `can_test` e' false su account inattivi o senza password SMTP; il
// `test_reason` (chiave i18n) alimenta il tooltip del pulsante disabilitato.
// `last_test_*` mostrano l'ultimo esito del test in un Tag.
const canTest = computed(() => store.currentAccount?.can_test === true)
const testReasonKey = computed(() => store.currentAccount?.test_reason || null)
const lastTestOutcome = computed(() => store.currentAccount?.last_test_outcome || null)
const lastTestAt = computed(() => store.currentAccount?.last_test_at || null)

const lastTestSeverity = computed(() => {
  if (lastTestOutcome.value === 'SUCCESS') return 'success'
  if (lastTestOutcome.value === 'FAILED') return 'danger'
  return 'secondary'
})

const lastTestLabel = computed(() => {
  if (lastTestOutcome.value === 'SUCCESS') return t('amministrazione.email_last_test_success')
  if (lastTestOutcome.value === 'FAILED') return t('amministrazione.email_last_test_failed')
  return t('amministrazione.email_last_test_never')
})

// Formattazione timestamp ultimo test via BB centralizzato (DD/MM/YYYY, HH:mm:ss).
const lastTestAtFormatted = computed(() => displayTimestamp(lastTestAt.value))

watch(() => props.visible, async (vis) => {
  if (!vis) return
  if (isEdit.value && props.accountId) {
    await store.fetchDetail(props.accountId)
    const d = store.currentAccount || {}
    // Spread del default + override col detail. La password resta vuota
    // (placeholder visivo "********"); se l'utente non la cambia, handleSave
    // la rimuove dal payload per non sovrascrivere quella corrente lato BE.
    form.value = {
      ...DEFAULT_FORM,
      codice: d.codice || '',
      descrizione: d.descrizione || '',
      smtp_host: d.smtp_host || '',
      smtp_port: d.smtp_port || DEFAULT_FORM.smtp_port,
      smtp_use_tls: d.smtp_use_tls ?? DEFAULT_FORM.smtp_use_tls,
      smtp_use_ssl: d.smtp_use_ssl ?? DEFAULT_FORM.smtp_use_ssl,
      smtp_username: d.smtp_username || '',
      email_from: d.email_from || '',
      email_reply_to: d.email_reply_to || '',
      unita_organizzativa_id: d.unita_organizzativa_id || null,
      attivo: d.attivo ?? DEFAULT_FORM.attivo,
    }
  } else {
    form.value = { ...DEFAULT_FORM }
  }
  fissa()
})

async function handleSave() {
  if (isReadonly.value) return
  const payload = { ...form.value }
  // Non inviare password vuota in edit (non sovrascrivere)
  if (isEdit.value && !payload.smtp_password) {
    delete payload.smtp_password
  }
  const result = await execute(
    () => isEdit.value
      ? store.update(props.accountId, payload)
      : store.create(payload),
    { successMessage: t('notifications.save_success') }
  )
  // Salvataggio fallito: il drawer resta aperto col lavoro dell'operatore (il
  // padre su `saved` chiude — prima chiudeva anche sull'errore, e il lavoro
  // si perdeva senza conferma).
  if (result === null) return
  fissa()
  emit('saved')
}

async function handleTest() {
  if (isReadonly.value) return
  if (!canTest.value) return
  if (!props.accountId) return
  testLoading.value = true
  try {
    const res = await testEmailAccount(props.accountId)
    const data = res.data?.data
    // Il BE ritorna detail arricchito (can_test, last_test_*) gia' aggiornato:
    // sostituisce currentAccount cosi' il Tag riflette subito l'esito senza
    // una GET aggiuntiva.
    if (data) store.currentAccount = data
    if (data?.success) {
      success(t('amministrazione.email_test_success'))
    } else {
      notifyError(data?.message || t('amministrazione.email_test_failed'))
    }
  } catch {
    notifyError(t('amministrazione.email_test_failed'))
  } finally {
    testLoading.value = false
  }
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('amministrazione.email_account_title')"
    :icon="NAV_ICONS.ACCOUNT_EMAIL"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="saving"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >
    <div class="form-grid">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('amministrazione.email_codice') }}</label>
          <InputText v-model="form.codice" class="app-codice-input" :disabled="isEdit || isReadonly" fluid
            :invalid="campiErrati.includes('codice')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.email_attivo') }}</label>
          <ToggleSwitch v-model="form.attivo" :disabled="isReadonly"
            :invalid="campiErrati.includes('attivo')"
          />
        </div>
      </div>

      <div class="form-field">
        <label>{{ t('amministrazione.email_descrizione') }}</label>
        <InputText v-model="form.descrizione" :disabled="isReadonly" fluid
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('amministrazione.email_smtp_host') }}</label>
          <InputText v-model="form.smtp_host" :disabled="isReadonly" fluid />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.email_smtp_port') }}</label>
          <InputNumber v-model="form.smtp_port" :min="1" :max="65535" :disabled="isReadonly" fluid />
        </div>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('amministrazione.email_smtp_tls') }}</label>
          <ToggleSwitch v-model="form.smtp_use_tls" :disabled="isReadonly" />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.email_smtp_ssl') }}</label>
          <ToggleSwitch v-model="form.smtp_use_ssl" :disabled="isReadonly" />
        </div>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('amministrazione.email_smtp_username') }}</label>
          <InputText v-model="form.smtp_username" :disabled="isReadonly" fluid />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.email_smtp_password') }}</label>
          <Password v-model="form.smtp_password" :feedback="false" toggleMask fluid
                   :disabled="isReadonly"
                   :placeholder="isEdit ? t('amministrazione.email_smtp_password_placeholder') : ''" />
        </div>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('amministrazione.email_from') }}</label>
          <InputText v-model="form.email_from" :disabled="isReadonly" fluid />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.email_reply_to') }}</label>
          <InputText v-model="form.email_reply_to" :disabled="isReadonly" fluid />
        </div>
      </div>

      <div v-if="isEdit && !isReadonly" class="email-test-row">
        <span v-tooltip.top="!canTest && testReasonKey ? t(testReasonKey) : null">
          <Button
            :label="t('amministrazione.email_test_connection')"
            :icon="MANAGE_ICONS.TEST_CONNESSIONE"
            :loading="testLoading"
            :disabled="!canTest"
            outlined
            size="small"
            @click="handleTest"
          />
        </span>
        <div class="email-last-test">
          <span class="email-last-test-label">{{ t('amministrazione.email_last_test_label') }}:</span>
          <Tag :value="lastTestLabel" :severity="lastTestSeverity" />
          <span v-if="lastTestAtFormatted" class="email-last-test-at">{{ lastTestAtFormatted }}</span>
        </div>
      </div>
    </div>
  </AppDrawer>
</template>

<style scoped>
.email-test-row {
  margin-top: 0.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}
.email-last-test {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}
.email-last-test-label {
  color: var(--app-text-muted, #6b7280);
}
.email-last-test-at {
  color: var(--app-text-muted, #6b7280);
  font-variant-numeric: tabular-nums;
}
</style>
