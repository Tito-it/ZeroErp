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
//          - context_builder_code dal REGISTRO del backend
//            (`GET /documenti/context-builders/`, dal 2026-10-03: prima era
//            una copia scritta a mano nel frontend, col flag «registrato»).
//        Emittente fiscale: gestito da `useEmittenteFiscaleField`. Per
//        l'operatore standard (1-a-1 col proprio emittente) il valore e'
//        derivato dal profilo e mostrato read-only; per l'admin globale
//        compare un Select popolato dal lookup admin esistente.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateDocumentiStore } from '../stores/templateDocumenti'
import { listContextBuilders } from '../api/templateDocumenti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookup } from '../../core/composables/useLookup'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useEmittenteFiscaleField } from '../../core/composables/useEmittenteFiscaleField'
import { DRAWER_WIDTH } from '../../core/constants'
import { labelOrCode } from '../../core/utils/i18nLabel'
import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import EmittenteFiscaleField from '../../core/components/EmittenteFiscaleField.vue'
import TemplateVersioniSection from './TemplateVersioniSection.vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'
import Divider from 'primevue/divider'

const { t, te } = useI18n()
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

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

// `mode` evolve da create a edit dopo il primo save (memoria
// feedback_drawer_create_autosave_bozza).
const localMode = ref(props.mode)
const createdId = ref(null)
const isEdit = computed(() => localMode.value === 'edit' || createdId.value !== null)
const isReadOnlyEffective = computed(() => props.readonly || isReadonly.value)
const effectiveId = computed(() => props.recordId || createdId.value)

// I builder registrati nel backend: la tendina li legge dal registro
// (sede unica), con l'etichetta dai locales e ripiego sul codice.
const { items: builderRegistrati, loaded: registroLetto, load: caricaBuilder } =
  useLookup(listContextBuilders)
// Scopo: le opzioni della tendina. Un template il cui codice NON e' nel
//        registro (un builder ritirato, o un codice scritto altrove) lo
//        mostra lo stesso, come opzione non registrata: sparire dalla
//        tendina farebbe leggere un campo vuoto su un template che un codice
//        ce l'ha.
function opzioneBuilder(codice, registered) {
  return {
    code: codice,
    label: labelOrCode(t, te, `documenti.context_builders.${codice}`, codice),
    registered,
  }
}
const contextBuilderOpts = computed(() => {
  const opzioni = builderRegistrati.value.map(({ codice }) => opzioneBuilder(codice, true))
  const corrente = form.value.context_builder_code
  if (corrente && !opzioni.some(o => o.code === corrente)) {
    opzioni.push(opzioneBuilder(corrente, false))
  }
  return opzioni
})

// Scopo: Avviso quando il codice del template non e' fra i registrati: il
//        template si salva, ma la generazione sollevera' E_DOCUMENTI_VALIDATION
//        finche' un dominio non registra quel builder. Si decide solo a
//        registro letto: prima ogni codice sembrerebbe non registrato.
const isSelectedBuilderUnregistered = computed(() =>
  registroLetto.value
    && contextBuilderOpts.value.find(o => o.code === form.value.context_builder_code)
      ?.registered === false,
)

// L'emittente del template LETTO (non quello del form): e' il padre della
// lista delle versioni. Il form, riaprendo un altro template, tiene i valori
// del precedente finche' il dettaglio non arriva — la lista partirebbe col
// padre vecchio e ripartirebbe da capo un attimo dopo. `null` = in attesa.
const emittenteLetto = ref(null)
// La forma dei dati che il builder del template produce oggi, LETTA dal
// dettaglio (`versione_contesto_builder`, un fatto del backend): la sezione
// versioni la mostra e ne precompila la nuova versione. `null` = in attesa, o
// builder non registrato.
const versioneContestoBuilder = ref(null)

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
  versioneContestoBuilder.value = data.versione_contesto_builder ?? null
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
    caricaBuilder()
    localMode.value = mode
    createdId.value = null
    emittenteLetto.value = null
    versioneContestoBuilder.value = null
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
      versioneContestoBuilder.value = result.versione_contesto_builder ?? null
      localMode.value = 'edit'
      fissa()
      emit('saved', result)
    }
  }
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('config.modelli_documenti.drawer_title')"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.COMPLEX"
    :readonly="isReadOnlyEffective"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >
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
        :template-id="effectiveId"
        :emittente-fiscale-id="emittenteLetto"
        :versione-contesto-builder="versioneContestoBuilder"
        :readonly="isReadOnlyEffective"
      />
    </template>
  </AppDrawer>
</template>
