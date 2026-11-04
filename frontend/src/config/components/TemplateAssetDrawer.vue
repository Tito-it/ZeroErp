<script setup>
// Scopo: Drawer crea (upload multipart) / modifica metadati asset
//        documentale (Tranche L). Modalita':
//         - create: form + file picker. POST multipart -> upload BE.
//         - edit:   solo metadati editabili (descrizione, valido_dal/al,
//                   attivo). Il BE rifiuta esplicitamente
//                   storage_key/sha256/file_size/mime/file_name e
//                   codice/codice_interno/asset_tipo_id/emittente_fiscale_id
//                   (immutabili). Per cambiare il file caricare un nuovo asset
//                   (Decisione 66).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateAssetDocumentiStore } from '../stores/templateAssetDocumenti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useEmittenteFiscaleField } from '../../core/composables/useEmittenteFiscaleField'
import { DRAWER_WIDTH, MANAGE_ICONS, DATE_FORMAT } from '../../core/constants'
import { parseIsoDate, toDateString } from '../../core/utils/date'
import { downloadBlob } from '../../core/utils/download'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { paramInt } from '../../core/utils/parameterCast'
import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import EmittenteFiscaleField from '../../core/components/EmittenteFiscaleField.vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import FileUpload from 'primevue/fileupload'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useTemplateAssetDocumentiStore()
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

const isEdit = computed(() => props.mode === 'edit')
const isReadOnlyEffective = computed(() => props.readonly || isReadonly.value)

const form = ref(emptyForm())
// Modifiche non salvate: fotografia a form popolato, conferma alla chiusura
// (BB useDrawerFormPreserve). Il file scelto sta fuori dal form: il
// confronto ne raccoglie il nome.
const selectedFile = ref(null)
const formSalvato = computed(() => ({ ...form.value, file_nome: selectedFile.value?.name ?? null }))
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(formSalvato, { visibile: () => props.visible })

// Il limite di upload e' il parametro che il backend applica
// (`documenti_asset_upload_max_mb`): letto da li', non ricopiato. Fino al
// 2026-10-03 era 25 MB scritto anche qui, e cambiando il parametro i due
// limiti si sarebbero separati in silenzio. Parametro non letto ⇒ nessun
// controllo anticipato: decide il backend, col suo errore.
const { defaults: paramUpload, load: caricaParamUpload } =
  useParameterDefaults(['documenti_asset_upload_max_mb'])
const maxFileBytes = computed(() => {
  const mb = paramInt(paramUpload.value.documenti_asset_upload_max_mb, null)
  return mb === null ? undefined : mb * 1024 * 1024
})
const downloadLoading = ref(false)

function emptyForm() {
  return {
    codice: '',
    codice_interno: '',
    descrizione: '',
    asset_tipo_id: null,
    emittente_fiscale_id: null,
    // Denormalizzati dal payload BE per display read-only in edit.
    emittente_fiscale_codice: null,
    emittente_ragione_sociale: null,
    mime_type: null,
    file_name: null,
    file_size_bytes: null,
    sha256: null,
    storage_key: null,
    valido_dal: null,
    valido_al: null,
    attivo: true,
  }
}

async function loadDetail() {
  if (!props.recordId) return
  const data = await store.fetchDetail(props.recordId)
  if (!data) return
  form.value = {
    codice: data.codice ?? '',
    codice_interno: data.codice_interno ?? '',
    descrizione: data.descrizione ?? '',
    asset_tipo_id: data.asset_tipo_id ?? null,
    emittente_fiscale_id: data.emittente_fiscale_id ?? null,
    emittente_fiscale_codice: data.emittente_fiscale_codice ?? null,
    emittente_ragione_sociale: data.emittente_ragione_sociale ?? null,
    mime_type: data.mime_type ?? null,
    file_name: data.file_name ?? null,
    file_size_bytes: data.file_size_bytes ?? null,
    sha256: data.sha256 ?? null,
    storage_key: data.storage_key ?? null,
    valido_dal: parseIsoDate(data.valido_dal),
    valido_al: parseIsoDate(data.valido_al),
    attivo: data.attivo ?? true,
  }
  fissa()
}

watch(
  [() => props.visible, () => props.recordId],
  ([visible]) => {
    if (!visible) return
    caricaParamUpload()
    selectedFile.value = null
    if (isEdit.value) {
      loadDetail()
    } else {
      form.value = emptyForm()
      // Autopopulate centralizzato: null se admin globale (sceglie via
      // Select), id dell'emittente del profilo per operatore standard.
      form.value.emittente_fiscale_id = defaultEmittenteId.value
      fissa()
    }
  },
)

const canSave = computed(() => {
  if (isReadOnlyEffective.value) return false
  const f = form.value
  if (!isEdit.value) {
    if (!f.codice?.trim()) return false
    if (!f.codice_interno?.trim()) return false
    if (!f.asset_tipo_id) return false
    if (!f.emittente_fiscale_id) return false
    if (!selectedFile.value) return false
  }
  if (!f.descrizione?.trim()) return false
  return true
})

const currentFileCount = computed(() => (form.value.file_name ? 1 : 0))

function onFileSelect(event) {
  // PrimeVue FileUpload event.files contiene l'elenco aggiunto.
  const files = event.files || []
  selectedFile.value = files[0] || null
}

function onFileClear() {
  selectedFile.value = null
}

function formatFileSize(bytes) {
  const value = Number(bytes)
  if (!Number.isFinite(value) || value <= 0) return '-'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

async function handleDownloadAsset() {
  if (!props.recordId || !form.value.file_name) return
  downloadLoading.value = true
  try {
    const result = await execute(
      () => store.download(props.recordId),
      { errorMessage: t('config.modelli_documenti.asset.download_error') },
    )
    if (!result) return
    downloadBlob(result.blob, result.fileName || form.value.file_name)
  } finally {
    downloadLoading.value = false
  }
}

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {
      descrizione: f.descrizione.trim(),
      valido_dal: toDateString(f.valido_dal),
      valido_al: toDateString(f.valido_al),
      attivo: f.attivo,
    }
    const result = await execute(
      () => store.update(props.recordId, payload),
      { successMessage: t('config.modelli_documenti.asset.saved') },
    )
    // Salvato: la fotografia diventa il salvato (il padre chiude dopo il refresh).
    if (result !== null) { fissa(); emit('saved', result) }
  } else {
    // Build FormData multipart.
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    fd.append('codice', f.codice.trim())
    fd.append('codice_interno', f.codice_interno.trim())
    fd.append('descrizione', f.descrizione.trim())
    fd.append('asset_tipo_id', String(f.asset_tipo_id))
    fd.append('emittente_fiscale_id', String(f.emittente_fiscale_id))
    const dalIso = toDateString(f.valido_dal)
    if (dalIso) fd.append('valido_dal', dalIso)
    const alIso = toDateString(f.valido_al)
    if (alIso) fd.append('valido_al', alIso)
    fd.append('attivo', String(f.attivo))
    const result = await execute(
      () => store.upload(fd),
      { successMessage: t('config.modelli_documenti.asset.uploaded') },
    )
    if (result !== null) { fissa(); emit('saved', result) }
  }
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('config.modelli_documenti.asset.drawer_title')"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
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
          <label>{{ t('config.modelli_documenti.asset.field_codice') }} *</label>
          <InputText
            v-model="form.codice"
            class="app-codice-input"
            :disabled="isEdit || isReadOnlyEffective"
            maxlength="120"
            fluid
            :invalid="campiErrati.includes('codice')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.asset.field_codice_interno') }} *</label>
          <InputText
            v-model="form.codice_interno"
            :disabled="isEdit || isReadOnlyEffective"
            maxlength="120"
            fluid
            :invalid="campiErrati.includes('codice_interno')"
          />
        </div>
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.asset.field_descrizione') }} *</label>
        <InputText
          v-model="form.descrizione"
          :disabled="isReadOnlyEffective"
          maxlength="500"
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.asset.field_tipo') }} *</label>
        <LookupSelect
          v-model="form.asset_tipo_id"
          rel="documenti.tipi_asset_documento"
          :placeholder="t('config.modelli_documenti.asset.filter_tipo')"
          :disabled="isEdit || isReadOnlyEffective"
        />
        <small v-if="isEdit" class="app-text-muted">
          {{ t('config.modelli_documenti.asset.field_tipo_immutable_hint') }}
        </small>
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
          <label>{{ t('config.modelli_documenti.asset.field_valido_dal') }}</label>
          <DatePicker v-model="form.valido_dal" :disabled="isReadOnlyEffective" :date-format="DATE_FORMAT" fluid
            :invalid="campiErrati.includes('valido_dal')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.asset.field_valido_al') }}</label>
          <DatePicker v-model="form.valido_al" :disabled="isReadOnlyEffective" :date-format="DATE_FORMAT" fluid
            :invalid="campiErrati.includes('valido_al')"
          />
        </div>
      </div>
      <div class="form-field">
        <label>{{ t('common.attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective"
          :invalid="campiErrati.includes('attivo')"
        />
      </div>

      <template v-if="!isEdit">
        <div class="form-field form-field-wide">
          <label>{{ t('config.modelli_documenti.asset.field_file') }} *</label>
          <FileUpload
            mode="basic"
            :auto="false"
            :multiple="false"
            :max-file-size="maxFileBytes"
            :choose-label="t('config.modelli_documenti.asset.choose_file')"
            :customUpload="true"
            @select="onFileSelect"
            @clear="onFileClear"
            :disabled="isReadOnlyEffective"
          />
          <small v-if="selectedFile" class="app-text-muted">
            {{ selectedFile.name }} ({{ Math.round(selectedFile.size / 1024) }} KB)
          </small>
          <small class="app-text-muted">
            {{ t('config.modelli_documenti.asset.field_file_hint') }}
          </small>
        </div>
      </template>
      <template v-else>
        <div class="form-field form-field-wide">
          <label>{{ t('config.modelli_documenti.asset.field_file') }}</label>
          <div class="asset-file-panel">
            <div class="asset-file-main">
              <span class="asset-file-count">
                {{ t('config.modelli_documenti.asset.file_count', { count: currentFileCount }) }}
              </span>
              <strong>{{ form.file_name || '-' }}</strong>
              <small class="app-text-muted">
                {{ form.mime_type || '-' }} · {{ formatFileSize(form.file_size_bytes) }}
              </small>
            </div>
            <Button
              :icon="MANAGE_ICONS.DOWNLOAD"
              :label="t('config.modelli_documenti.asset.download_file')"
              size="small"
              severity="secondary"
              outlined
              :loading="downloadLoading"
              :disabled="!form.file_name"
              class="app-escape"
              @click="handleDownloadAsset"
            />
          </div>
          <small v-if="form.sha256" class="app-text-muted asset-file-hash">
            SHA256 {{ form.sha256 }}
          </small>
        </div>
      </template>

      <Message v-if="isEdit" severity="info" :closable="false">
        {{ t('config.modelli_documenti.asset.edit_metadati_only_hint') }}
      </Message>
    </div>
  </AppDrawer>
</template>

<style scoped>
.asset-file-panel {
  align-items: center;
  border: 1px solid var(--app-border-color);
  border-radius: 6px;
  display: flex;
  gap: 0.75rem;
  justify-content: space-between;
  padding: 0.65rem 0.75rem;
}

.asset-file-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.asset-file-main strong,
.asset-file-main small,
.asset-file-hash {
  overflow-wrap: anywhere;
}

.asset-file-count {
  color: var(--app-text-muted);
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
}
</style>
