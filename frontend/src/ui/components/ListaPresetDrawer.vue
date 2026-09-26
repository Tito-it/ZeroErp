<script setup>
// Scopo: Drawer crea/modifica testata preset (`ui.lista_preset`).
//        Pattern standard:
//          - DrawerTitle (auto-include ReadonlyBadge se readonly)
//          - app-readonly su contenuto se isReadonly OR props.readonly
//          - FormFooter standard (Salva nascosto in readonly)
//          - Refs profilo/emittente condizionali ad ambito
//        Lookup profili_accesso e emittenti_fiscali via LookupSelect /
//        endpoint dedicato (admin only). Per tenere il componente minimale
//        e Fase 1 minimal, qui uso 2 InputNumber (id) — il super-admin
//        sa gli id; in Fase 2 si possono sostituire con autocomplete
//        ricchi senza cambiare il contratto del drawer.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { DRAWER_WIDTH } from '../../core/constants'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerFormPreserve, gestoreVisibile } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useUiPresetAdminStore } from '../stores/uiPresetAdmin'



const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
  recordId: { type: Number, default: null },
  recordData: { type: Object, default: null },
  listaId: { type: Number, default: null },
  readonly: { type: Boolean, default: false },
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const { t } = useI18n()
const presetStore = useUiPresetAdminStore()
const { execute, loading, campiErrati } = useApiHandler()

const injectedReadonly = useInjectReadonly()
const isReadonlyEffective = computed(
  () => props.readonly || injectedReadonly.value,
)
const isEdit = computed(() => props.mode === 'edit')

const ambitiOptions = computed(() => [
  { label: t('ui.admin.preset_ambito_sistema'), value: 'sistema' },
  { label: t('ui.admin.preset_ambito_emittente_fiscale'), value: 'emittente_fiscale' },
  { label: t('ui.admin.preset_ambito_ruolo'), value: 'ruolo' },
])

function defaultForm() {
  return {
    codice: '',
    descrizione: '',
    ambito: 'sistema',
    profilo_accesso_id: null,
    emittente_fiscale_id: null,
    is_default: false,
    pagina_dimensione: null,
    attivo: true,
  }
}

const form = ref(defaultForm())
// Modifiche non salvate: fotografia a form popolato, conferma alla chiusura
// (BB useDrawerFormPreserve). Prima del watch immediate (TDZ).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

// Watch su props.recordData per pre-popolare il form in edit. Usa la
// risposta admin che include gia' tutti i campi.
watch(
  () => [props.visible, props.recordData],
  ([visible, data]) => {
    if (!visible) return
    if (isEdit.value && data) {
      form.value = {
        codice: data.codice ?? '',
        descrizione: data.descrizione ?? '',
        ambito: data.ambito ?? 'sistema',
        profilo_accesso_id: data.profilo_accesso_id ?? null,
        emittente_fiscale_id: data.emittente_fiscale_id ?? null,
        is_default: !!data.is_default,
        pagina_dimensione: data.pagina_dimensione ?? null,
        attivo: !!data.attivo,
      }
    } else {
      form.value = defaultForm()
    }
    fissa()
  },
  { immediate: true },
)

// Reset refs quando cambia ambito (UX coerenza con CHECK ambito_refs DB).
watch(() => form.value.ambito, (nuovo) => {
  if (nuovo === 'sistema') {
    form.value.profilo_accesso_id = null
    form.value.emittente_fiscale_id = null
  } else if (nuovo === 'ruolo') {
    form.value.emittente_fiscale_id = null
  } else if (nuovo === 'emittente_fiscale') {
    form.value.profilo_accesso_id = null
  }
})

const canSave = computed(() => {
  if (!form.value.codice?.trim()) return false
  if (!form.value.descrizione?.trim()) return false
  if (!form.value.ambito) return false
  if (form.value.ambito === 'ruolo' && !form.value.profilo_accesso_id) return false
  if (form.value.ambito === 'emittente_fiscale' && !form.value.emittente_fiscale_id) return false
  return true
})

function buildPayload() {
  const payload = {
    codice: form.value.codice.trim(),
    descrizione: form.value.descrizione.trim(),
    is_default: form.value.is_default,
    attivo: form.value.attivo,
  }
  if (form.value.pagina_dimensione != null) {
    payload.pagina_dimensione = form.value.pagina_dimensione
  }
  if (!isEdit.value) {
    // Campi immutabili: solo in create.
    payload.ambito = form.value.ambito
    if (form.value.ambito === 'ruolo') {
      payload.profilo_accesso_id = form.value.profilo_accesso_id
    } else if (form.value.ambito === 'emittente_fiscale') {
      payload.emittente_fiscale_id = form.value.emittente_fiscale_id
    }
  }
  return payload
}

async function onSave() {
  if (!canSave.value) return
  const payload = buildPayload()
  let result
  if (isEdit.value) {
    result = await execute(
      () => presetStore.update(props.recordId, payload),
      { successMessage: t('notifications.save_success') },
    )
  } else {
    result = await execute(
      () => presetStore.create(props.listaId, payload),
      { successMessage: t('notifications.save_success') },
    )
  }
  if (result !== null) {
    emit('saved', result)
  }
}

function onCancel() {
  emit('cancelled')
  emit('update:visible', false)
}
const chiudi = () => chiudiConConferma(onCancel)
const suVisibile = gestoreVisibile(emit, chiudi)
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="suVisibile"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :modal="true"
    :dismissable-mask="false"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :modificato="modificato"
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('ui.admin.preset')"
        icon="pi pi-th-large"
      />
    </template>

    <div v-if="contentReady"
      class="app-drawer-content"
      :class="{ 'app-readonly': isReadonlyEffective }"
    >
      <div class="form-grid">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('ui.admin.preset_codice') }}</label>
            <InputText v-model="form.codice" maxlength="80"
              :invalid="campiErrati.includes('codice')"
            />
          </div>
          <div class="form-field">
            <label>{{ t('ui.admin.preset_pagina_dimensione') }}</label>
            <InputNumber
              v-model="form.pagina_dimensione"
              :min="1"
              :max="500"
              show-buttons
              :invalid="campiErrati.includes('pagina_dimensione')"
            />
          </div>
        </div>

        <div class="form-field">
          <label>{{ t('ui.admin.preset_descrizione') }}</label>
          <InputText v-model="form.descrizione" maxlength="200"
            :invalid="campiErrati.includes('descrizione')"
          />
        </div>

        <div class="form-field">
          <label>{{ t('ui.admin.preset_ambito') }}</label>
          <Select
            v-model="form.ambito"
            :options="ambitiOptions"
            option-label="label"
            option-value="value"
            :disabled="isEdit"
            :invalid="campiErrati.includes('ambito')"
          />
          <Message
            v-if="isEdit"
            severity="info"
            :closable="false"
            size="small"
            class="mt-025"
          >
            {{ t('ui.admin.preset_ambito_immutabile') }}
          </Message>
        </div>

        <div v-if="form.ambito === 'ruolo'" class="form-field">
          <label>{{ t('ui.admin.preset_profilo_accesso') }}</label>
          <LookupSelect
            v-if="!isEdit"
            v-model="form.profilo_accesso_id"
            rel="config.profili_accesso"
            show-code
            :placeholder="t('ui.admin.preset_seleziona_profilo')"
          />
          <InputText
            v-else
            :model-value="recordData?.profilo_accesso_codice ?? ''"
            readonly
          />
        </div>
        <div v-else-if="form.ambito === 'emittente_fiscale'" class="form-field">
          <label>{{ t('ui.admin.preset_emittente_fiscale') }}</label>
          <!-- emittenti_fiscali non e' nella whitelist lookup generico
               (campi non standard); manteniamo InputNumber per ora.
               Fase 2: switch a EmittenteFiscaleField (gia' building block). -->
          <InputNumber
            v-if="!isEdit"
            v-model="form.emittente_fiscale_id"
            :min="1"
            show-buttons
            :invalid="campiErrati.includes('emittente_fiscale_id')"
          />
          <InputText
            v-else
            :model-value="recordData?.emittente_fiscale_codice ?? ''"
            readonly
          />
        </div>

        <div class="form-grid-2col">
          <div class="form-field form-field-inline">
            <Checkbox v-model="form.is_default" binary input-id="ui-preset-default"
              :invalid="campiErrati.includes('is_default')"
            />
            <label for="ui-preset-default">{{ t('ui.admin.preset_is_default') }}</label>
          </div>
          <div class="form-field form-field-inline">
            <Checkbox v-model="form.attivo" binary input-id="ui-preset-attivo"
              :invalid="campiErrati.includes('attivo')"
            />
            <label for="ui-preset-attivo">{{ t('common.active') }}</label>
          </div>
        </div>
      </div>
    </div>

    <FormFooter
      v-if="!isReadonlyEffective"
      :loading="loading"
      :disabled="!canSave"
      @save="onSave"
      @cancel="chiudi"
    />
  </Drawer>
</template>

<style scoped>
.form-field-inline {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}
</style>
