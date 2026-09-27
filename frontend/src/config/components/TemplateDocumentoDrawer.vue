<script setup>
// Scopo: Drawer crea/modifica testata template documentale (Tranche L).
//        - In create: tutti i campi editabili. Immutabili dopo create:
//          tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id
//          (chiave logica del template). Update li rifiuta a livello service
//          BE con messaggio parlante.
//        - In edit: la sezione versioni e' visibile e usabile. In create
//          viene nascosta (non si possono creare versioni se la testata
//          non esiste ancora — workaround del pattern auto-save BOZZA
//          rimandato a future iterazioni).
//        - Sola lettura: prop `readonly` cumulativa con useInjectReadonly.
//
//        Dropdown lookup standard:
//          - tipi_documento_output, sorgenti, render_engine via LookupSelect
//            (lista del lookup `config.tabelle_gestibili`);
//          - context_builder_code via dropdown hardcoded (whitelist
//            applicativa Decisione 18+74).
//        Emittente fiscale: gestito da `useEmittenteFiscaleField`. Per
//        l'operatore standard (1-a-1 col proprio emittente) il valore e'
//        derivato dal profilo e mostrato read-only; per l'admin globale
//        compare un Select popolato dal lookup admin esistente.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateDocumentiStore } from '../stores/templateDocumenti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerFormPreserve, gestoreVisibile, unisciFotografie } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useEmittenteFiscaleField } from '../../core/composables/useEmittenteFiscaleField'
import { DRAWER_WIDTH } from '../../core/constants'
import { contextBuilderOptions } from '../constants/documentiContextBuilders'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import EmittenteFiscaleField from '../../core/components/EmittenteFiscaleField.vue'
import TemplateVersioniSection from './TemplateVersioniSection.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'
import Divider from 'primevue/divider'



const { t } = useI18n()
const store = useTemplateDocumentiStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()
const { defaultEmittenteId } = useEmittenteFiscaleField()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  recordId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

// `mode` evolve da create a edit dopo il primo save (memoria
// feedback_drawer_create_autosave_bozza).
const localMode = ref(props.mode)
const createdId = ref(null)
const isEdit = computed(() => localMode.value === 'edit' || createdId.value !== null)
const isReadOnlyEffective = computed(() => props.readonly || isReadonly.value)
const effectiveId = computed(() => props.recordId || createdId.value)

const contextBuilderOpts = computed(() => contextBuilderOptions(t))

// Scopo: Avviso quando l'operatore seleziona un builder non ancora
//        registrato lato BE (whitelist applicativa Decisione 18+74).
//        Il template e' creabile, ma la generazione documento sollevera'
//        E_DOCUMENTI_VALIDATION finche' un dominio sorgente non registra
//        il builder corrispondente.
const selectedContextBuilderInfo = computed(() => {
  const code = form.value.context_builder_code
  if (!code) return null
  return contextBuilderOpts.value.find(o => o.code === code) || null
})
const isSelectedBuilderUnregistered = computed(() =>
  selectedContextBuilderInfo.value?.registered === false,
)

// Aggiornato via `@form-aperto` da TemplateVersioniSection: quando l'utente
// e' nel form inline di nuova/modifica versione, nascondiamo la FormFooter
// del drawer template (i suoi pulsanti non salvano la versione e creano
// confusione). Stesso pattern di PreventiviDrawer/PreventiviRigheTable.
const formVersioneAperto = ref(false)
// L'emittente del template LETTO (non quello del form): e' il padre della
// lista delle versioni. Il form, riaprendo un altro template, tiene i valori
// del precedente finche' il dettaglio non arriva — la lista partirebbe col
// padre vecchio e ripartirebbe da capo un attimo dopo. `null` = in attesa.
const emittenteLetto = ref(null)

const form = ref(emptyForm())
// Modifiche non salvate della testata: fotografia a form popolato, conferma
// alla chiusura (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })
function emptyForm() {
  return {
    codice: '',
    codice_interno: '',
    descrizione: '',
    tipo_documento_output_id: null,
    sorgente_tipo_id: null,
    emittente_fiscale_id: null,
    // Denormalizzati dal payload BE (list/detail JOIN). Servono solo per
    // il display read-only in edit; non sono inviati nel payload.
    emittente_fiscale_codice: null,
    emittente_ragione_sociale: null,
    context_builder_code: '',
    file_name_pattern: '',
    is_default: false,
    attivo: true,
  }
}

async function loadDetail() {
  if (!effectiveId.value) return
  const data = await store.fetchDetail(effectiveId.value)
  if (!data) return
  emittenteLetto.value = data.emittente_fiscale_id ?? null
  form.value = {
    codice: data.codice ?? '',
    codice_interno: data.codice_interno ?? '',
    descrizione: data.descrizione ?? '',
    tipo_documento_output_id: data.tipo_documento_output_id ?? null,
    sorgente_tipo_id: data.sorgente_tipo_id ?? null,
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    emittente_fiscale_codice: data.emittente_fiscale_codice ?? null,
    emittente_ragione_sociale: data.emittente_ragione_sociale ?? null,
    context_builder_code: data.context_builder_code ?? '',
    file_name_pattern: data.file_name_pattern ?? '',
    is_default: data.is_default ?? false,
    attivo: data.attivo ?? true,
  }
  fissa()
}

watch(
  [() => props.visible, () => props.recordId, () => props.mode],
  ([visible, , mode]) => {
    if (!visible) return
    localMode.value = mode
    createdId.value = null
    emittenteLetto.value = null
    if (mode === 'edit') {
      loadDetail()
    } else {
      form.value = emptyForm()
      // Autopopulate centralizzato dal composable: null per admin
      // globale (sceglie via Select), id derivato dal profilo per
      // operatore standard. EmittenteFiscaleField si occupa del
      // lazy load del lookup admin quando reso.
      form.value.emittente_fiscale_id = defaultEmittenteId.value
      fissa()
    }
  },
)

const canSave = computed(() => {
  if (isReadOnlyEffective.value) return false
  const f = form.value
  if (!f.codice?.trim()) return false
  if (!f.codice_interno?.trim()) return false
  if (!f.descrizione?.trim()) return false
  if (!f.context_builder_code) return false
  if (!isEdit.value) {
    // immutabili obbligatori solo in create
    if (!f.tipo_documento_output_id) return false
    if (!f.sorgente_tipo_id) return false
    if (!f.emittente_fiscale_id) return false
  }
  return true
})

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {
      codice: f.codice.trim(),
      codice_interno: f.codice_interno.trim(),
      descrizione: f.descrizione.trim(),
      context_builder_code: f.context_builder_code,
      file_name_pattern: f.file_name_pattern?.trim() || null,
      is_default: f.is_default,
      attivo: f.attivo,
    }
    const result = await execute(
      () => store.update(effectiveId.value, payload),
      { successMessage: t('config.modelli_documenti.saved') },
    )
    if (result !== null) {
      // Resta aperto senza ricaricare: la fotografia diventa il salvato.
      fissa()
      emit('saved', result)
    }
  } else {
    const payload = {
      codice: f.codice.trim(),
      codice_interno: f.codice_interno.trim(),
      descrizione: f.descrizione.trim(),
      tipo_documento_output_id: f.tipo_documento_output_id,
      sorgente_tipo_id: f.sorgente_tipo_id,
      emittente_fiscale_id: f.emittente_fiscale_id,
      context_builder_code: f.context_builder_code,
      file_name_pattern: f.file_name_pattern?.trim() || null,
      is_default: f.is_default,
      attivo: f.attivo,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('config.modelli_documenti.created') },
    )
    if (result !== null) {
      // Pattern edit-evolved: dopo create rimaniamo nel drawer in mode edit
      // per consentire la gestione versioni. La lista padre viene aggiornata
      // tramite emit 'saved'.
      createdId.value = result.id
      // Il template appena salvato ha l'emittente scelto nel form: e' il
      // padre della lista delle versioni, che senza resterebbe in attesa.
      emittenteLetto.value = result.emittente_fiscale_id ?? payload.emittente_fiscale_id ?? null
      localMode.value = 'edit'
      fissa()
      emit('saved', result)
    }
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
// Il form inline delle versioni (sezione figlia) ha la sua fotografia: la
// chiusura chiede conferma se UNO dei due e' modificato, con un dialog solo.
const versioniRef = ref(null)
const { modificato: modificatoTutto, chiudiConConferma: chiudiTutto } =
  unisciFotografie({ modificato, chiudiConConferma }, () => versioniRef.value)
const chiudi = () => chiudiTutto(close)
const suVisibile = gestoreVisibile(emit, chiudi)
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="suVisibile"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    :dismissable="true"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :modificato="modificatoTutto"
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('config.modelli_documenti.drawer_title')"
      />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadOnlyEffective }">
      <div class="form-grid">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('config.modelli_documenti.field_codice') }} *</label>
            <InputText v-model="form.codice" :disabled="isReadOnlyEffective" maxlength="120" fluid
              :invalid="campiErrati.includes('codice')"
            />
          </div>
          <div class="form-field">
            <label>{{ t('config.modelli_documenti.field_codice_interno') }} *</label>
            <InputText v-model="form.codice_interno" :disabled="isReadOnlyEffective" maxlength="120" fluid
              :invalid="campiErrati.includes('codice_interno')"
            />
          </div>
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.field_descrizione') }} *</label>
          <InputText v-model="form.descrizione" :disabled="isReadOnlyEffective" maxlength="500" fluid
            :invalid="campiErrati.includes('descrizione')"
          />
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('config.modelli_documenti.field_tipo_output') }} *</label>
            <LookupSelect
              v-model="form.tipo_documento_output_id"
              rel="documenti.tipi_documento_output"
              :placeholder="t('config.modelli_documenti.filter_tipo_output')"
              :disabled="isEdit || isReadOnlyEffective"
            />
            <small class="app-text-muted">
              {{ t('config.modelli_documenti.field_immutable_after_create') }}
            </small>
          </div>
          <div class="form-field">
            <label>{{ t('config.modelli_documenti.field_sorgente') }} *</label>
            <LookupSelect
              v-model="form.sorgente_tipo_id"
              rel="config.sorgenti"
              :placeholder="t('config.modelli_documenti.filter_sorgente')"
              :disabled="isEdit || isReadOnlyEffective"
            />
          </div>
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.field_emittente') }} *</label>
          <EmittenteFiscaleField
            v-model="form.emittente_fiscale_id"
            :record="form"
            :is-edit="isEdit"
            :disabled="isReadOnlyEffective"
          />
          <small class="app-text-muted">
            {{ t('config.modelli_documenti.field_emittente_hint') }}
          </small>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('config.modelli_documenti.field_context_builder') }} *</label>
            <Select
              v-model="form.context_builder_code"
              :options="contextBuilderOpts"
              option-label="label"
              option-value="code"
              :placeholder="t('config.modelli_documenti.field_context_builder_placeholder')"
              :disabled="isReadOnlyEffective"
              fluid
              :invalid="campiErrati.includes('context_builder_code')"
            />
            <Message
              v-if="isSelectedBuilderUnregistered"
              severity="warn"
              :closable="false"
              class="mt-025"
            >
              {{ t('config.modelli_documenti.field_context_builder_unregistered_warn') }}
            </Message>
          </div>
          <div class="form-field">
            <label>{{ t('config.modelli_documenti.field_file_name_pattern') }}</label>
            <InputText
              v-model="form.file_name_pattern"
              :disabled="isReadOnlyEffective"
              :placeholder="t('config.modelli_documenti.field_file_name_pattern_placeholder')"
              maxlength="255"
              fluid
              :invalid="campiErrati.includes('file_name_pattern')"
            />
            <small class="app-text-muted">
              {{ t('config.modelli_documenti.field_file_name_pattern_hint') }}
            </small>
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('config.modelli_documenti.field_is_default') }}</label>
            <ToggleSwitch v-model="form.is_default" :disabled="isReadOnlyEffective"
              :invalid="campiErrati.includes('is_default')"
            />
            <small class="app-text-muted">
              {{ t('config.modelli_documenti.field_is_default_hint') }}
            </small>
          </div>
          <div class="form-field">
            <label>{{ t('common.attivo') }}</label>
            <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective"
              :invalid="campiErrati.includes('attivo')"
            />
          </div>
        </div>
      </div>

      <Message v-if="!isEdit" severity="info" :closable="false" class="mt-1">
        {{ t('config.modelli_documenti.create_first_save_hint') }}
      </Message>

      <template v-if="isEdit && effectiveId">
        <Divider />
        <TemplateVersioniSection
          ref="versioniRef"
          :template-id="effectiveId"
          :emittente-fiscale-id="emittenteLetto"
          :readonly="isReadOnlyEffective"
          @form-aperto="(v) => { formVersioneAperto = v }"
        />
      </template>

    </div>

    <template #footer>
      <FormFooter
        v-if="!formVersioneAperto"
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="chiudi"
      />
    </template>
  </Drawer>
</template>
