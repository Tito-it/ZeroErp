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
import { lookupCodici } from '../../core/apiCore'
import { listUnitaOrganizzative } from '../api/amministrazione'
import { RUOLO_SISTEMA, TIPO_RUOLO_CODICE, buildRuoloOptions } from '../constants'
import { DRAWER_WIDTH } from '../../core/constants'
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
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import { useConfirm } from 'primevue/useconfirm'

const { t } = useI18n()
const store = useOperatoriStore()
const { execute, loading } = useApiHandler()
const confirm = useConfirm()
const notify = useNotify()
const isReadonly = useInjectReadonly()

// Building block: auth user (solo creazione)
const auth = useAuthUser()

// SoggettoResolver: sotto-drawer per cerca/crea soggetto (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)

// Lookup
const qualifiche = useLookup(() => lookupCodici('config.qualifiche'), { immediate: true })
const unitaOrg = useLookup(listUnitaOrganizzative, { immediate: true })

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  authUserId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

const ruoloOptions = buildRuoloOptions(t)

// Form unico per entrambe le modalita'
const form = ref({
  cognome: '',
  nome: '',
  email: '',
  ruolo_sistema: RUOLO_SISTEMA.OPERATIVO,
  qualifica_id: null,
  unita_organizzativa_id: null,
  valido_al: null,
  // Dati soggetto associato (sola lettura)
  soggetto_id: null,
  ragione_sociale: null,
  codice_fiscale: null
})

// Scopo: Reset form a valori iniziali.
function resetForm() {
  soggettoSelezionato.value = null
  auth.reset()
  form.value = {
    cognome: '',
    nome: '',
    email: '',
    ruolo_sistema: RUOLO_SISTEMA.OPERATIVO,
    qualifica_id: null,
    unita_organizzativa_id: null,
    valido_al: null,
    soggetto_id: null,
    ragione_sociale: null,
    codice_fiscale: null
  }
}

// Carica dati quando il drawer si apre
watch(() => props.visible, async (val) => {
  if (!val) return
  // Forza remount TabView dopo che il drawer è visibile (ink bar fix)
  nextTick(() => { tabViewKey.value++ })
  if (isEdit.value && props.authUserId) {
    await store.fetchDetail(props.authUserId)
    const u = store.currentOperatore
    if (u) {
      form.value = {
        cognome: u.soggetto_cognome || u.last_name || '',
        nome: u.soggetto_nome || u.first_name || '',
        email: u.email || '',
        ruolo_sistema: u.ruolo_sistema || RUOLO_SISTEMA.OPERATIVO,
        qualifica_id: null,
        unita_organizzativa_id: u.unita_organizzativa_id,
        valido_al: u.valido_al || null,
        soggetto_id: u.soggetto_id || null,
        ragione_sociale: u.ragione_sociale_completa || null,
        codice_fiscale: u.codice_fiscale || null
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

// Scopo: Salva operatore (crea o aggiorna).
async function onSave() {
  if (isEdit.value) {
    const payload = {
      email: form.value.email,
      first_name: form.value.nome,
      last_name: form.value.cognome,
      ruolo_sistema: form.value.ruolo_sistema,
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
    const payload = {
      soggetto_id: sogg?.id || null,
      cognome: sogg?.cognome || null,
      nome: sogg?.nome || null,
      email: auth.form.email,
      username: auth.form.username,
      password: auth.form.password,
      ruolo_sistema: form.value.ruolo_sistema,
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

const isDisabilitato = computed(() => form.value.ruolo_sistema === RUOLO_SISTEMA.DISABILITATO)

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
  && !!form.value.ruolo_sistema
)

const canSave = computed(() => isEdit.value ? canSaveEdit.value : canSaveCreate.value)

async function eseguiToggleStato() {
  if (isDisabilitato.value) {
    const result = await execute(
      () => store.riattiva(props.authUserId),
      { successMessage: t('amm.operatore_riattivato') }
    )
    if (result !== null) {
      emit('saved')
    }
  } else {
    const result = await execute(
      () => store.disabilita(props.authUserId),
      { successMessage: t('amm.operatore_disabilitato') }
    )
    if (result !== null) {
      emit('saved')
    }
  }
}

function onToggleStato() {
  confirm.require({
    message: isDisabilitato.value ? t('amm.riattiva_confirm') : t('amm.disabilita_confirm'),
    header: isDisabilitato.value ? t('amm.riattiva_title') : t('amm.disabilita_title'),
    icon: isDisabilitato.value ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-success',
    rejectClass: 'p-button-secondary',
    accept: eseguiToggleStato
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
            <Button :label="t('resolver.change')" icon="pi pi-pencil"
              text size="small" class="mt-1" @click="clearSoggetto" />
          </div>
          <div v-else>
            <Button :label="t('resolver.open')" icon="pi pi-search"
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
          <!-- Cognome / Nome (solo modifica — in creazione vengono dal soggetto) -->
          <template v-if="isEdit">
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
            <div class="form-field">
              <label>{{ t('common.email') }}</label>
              <InputText v-model="form.email" class="w-full" />
            </div>
          </template>

          <div class="form-field">
            <label>{{ t('amm.field_ruolo') }}</label>
            <Select v-model="form.ruolo_sistema" :options="ruoloOptions"
              option-label="label" option-value="value" class="w-full" />
          </div>

          <!-- Qualifica: solo creazione -->
          <div v-if="!isEdit" class="form-field">
            <label>{{ t('amm.field_qualifica') }} *</label>
            <Select v-model="form.qualifica_id"
              :options="qualifiche.items.value"
              :loading="qualifiche.loading.value"
              option-label="descrizione" option-value="id"
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

          <!-- Valido al: solo modifica (sola lettura) -->
          <div v-if="isEdit" class="form-field">
            <label>{{ t('amm.field_valido_al') }}</label>
            <InputText :model-value="form.valido_al ? displayDate(form.valido_al) : t('amm.valido_al_illimitato')" disabled class="w-full" />
          </div>
        </div>

        <!-- Azioni footer -->
        <div class="flex justify-between mt-4">
          <Button v-if="isEdit"
            :label="isDisabilitato ? t('amm.riattiva_operatore') : t('amm.disabilita_operatore')"
            :severity="isDisabilitato ? 'success' : 'danger'"
            :icon="isDisabilitato ? 'pi pi-check-circle' : 'pi pi-ban'"
            outlined @click="onToggleStato" />
          <span v-else />
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

<!-- Stili .form-grid e .form-field definiti in main.css -->
