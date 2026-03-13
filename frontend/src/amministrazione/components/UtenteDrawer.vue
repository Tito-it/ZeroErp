<script setup>
// Scopo: drawer laterale per creazione e modifica operatore.
// Modalita' CREA: form Persona + Accesso + Collocazione.
// Modalita' MODIFICA: stessi campi (no password) + TabView Dati | Permessi.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtentiStore } from '../stores/utenti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { DRAWER_WIDTH } from '../../core/constants'
import UtentePermessiTab from './UtentePermessiTab.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import { useConfirm } from 'primevue/useconfirm'
import ConfirmDialog from 'primevue/confirmdialog'

const { t } = useI18n()
const store = useUtentiStore()
const { execute, loading } = useApiHandler()
const confirm = useConfirm()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  authUserId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

// Form fields
const form = ref({
  cognome: '',
  nome: '',
  username: '',
  email: '',
  password: '',
  codice_fiscale: '',
  data_nascita: null,
  sesso: 'M',
  ruolo_sistema: 'OPERATIVO',
  unita_organizzativa_id: null,
  valido_dal: null,
  valido_al: null
})

const sessoOptions = [
  { label: 'M', value: 'M' },
  { label: 'F', value: 'F' }
]

const ruoloOptions = [
  { label: t('amm.ruolo_admin'), value: 'ADMIN' },
  { label: t('amm.ruolo_operativo'), value: 'OPERATIVO' }
]

// Carica dati quando il drawer si apre in modifica
watch(() => props.visible, async (val) => {
  if (!val) return
  await store.fetchUnitaOrganizzative()
  if (isEdit.value && props.authUserId) {
    await store.fetchDetail(props.authUserId)
    const u = store.currentUtente
    if (u) {
      form.value = {
        cognome: u.last_name || '',
        nome: u.first_name || '',
        username: u.username || '',
        email: u.email || '',
        password: '',
        codice_fiscale: '',
        data_nascita: null,
        sesso: 'M',
        ruolo_sistema: u.ruolo_sistema || 'OPERATIVO',
        unita_organizzativa_id: u.unita_organizzativa_id,
        valido_dal: null,
        valido_al: u.valido_al || null
      }
    }
  } else {
    resetForm()
  }
})

function resetForm() {
  form.value = {
    cognome: '', nome: '', username: '', email: '', password: '',
    codice_fiscale: '', data_nascita: null, sesso: 'M',
    ruolo_sistema: 'OPERATIVO', unita_organizzativa_id: null,
    valido_dal: null, valido_al: null
  }
}

async function onSave() {
  if (isEdit.value) {
    const payload = {
      email: form.value.email,
      first_name: form.value.nome,
      last_name: form.value.cognome,
      ruolo_sistema: form.value.ruolo_sistema,
      unita_organizzativa_id: form.value.unita_organizzativa_id,
      valido_al: form.value.valido_al
    }
    const result = await execute(
      () => store.update(props.authUserId, payload),
      { successMessage: t('notifications.save_success') }
    )
    if (result) emit('saved')
  } else {
    const result = await execute(
      () => store.create(form.value),
      { successMessage: t('amm.utente_creato') }
    )
    if (result) emit('saved')
  }
}

function onDisabilita() {
  confirm.require({
    message: t('amm.disabilita_confirm'),
    header: t('amm.disabilita_title'),
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: async () => {
      const result = await execute(
        () => store.disabilita(props.authUserId),
        { successMessage: t('amm.utente_disabilitato') }
      )
      if (result) emit('saved')
    }
  })
}

function onClose() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    :header="isEdit ? t('amm.modifica_operatore') : t('amm.nuovo_operatore')"
    @update:visible="val => emit('update:visible', val)"
  >
    <ConfirmDialog />

    <template v-if="isEdit">
      <TabView>
        <TabPanel :header="t('amm.tab_dati')">
          <!-- Form campi modifica -->
          <div class="form-grid">
            <div class="field">
              <label>{{ t('amm.field_cognome') }}</label>
              <InputText v-model="form.cognome" class="w-full" />
            </div>
            <div class="field">
              <label>{{ t('amm.field_nome') }}</label>
              <InputText v-model="form.nome" class="w-full" />
            </div>
            <div class="field">
              <label>{{ t('amm.field_email') }}</label>
              <InputText v-model="form.email" class="w-full" />
            </div>
            <div class="field">
              <label>{{ t('amm.field_ruolo') }}</label>
              <Select v-model="form.ruolo_sistema" :options="ruoloOptions"
                option-label="label" option-value="value" class="w-full" />
            </div>
            <div class="field">
              <label>{{ t('amm.field_reparto') }}</label>
              <Select v-model="form.unita_organizzativa_id"
                :options="store.unitaOrganizzative"
                option-label="nome" option-value="id"
                class="w-full" :placeholder="t('amm.select_reparto')" />
            </div>
            <div class="field">
              <label>{{ t('amm.field_valido_al') }}</label>
              <DatePicker v-model="form.valido_al" date-format="yy-mm-dd" class="w-full" />
            </div>
          </div>

          <div class="flex justify-between mt-4">
            <Button :label="t('amm.disabilita_operatore')" severity="danger"
              icon="pi pi-ban" outlined @click="onDisabilita" />
            <div class="flex gap-2">
              <Button :label="t('common.cancel')" severity="secondary" @click="onClose" />
              <Button :label="t('common.save')" icon="pi pi-check"
                :loading="loading" @click="onSave" />
            </div>
          </div>
        </TabPanel>

        <TabPanel :header="t('amm.tab_permessi')">
          <UtentePermessiTab :auth-user-id="props.authUserId" />
        </TabPanel>
      </TabView>
    </template>

    <template v-else>
      <!-- Form creazione -->
      <div class="form-grid">
        <h4>{{ t('amm.section_persona') }}</h4>
        <div class="field">
          <label>{{ t('amm.field_cognome') }} *</label>
          <InputText v-model="form.cognome" class="w-full" />
        </div>
        <div class="field">
          <label>{{ t('amm.field_nome') }} *</label>
          <InputText v-model="form.nome" class="w-full" />
        </div>
        <div class="field">
          <label>{{ t('amm.field_cf') }}</label>
          <InputText v-model="form.codice_fiscale" class="w-full" />
        </div>
        <div class="field">
          <label>{{ t('amm.field_sesso') }}</label>
          <Select v-model="form.sesso" :options="sessoOptions"
            option-label="label" option-value="value" class="w-full" />
        </div>

        <h4>{{ t('amm.section_accesso') }}</h4>
        <div class="field">
          <label>{{ t('amm.field_username') }} *</label>
          <InputText v-model="form.username" class="w-full" />
        </div>
        <div class="field">
          <label>{{ t('amm.field_email') }} *</label>
          <InputText v-model="form.email" class="w-full" />
        </div>
        <div class="field">
          <label>{{ t('amm.field_password') }} *</label>
          <InputText v-model="form.password" type="password" class="w-full" />
        </div>

        <h4>{{ t('amm.section_collocazione') }}</h4>
        <div class="field">
          <label>{{ t('amm.field_ruolo') }}</label>
          <Select v-model="form.ruolo_sistema" :options="ruoloOptions"
            option-label="label" option-value="value" class="w-full" />
        </div>
        <div class="field">
          <label>{{ t('amm.field_reparto') }} *</label>
          <Select v-model="form.unita_organizzativa_id"
            :options="store.unitaOrganizzative"
            option-label="nome" option-value="id"
            class="w-full" :placeholder="t('amm.select_reparto')" />
        </div>
      </div>

      <div class="flex justify-end gap-2 mt-4">
        <Button :label="t('common.cancel')" severity="secondary" @click="onClose" />
        <Button :label="t('common.save')" icon="pi pi-check"
          :loading="loading" @click="onSave" />
      </div>
    </template>
  </Drawer>
</template>

<style scoped>
.form-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.field label {
  font-weight: 600;
  font-size: 0.875rem;
}
</style>
