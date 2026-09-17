<script setup>
// Scopo: Drawer unificato creazione/modifica operatore.
// Sezioni: Soggetto (resolver in crea, banner in modifica),
// Auth (solo crea), Dati anagrafici, Collocazione.
// Tabs: Dati + Permessi (permessi solo in modifica).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOperatoriStore } from '../stores/operatori'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useAuthUser } from '../../core/composables/useAuthUser'
import { useLookup } from '../../core/composables/useLookup'
import { listUnitaOrganizzative, invitaOperatore, reinviaInvito } from '../api/amministrazione'
import { TIPO_RUOLO_CODICE } from '../constants'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
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
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import Tab from 'primevue/tab'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Button from 'primevue/button'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'

const { t } = useI18n()
const store = useOperatoriStore()
const { execute, loading, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()
const injectedReadonly = useInjectReadonly()

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
  authUserId: { type: Number, default: null },
  // Sola lettura CUMULATIVA con quella iniettata (standard drawer admin): il
  // chiamante può imporla anche dove il contesto non la fornisce, e non può
  // toglierla dove il contesto la impone.
  readonly: { type: Boolean, default: false }
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const isReadonly = computed(() => props.readonly || injectedReadonly.value)
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
  activeTab.value = 'dati'
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
      { successMessage: t('amministrazione.operatore_creato') }
    )
    if (result !== null) {
      emit('saved')
    }
  }
}

// Tab attivo. Riportato a 'dati' a ogni apertura del drawer: il tab
// 'permessi' esiste solo in modifica, quindi riaprendo in creazione un
// valore residuo punterebbe a un tab inesistente (nessun pannello reso).
const activeTab = ref('dati')

// ⭐ La larghezza segue il TAB, e non è un vezzo: i due tab chiedono due
// stanze diverse. «Dati» è un form a colonna singola — a 1360px sarebbe una
// riga di campi persi in mezzo al bianco. «Permessi» è una matrice
// slot/override a cinque colonne (voce, ereditato, override, stato, azione)
// per 13 aree, 34 azioni e 12 oggetti: a 800px le colonne si strizzano
// proprio dove la schermata esiste per farsi leggere.
// ℹ️ `XLARGE` è la taglia che la costante dedica alle «matrici
// parametri-per-entità (utility, slot/override)»; il drawer dedicato
// `OperatorePermessiDrawer` usa la stessa.
const larghezzaDrawer = computed(() =>
  activeTab.value === 'permessi' ? DRAWER_WIDTH.XLARGE : DRAWER_WIDTH.COMPLEX
)

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
    title: t('amministrazione.invito_confirm_title'),
    message: isReinvio ? t('amministrazione.reinvio_confirm_msg') : t('amministrazione.invito_confirm_msg'),
    onAccept: async () => {
      invitaLoading.value = true
      try {
        const apiFn = isReinvio ? reinviaInvito : invitaOperatore
        const res = await apiFn(props.authUserId)
        const data = res.data?.data
        const msg = data?.email
          ? t('amministrazione.invito_inviato') + ` (${data.email})`
          : t('amministrazione.invito_inviato')
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

const onClose = useDrawerClose(emit, 'cancelled')
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: larghezzaDrawer }"
    @update:visible="val => emit('update:visible', val)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('amministrazione.operatore')" :icon="NAV_ICONS.OPERATORE" />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="dati">{{ t('amministrazione.tab_dati') }}</Tab>
        <Tab v-if="isEdit" value="permessi">{{ t('amministrazione.tab_permessi') }}</Tab>
      </TabList>
      <TabPanels>
      <TabPanel value="dati">
        <!-- === Sezione Soggetto === -->
        <h4>{{ t('amministrazione.section_persona') }}</h4>

        <!-- Modifica: banner soggetto sola lettura -->
        <div v-if="isEdit && form.soggetto_id">
          <SoggettoMessageBanner
            :ragione-sociale="form.ragione_sociale || `${form.cognome} ${form.nome}`.trim()"
            :id-fiscale="form.codice_fiscale || form.partita_iva"
          />
        </div>

        <!-- Creazione: resolver soggetto -->
        <template v-if="!isEdit">
          <div v-if="soggettoSelezionato">
            <SoggettoMessageBanner
              :ragione-sociale="soggettoSelezionato.ragione_sociale"
              :id-fiscale="soggettoSelezionato.cf || soggettoSelezionato.piva"
            />
            <Button :label="t('resolver.change')" :icon="MANAGE_ICONS.EDIT"
              text size="small" class="mt-1" @click="clearSoggetto" />
          </div>
          <div v-else>
            <Button :label="`${t('resolver.open')} *`" icon="pi pi-search"
              outlined @click="resolverVisible = true" />
          </div>
        </template>

        <!-- === Sezione Auth (solo creazione) === -->
        <template v-if="!isEdit">
          <h4>{{ t('amministrazione.section_accesso') }}</h4>
          <AuthUserForm
            :form="auth.form"
            :password-match="auth.passwordMatch.value"
          />
        </template>

        <!-- === Sezione Dati anagrafici + Collocazione === -->
        <h4 v-if="!isEdit">{{ t('amministrazione.section_collocazione') }}</h4>
        <div class="form-grid">
          <!-- Username + Emittente su stessa riga (solo modifica, sola lettura) -->
          <div v-if="isEdit" class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('common.username') }}</label>
              <InputText :model-value="form.username" disabled />
            </div>
            <div class="form-field">
              <label>{{ t('amministrazione.field_emittente') }}</label>
              <InputText :model-value="form.emittenti_descrizione || '—'" disabled />
            </div>
          </div>

          <!-- Cognome + Nome su stessa riga (solo modifica) -->
          <template v-if="isEdit">
            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('common.cognome') }}</label>
                <InputText v-model="form.cognome"
                  @blur="form.cognome = capitalizeWords(form.cognome)" />
              </div>
              <div class="form-field">
                <label>{{ t('common.nome') }}</label>
                <InputText v-model="form.nome"
                  @blur="form.nome = capitalizeWords(form.nome)" />
              </div>
            </div>
            <div class="form-field">
              <label>{{ t('common.email') }} *</label>
              <InputText v-model="form.email"
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
                  <span>{{ t('amministrazione.is_super_admin.label') }}</span>
                  <small class="operatore-toggle-help">{{ t('amministrazione.is_super_admin.help') }}</small>
                </label>
              </div>
            </div>
            <div class="form-field">
              <div class="operatore-toggle-row">
                <ToggleSwitch v-model="form.attivo" input-id="tg-attivo"
                  :invalid="campiErrati.includes('attivo')"
                />
                <label for="tg-attivo" class="operatore-toggle-label">
                  <span>{{ t('amministrazione.accesso_attivo.label') }}</span>
                  <small class="operatore-toggle-help">{{ t('amministrazione.accesso_attivo.help') }}</small>
                </label>
              </div>
            </div>
          </template>

          <!-- Creazione: toggle SUPER_ADMIN (attivo implicito=true) -->
          <div v-if="!isEdit" class="form-field">
            <div class="operatore-toggle-row">
              <ToggleSwitch v-model="form.is_super_admin" input-id="tg-super-admin-new" />
              <label for="tg-super-admin-new" class="operatore-toggle-label">
                <span>{{ t('amministrazione.is_super_admin.label') }}</span>
                <small class="operatore-toggle-help">{{ t('amministrazione.is_super_admin.help') }}</small>
              </label>
            </div>
          </div>

          <!-- Qualifica: solo creazione -->
          <div v-if="!isEdit" class="form-field">
            <label>{{ t('amministrazione.field_qualifica') }} *</label>
            <LookupSelect v-model="form.qualifica_id"
              rel="config.qualifiche"
              :placeholder="t('amministrazione.select_qualifica')" />
          </div>

          <div class="form-field">
            <label>{{ t('amministrazione.field_reparto') }}</label>
            <Select v-model="form.unita_organizzativa_id"
              :options="unitaOrg.items.value"
              :loading="unitaOrg.loading.value"
              option-label="descrizione" option-value="id"
              :placeholder="t('amministrazione.select_reparto')" />
          </div>

          <!-- Validita' (solo modifica, sola lettura informativa) -->
          <template v-if="isEdit">
            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('amministrazione.field_valido_dal') }}</label>
                <InputText :model-value="form.valido_dal ? displayDate(form.valido_dal) : '—'" disabled />
              </div>
              <div class="form-field">
                <label>{{ t('amministrazione.field_valido_al') }}</label>
                <InputText :model-value="form.valido_al ? displayDate(form.valido_al) : t('amministrazione.valido_al_illimitato')" disabled />
              </div>
            </div>
          </template>
        </div>

        <!-- Invito operatore (solo modifica, mai loggato) -->
        <div v-if="canInvite">
          <Button
            :label="hasBeenInvited ? t('amministrazione.reinvia_invito') : t('amministrazione.invita_operatore')"
            icon="pi pi-envelope"
            :loading="invitaLoading"
            outlined size="small"
            @click="onInvita" />
        </div>

        <!-- Footer Salva/Annulla -->
        <div>
          <FormFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="onClose" />
        </div>
      </TabPanel>

      <!-- Tab Permessi: solo modifica -->
      <TabPanel v-if="isEdit" value="permessi">
        <OperatorePermessiTab :auth-user-id="props.authUserId" :readonly="isReadonly" />
      </TabPanel>
      </TabPanels>
    </Tabs>
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
