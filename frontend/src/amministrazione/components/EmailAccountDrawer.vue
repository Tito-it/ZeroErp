<script setup>
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Password from 'primevue/password'
import ToggleSwitch from 'primevue/toggleswitch'
import Button from 'primevue/button'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import { DRAWER_WIDTH } from '../../core/constants'
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
const { execute, loading: saving } = useApiHandler()
const { success, error: notifyError } = useNotify()

const form = ref({})
const testLoading = ref(false)

const isEdit = computed(() => props.mode === 'edit')
const canSave = computed(() => {
  const f = form.value
  return f.codice?.trim() && f.descrizione?.trim() && f.email_from?.trim()
})

watch(() => props.visible, async (vis) => {
  if (!vis) return
  if (isEdit.value && props.accountId) {
    await store.fetchDetail(props.accountId)
    const d = store.currentAccount
    form.value = {
      codice: d?.codice || '',
      descrizione: d?.descrizione || '',
      smtp_host: d?.smtp_host || '',
      smtp_port: d?.smtp_port || 587,
      smtp_use_tls: d?.smtp_use_tls ?? true,
      smtp_use_ssl: d?.smtp_use_ssl ?? false,
      smtp_username: d?.smtp_username || '',
      smtp_password: '',
      email_from: d?.email_from || '',
      email_reply_to: d?.email_reply_to || '',
      unita_organizzativa_id: d?.unita_organizzativa_id || null,
      attivo: d?.attivo ?? true
    }
  } else {
    form.value = {
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
      attivo: true
    }
  }
})

async function handleSave() {
  const payload = { ...form.value }
  // Non inviare password vuota in edit (non sovrascrivere)
  if (isEdit.value && !payload.smtp_password) {
    delete payload.smtp_password
  }
  await execute(
    () => isEdit.value
      ? store.update(props.accountId, payload)
      : store.create(payload),
    { successMessage: t('notifications.save_success') }
  )
  emit('saved')
}

async function handleTest() {
  if (!props.accountId) return
  testLoading.value = true
  try {
    const res = await testEmailAccount(props.accountId)
    const data = res.data?.data
    if (data?.success) {
      success(t('amm.email_test_success'))
    } else {
      notifyError(data?.message || t('amm.email_test_failed'))
    }
  } catch {
    notifyError(t('amm.email_test_failed'))
  } finally {
    testLoading.value = false
  }
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        title="Account Email"
        icon="pi pi-at"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('amm.email_codice') }}</label>
            <InputText v-model="form.codice" :disabled="isEdit" fluid />
          </div>
          <div class="form-field">
            <label>{{ t('amm.email_attivo') }}</label>
            <ToggleSwitch v-model="form.attivo" />
          </div>
        </div>

        <div class="form-field">
          <label>{{ t('amm.email_descrizione') }}</label>
          <InputText v-model="form.descrizione" fluid />
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('amm.email_smtp_host') }}</label>
            <InputText v-model="form.smtp_host" fluid />
          </div>
          <div class="form-field">
            <label>{{ t('amm.email_smtp_port') }}</label>
            <InputNumber v-model="form.smtp_port" :min="1" :max="65535" fluid />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('amm.email_smtp_tls') }}</label>
            <ToggleSwitch v-model="form.smtp_use_tls" />
          </div>
          <div class="form-field">
            <label>{{ t('amm.email_smtp_ssl') }}</label>
            <ToggleSwitch v-model="form.smtp_use_ssl" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('amm.email_smtp_username') }}</label>
            <InputText v-model="form.smtp_username" fluid />
          </div>
          <div class="form-field">
            <label>{{ t('amm.email_smtp_password') }}</label>
            <Password v-model="form.smtp_password" :feedback="false" toggleMask fluid
                     :placeholder="isEdit ? '********' : ''" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('amm.email_from') }}</label>
            <InputText v-model="form.email_from" fluid />
          </div>
          <div class="form-field">
            <label>{{ t('amm.email_reply_to') }}</label>
            <InputText v-model="form.email_reply_to" fluid />
          </div>
        </div>

        <div v-if="isEdit" style="margin-top: 0.5rem;">
          <Button
            :label="t('amm.email_test_connection')"
            icon="pi pi-wifi"
            :loading="testLoading"
            outlined
            size="small"
            @click="handleTest"
          />
        </div>
      </div>
    </div>

    <template #footer>
      <DrawerFooter
        :loading="saving"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="emit('cancelled')"
      />
    </template>
  </Drawer>
</template>
