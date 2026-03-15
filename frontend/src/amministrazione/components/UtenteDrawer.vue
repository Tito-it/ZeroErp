<script setup>
// Scopo: Drawer laterale per creazione e modifica operatore.
// Modalita' CREA: SoggettoForm (tipo PR forzato) + AuthUserForm + collocazione.
// Modalita' MODIFICA: form dati + TabView Dati | Permessi.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUtentiStore } from '../stores/utenti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useSoggettoForm } from '../../core/composables/useSoggettoForm'
import { useAuthUser } from '../../core/composables/useAuthUser'
import { useLookup } from '../../core/composables/useLookup'
import { lookupCodici } from '../../core/apiCore'
import { listUnitaOrganizzative } from '../api/amministrazione'
import { DRAWER_WIDTH } from '../../core/constants'
import SoggettoForm from '../../core/components/SoggettoForm.vue'
import AuthUserForm from '../../core/components/AuthUserForm.vue'
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

// Building block: soggetto PF (tipo forzato = 1 = PR persona fisica)
const soggetto = useSoggettoForm({ tipoForzato: 1 })
const auth = useAuthUser()

// Lookup via useLookup (non piu' dallo store)
const qualifiche = useLookup(() => lookupCodici('config.qualifiche'), { immediate: true })
const unitaOrg = useLookup(listUnitaOrganizzative, { immediate: true })

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  authUserId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

// Collocazione (specifico operatore, non building block)
const collocazione = ref({
  ruolo_sistema: 'OPERATIVO',
  qualifica_id: null,
  unita_organizzativa_id: null,
  valido_al: null
})

const ruoloOptions = [
  { label: t('amm.ruolo_admin'), value: 'ADMIN' },
  { label: t('amm.ruolo_operativo'), value: 'OPERATIVO' }
]

// Form modifica (solo per edit mode)
const editForm = ref({
  cognome: '', nome: '', email: '',
  ruolo_sistema: 'OPERATIVO',
  unita_organizzativa_id: null,
  valido_al: null
})

// Carica dati quando il drawer si apre
watch(() => props.visible, async (val) => {
  if (!val) return
  if (isEdit.value && props.authUserId) {
    await store.fetchDetail(props.authUserId)
    const u = store.currentUtente
    if (u) {
      editForm.value = {
        cognome: u.last_name || '',
        nome: u.first_name || '',
        email: u.email || '',
        ruolo_sistema: u.ruolo_sistema || 'OPERATIVO',
        unita_organizzativa_id: u.unita_organizzativa_id,
        valido_al: u.valido_al || null
      }
    }
  } else {
    soggetto.reset()
    auth.reset()
    collocazione.value = {
      ruolo_sistema: 'OPERATIVO',
      qualifica_id: null,
      unita_organizzativa_id: null,
      valido_al: null
    }
  }
})

async function onSave() {
  if (isEdit.value) {
    const payload = {
      email: editForm.value.email,
      first_name: editForm.value.nome,
      last_name: editForm.value.cognome,
      ruolo_sistema: editForm.value.ruolo_sistema,
      unita_organizzativa_id: editForm.value.unita_organizzativa_id,
      valido_al: editForm.value.valido_al
    }
    const result = await execute(
      () => store.update(props.authUserId, payload),
      { successMessage: t('notifications.save_success') }
    )
    if (result) emit('saved')
  } else {
    // Assembla payload da building block
    const payload = {
      cognome: soggetto.form.cognome,
      nome: soggetto.form.nome,
      codice_fiscale: soggetto.form.codice_fiscale,
      data_nascita: soggetto.form.data_nascita,
      sesso: soggetto.form.sesso,
      comune_nascita_id: soggetto.form.comune_nascita_id,
      email: auth.form.email,
      username: auth.form.username,
      password: auth.form.password,
      ...collocazione.value
    }
    const result = await execute(
      () => store.create(payload),
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
          <div class="form-grid">
            <div class="form-field">
              <label>{{ t('common.cognome') }}</label>
              <InputText v-model="editForm.cognome" class="w-full" />
            </div>
            <div class="form-field">
              <label>{{ t('common.nome') }}</label>
              <InputText v-model="editForm.nome" class="w-full" />
            </div>
            <div class="form-field">
              <label>{{ t('common.email') }}</label>
              <InputText v-model="editForm.email" class="w-full" />
            </div>
            <div class="form-field">
              <label>{{ t('amm.field_ruolo') }}</label>
              <Select v-model="editForm.ruolo_sistema" :options="ruoloOptions"
                option-label="label" option-value="value" class="w-full" />
            </div>
            <div class="form-field">
              <label>{{ t('amm.field_reparto') }}</label>
              <Select v-model="editForm.unita_organizzativa_id"
                :options="unitaOrg.items.value"
                option-label="descrizione" option-value="id"
                class="w-full" :placeholder="t('amm.select_reparto')" />
            </div>
            <div class="form-field">
              <label>{{ t('amm.field_valido_al') }}</label>
              <DatePicker v-model="editForm.valido_al" date-format="yy-mm-dd" class="w-full" />
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

    <div v-else class="app-drawer-content">
      <!-- Building block: soggetto PF -->
      <h4>{{ t('amm.section_persona') }}</h4>
      <SoggettoForm
        :form="soggetto.form"
        :tipi-soggetto="soggetto.tipiSoggetto"
        :is-p-f="soggetto.isPF.value"
        :show-partita-iva="soggetto.showPartitaIva.value"
        :tipo-forzato="1"
      />

      <!-- Building block: auth user -->
      <h4>{{ t('amm.section_accesso') }}</h4>
      <AuthUserForm
        :form="auth.form"
        :password-match="auth.passwordMatch.value"
      />

      <!-- Collocazione operatore (specifico dominio) -->
      <h4>{{ t('amm.section_collocazione') }}</h4>
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('amm.field_ruolo') }}</label>
          <Select v-model="collocazione.ruolo_sistema" :options="ruoloOptions"
            option-label="label" option-value="value" class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('amm.field_qualifica') }} *</label>
          <Select v-model="collocazione.qualifica_id"
            :options="qualifiche.items.value"
            :loading="qualifiche.loading.value"
            option-label="descrizione" option-value="id"
            class="w-full" :placeholder="t('amm.select_qualifica')" />
        </div>
        <div class="form-field">
          <label>{{ t('amm.field_reparto') }}</label>
          <Select v-model="collocazione.unita_organizzativa_id"
            :options="unitaOrg.items.value"
            :loading="unitaOrg.loading.value"
            option-label="descrizione" option-value="id"
            class="w-full" :placeholder="t('amm.select_reparto')" />
        </div>
      </div>

      <div class="flex justify-end gap-2 mt-4">
        <Button :label="t('common.cancel')" severity="secondary" @click="onClose" />
        <Button :label="t('common.save')" icon="pi pi-check"
          :loading="loading" @click="onSave" />
      </div>
    </div>
  </Drawer>
</template>

<!-- Stili .form-grid e .form-field definiti in main.css -->
