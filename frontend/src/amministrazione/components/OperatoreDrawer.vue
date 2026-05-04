<script setup>
// Scopo: Drawer unificato creazione/modifica operatore.
// Sezioni: Soggetto (resolver in crea, banner in modifica),
// Auth (solo crea), Dati anagrafici, Collocazione.
// TabView: Dati + Permessi (permessi solo in modifica).
import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOperatoriStore } from '../stores/operatori'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useAuthUser } from '../../core/composables/useAuthUser'
import { useLookup } from '../../core/composables/useLookup'
import { listUnitaOrganizzative, invitaOperatore, reinviaInvito } from '../api/amministrazione'
import { TIPO_RUOLO_CODICE } from '../constants'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { capitalizeWords } from '../../core/utils/string'
import { isEmailValid } from '../../core/utils/validators'
import { useNotify } from '../../core/composables/useNotify'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import SoggettoResolver from '../../core/components/SoggettoResolver.vue'
import SoggettoMessageBanner from '../../core/components/SoggettoMessageBanner.vue'
import AuthUserForm from '../../core/components/AuthUserForm.vue'
import OperatorePermessiTab from './OperatorePermessiTab.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import { useConfirmAction } from '../../core/composables/useConfirmAction'

const { t } = useI18n()
const store = useOperatoriStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()
const isReadonly = useInjectReadonly()

// Building block: auth user (solo creazione)
const auth = useAuthUser()

// SoggettoResolver: sotto-drawer per cerca/crea soggetto (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)

// Lookup
const unitaOrg = useLookup(listUnitaOrganizzative, { immediate: true })

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  authUserId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const invitaLoading = ref(false)
const emailEditInvalid = ref(false)

// Scopo: Mostra pulsante invito se operatore non ha mai fatto login.
const canInvite = computed(() => {
  const u = store.currentOperatore
  return isEdit.value && u && !u.last_login && u.is_active
})
const hasBeenInvited = computed(() => !!store.currentOperatore?.invito_inviato_at)

// Multi-face auth Stage B: il vecchio radio ruolo_sistema (ADMIN/OPERATIVO/
// DISABILITATO) e' sostituito da due toggle indipendenti:
//   - is_super_admin: binding al profilo SUPER_ADMIN (id 9100)
//   - attivo:         stato operativo dell'identita' digitale
// Il ruolo applicativo resta implicito = OPERATORE per questo drawer
// (operatori interni). Portali e shop useranno drawer dedicati.
const INITIAL_FORM = Object.freeze({
  cognome: '',
  nome: '',
  email: '',
  is_super_admin: false,
  attivo: true,
  qualifica_id: null,
  unita_organizzativa_id: null,
  valido_dal: null,
  valido_al: null,
  soggetto_id: null,
  ragione_sociale: null,
  codice_fiscale: null
})

const form = ref({ ...INITIAL_FORM })

// Scopo: Reset form a valori iniziali.
function resetForm() {
  soggettoSelezionato.value = null
  emailEditInvalid.value = false
  auth.reset()
  form.value = { ...INITIAL_FORM }
}

// Carica dati quando il drawer si apre
watch(() => props.visible, async (val) => {
  if (!val) return
  emailEditInvalid.value = false
  // Forza remount TabView dopo che il drawer è visibile (ink bar fix)
  nextTick(() => { tabViewKey.value++ })
  if (isEdit.value && props.authUserId) {
    await store.fetchDetail(props.authUserId)
    const u = store.currentOperatore
    if (u) {
      form.value = {
        username: u.username || '',
        cognome: u.soggetto_cognome || u.last_name || '',
        nome: u.soggetto_nome || u.first_name || '',
        email: u.email || '',
        // Multi-face auth: i flag nativi vengono dal BE (is_super_admin +
        // attivo del detail). Fallback difensivo su is_active per setup
        // vecchi che non hanno ancora aggiornato la proiezione.
        is_super_admin: u.is_super_admin === true,
        attivo: u.attivo !== undefined ? !!u.attivo : !!u.is_active,
        qualifica_id: null,
        unita_organizzativa_id: u.unita_organizzativa_id,
        valido_dal: u.valido_dal || null,
        valido_al: u.valido_al || null,
        soggetto_id: u.soggetto_id || null,
        ragione_sociale: u.ragione_sociale_completa || null,
        codice_fiscale: u.codice_fiscale || null,
        emittenti_descrizione: u.emittenti_descrizione || ''
      }
    }
  } else {
    resetForm()
  }
})

// Scopo: Pre-compila email dal soggetto se il campo auth e' vuoto.
function prefillEmail(data) {
  if (data.email && !auth.form.email) {
    auth.form.email = data.email
  }
}

function onSoggettoSelezionato(data) {
  soggettoSelezionato.value = data
  prefillEmail(data)
}

function onSoggettoCreato(data) {
  soggettoSelezionato.value = data
  prefillEmail(data)
}

function clearSoggetto() {
  soggettoSelezionato.value = null
}

// Scopo: Valida il formato email in modifica usando il building block condiviso.
function validateEditEmail() {
  emailEditInvalid.value = !!form.value.email?.trim() && !isEmailValid(form.value.email)
}

// Scopo: Rimuove lo stato errore mentre l'utente corregge il campo email.
function clearEditEmailInvalid() {
  if (emailEditInvalid.value) emailEditInvalid.value = false
}

// Scopo: Salva operatore (crea o aggiorna).
// Contract multi-face (Fase 7): {is_super_admin, attivo, ...}. Il backend
// gestisce binding SUPER_ADMIN + stato identita_digitali in modo
// ortogonale tra i due flag.
async function onSave() {
  if (isEdit.value) {
    const payload = {
      email: form.value.email,
      first_name: form.value.nome,
      last_name: form.value.cognome,
      is_super_admin: form.value.is_super_admin,
      attivo: form.value.attivo,
      unita_organizzativa_id: form.value.unita_organizzativa_id
    }
    const result = await execute(
      () => store.update(props.authUserId, payload),
      { successMessage: t('notifications.save_success') }
    )
    if (result !== null) {
      emit('saved')
    }
  } else {
    // Validazione client-side per creazione
    const authErrors = auth.validate()
    if (!form.value.qualifica_id) authErrors.push('qualifica_id')
    if (authErrors.length) {
      notify.error(t('notifications.validation_error'))
      return
    }

    const sogg = soggettoSelezionato.value
    // Contract multi-face (Fase 7): il payload create accetta `is_super_admin`
    // direttamente. Il BE rifiuta `ruolo_sistema` con E_AMM_VALIDAZIONE.
    // L'utente creato e' sempre attivo (la disabilitazione passa dal comando
    // dedicato `/disabilita/` in un secondo momento).
    const payload = {
      soggetto_id: sogg?.id || null,
      cognome: sogg?.cognome || null,
      nome: sogg?.nome || null,
      email: auth.form.email,
      username: auth.form.username,
      password: auth.form.password,
      is_super_admin: form.value.is_super_admin,
      qualifica_id: form.value.qualifica_id,
      unita_organizzativa_id: form.value.unita_organizzativa_id
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('amm.operatore_creato') }
    )
    if (result !== null) {
      emit('saved')
    }
  }
}

// Scopo: forza remount TabView dopo apertura drawer per ink bar
const tabViewKey = ref(0)

// Computed: form creazione completo
const canSaveCreate = computed(() =>
  !!soggettoSelezionato.value
  && !!auth.form.username.trim()
  && isEmailValid(auth.form.email)
  && !!auth.form.password
  && auth.passwordMatch.value
  && !!form.value.qualifica_id
)

// Computed: form modifica completo
const canSaveEdit = computed(() =>
  isEmailValid(form.value.email)
)

const canSave = computed(() => isEdit.value ? canSaveEdit.value : canSaveCreate.value)

// Scopo: Invia o reinvia invito operatore con conferma.
function onInvita() {
  const isReinvio = hasBeenInvited.value
  confirmAction({
    title: t('amm.invito_confirm_title'),
    message: isReinvio ? t('amm.reinvio_confirm_msg') : t('amm.invito_confirm_msg'),
    onAccept: async () => {
      invitaLoading.value = true
      try {
        const apiFn = isReinvio ? reinviaInvito : invitaOperatore
        const res = await apiFn(props.authUserId)
        const data = res.data?.data
        const msg = data?.email
          ? t('amm.invito_inviato') + ` (${data.email})`
          : t('amm.invito_inviato')
        notify.success(msg)
        // Ricarica dettaglio per aggiornare invito_inviato_at
        await store.fetchDetail(props.authUserId)
      } catch (err) {
        const errMsg = err?.response?.data?.error?.message || t('common.error')
        notify.error(errMsg)
      } finally {
        invitaLoading.value = false
      }
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
    @update:visible="val => emit('update:visible', val)"
  >
    <template #header>
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('amm.operatore')" icon="pi pi-user" />
    </template>

    <div :class="{ 'app-readonly': isReadonly }">
    <TabView :key="tabViewKey">
      <TabPanel :header="t('amm.tab_dati')">
        <!-- === Sezione Soggetto === -->
        <h4>{{ t('amm.section_persona') }}</h4>

        <!-- Modifica: banner soggetto sola lettura -->
        <div v-if="isEdit && form.soggetto_id" class="mb-3">
          <SoggettoMessageBanner
            :ragione-sociale="form.ragione_sociale || `${form.cognome} ${form.nome}`.trim()"
            :codice-fiscale="form.codice_fiscale"
          />
        </div>

        <!-- Creazione: resolver soggetto -->
        <template v-if="!isEdit">
          <div v-if="soggettoSelezionato" class="mb-3">
            <SoggettoMessageBanner
              :ragione-sociale="soggettoSelezionato.ragione_sociale"
              :codice-fiscale="soggettoSelezionato.cf"
            />
            <Button :label="t('resolver.change')" :icon="MANAGE_ICONS.EDIT"
              text size="small" class="mt-1" @click="clearSoggetto" />
          </div>
          <div v-else>
            <Button :label="`${t('resolver.open')} *`" icon="pi pi-search"
              outlined class="w-full" @click="resolverVisible = true" />
          </div>
        </template>

        <!-- === Sezione Auth (solo creazione) === -->
        <template v-if="!isEdit">
          <h4 class="mt-3">{{ t('amm.section_accesso') }}</h4>
          <AuthUserForm
            :form="auth.form"
            :password-match="auth.passwordMatch.value"
          />
        </template>

        <!-- === Sezione Dati anagrafici + Collocazione === -->
        <h4 v-if="!isEdit" class="mt-3">{{ t('amm.section_collocazione') }}</h4>
        <div class="form-grid">
          <!-- Username + Emittente su stessa riga (solo modifica, sola lettura) -->
          <div v-if="isEdit" class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('common.username') }}</label>
              <InputText :model-value="form.username" disabled class="w-full" />
            </div>
            <div class="form-field">
              <label>{{ t('amm.field_emittente') }}</label>
              <InputText :model-value="form.emittenti_descrizione || '—'" disabled class="w-full" />
            </div>
          </div>

          <!-- Cognome + Nome su stessa riga (solo modifica) -->
          <template v-if="isEdit">
            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('common.cognome') }}</label>
                <InputText v-model="form.cognome" class="w-full"
                  @blur="form.cognome = capitalizeWords(form.cognome)" />
              </div>
              <div class="form-field">
                <label>{{ t('common.nome') }}</label>
                <InputText v-model="form.nome" class="w-full"
                  @blur="form.nome = capitalizeWords(form.nome)" />
              </div>
            </div>
            <div class="form-field">
              <label>{{ t('common.email') }} *</label>
              <InputText v-model="form.email" class="w-full"
                :invalid="emailEditInvalid"
                @blur="validateEditEmail"
                @input="clearEditEmailInvalid" />
              <small v-if="emailEditInvalid" class="app-field-error">
                {{ t('validation.email_format') }}
              </small>
            </div>
          </template>

          <!-- Stato operatore (solo modifica): 2 toggle indipendenti -->
          <template v-if="isEdit">
            <div class="form-field">
              <div class="operatore-toggle-row">
                <ToggleSwitch v-model="form.is_super_admin" input-id="tg-super-admin" />
                <label for="tg-super-admin" class="operatore-toggle-label">
                  <span>{{ t('amm.is_super_admin.label') }}</span>
                  <small class="operatore-toggle-help">{{ t('amm.is_super_admin.help') }}</small>
                </label>
              </div>
            </div>
            <div class="form-field">
              <div class="operatore-toggle-row">
                <ToggleSwitch v-model="form.attivo" input-id="tg-attivo" />
                <label for="tg-attivo" class="operatore-toggle-label">
                  <span>{{ t('amm.accesso_attivo.label') }}</span>
                  <small class="operatore-toggle-help">{{ t('amm.accesso_attivo.help') }}</small>
                </label>
              </div>
            </div>
          </template>

          <!-- Creazione: toggle SUPER_ADMIN (attivo implicito=true) -->
          <div v-if="!isEdit" class="form-field">
            <div class="operatore-toggle-row">
              <ToggleSwitch v-model="form.is_super_admin" input-id="tg-super-admin-new" />
              <label for="tg-super-admin-new" class="operatore-toggle-label">
                <span>{{ t('amm.is_super_admin.label') }}</span>
                <small class="operatore-toggle-help">{{ t('amm.is_super_admin.help') }}</small>
              </label>
            </div>
          </div>

          <!-- Qualifica: solo creazione -->
          <div v-if="!isEdit" class="form-field">
            <label>{{ t('amm.field_qualifica') }} *</label>
            <LookupSelect v-model="form.qualifica_id"
              rel="config.qualifiche"
              class="w-full" :placeholder="t('amm.select_qualifica')" />
          </div>

          <div class="form-field">
            <label>{{ t('amm.field_reparto') }}</label>
            <Select v-model="form.unita_organizzativa_id"
              :options="unitaOrg.items.value"
              :loading="unitaOrg.loading.value"
              option-label="descrizione" option-value="id"
              class="w-full" :placeholder="t('amm.select_reparto')" />
          </div>

          <!-- Validita' (solo modifica, sola lettura informativa) -->
          <template v-if="isEdit">
            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('amm.field_valido_dal') }}</label>
                <InputText :model-value="form.valido_dal ? displayDate(form.valido_dal) : '—'" disabled class="w-full" />
              </div>
              <div class="form-field">
                <label>{{ t('amm.field_valido_al') }}</label>
                <InputText :model-value="form.valido_al ? displayDate(form.valido_al) : t('amm.valido_al_illimitato')" disabled class="w-full" />
              </div>
            </div>
          </template>
        </div>

        <!-- Invito operatore (solo modifica, mai loggato) -->
        <div v-if="canInvite" class="mt-3">
          <Button
            :label="hasBeenInvited ? t('amm.reinvia_invito') : t('amm.invita_operatore')"
            icon="pi pi-envelope"
            :loading="invitaLoading"
            outlined size="small"
            @click="onInvita" />
        </div>

        <!-- Footer Salva/Annulla -->
        <div class="flex justify-end mt-4">
          <DrawerFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="onClose" />
        </div>
      </TabPanel>

      <!-- Tab Permessi: solo modifica -->
      <TabPanel v-if="isEdit" :header="t('amm.tab_permessi')">
        <OperatorePermessiTab :auth-user-id="props.authUserId" />
      </TabPanel>
    </TabView>
    </div>

    <!-- Sotto-drawer: SoggettoResolver (solo creazione) -->
    <SoggettoResolver
      v-if="!isEdit"
      :visible="resolverVisible"
      :tipo-ruolo-codice="TIPO_RUOLO_CODICE.RIS_UMANA"
      @update:visible="v => resolverVisible = v"
      @soggetto-selezionato="onSoggettoSelezionato"
      @soggetto-creato="onSoggettoCreato"
      @annullato="resolverVisible = false"
    />
  </Drawer>
</template>

<style scoped>
/* Toggle stato operatore: switch + label con riga helper */
.operatore-toggle-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.operatore-toggle-label {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  cursor: pointer;
}
.operatore-toggle-help {
  font-size: 0.78rem;
  color: var(--app-text-muted, var(--p-text-muted-color));
}
</style>

<!-- Stili .form-grid e .form-field definiti in main.css -->
