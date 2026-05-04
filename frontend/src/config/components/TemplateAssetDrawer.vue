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
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import { isoToLocalDate, localDateToIso } from '../../core/utils/dateHelpers'
import { ASSET_UPLOAD_MAX_BYTES } from '../constants/documentiVersioniWhitelists'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import FileUpload from 'primevue/fileupload'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useTemplateAssetDocumentiStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

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
const selectedFile = ref(null)

function emptyForm() {
  return {
    codice: '',
    codice_interno: '',
    descrizione: '',
    asset_tipo_id: null,
    emittente_fiscale_id: null,
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
    valido_dal: isoToLocalDate(data.valido_dal),
    valido_al: isoToLocalDate(data.valido_al),
    attivo: data.attivo ?? true,
  }
}

watch(
  [() => props.visible, () => props.recordId],
  ([visible]) => {
    if (!visible) return
    selectedFile.value = null
    if (isEdit.value) {
      loadDetail()
    } else {
      form.value = emptyForm()
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

function onFileSelect(event) {
  // PrimeVue FileUpload event.files contiene l'elenco aggiunto.
  const files = event.files || []
  selectedFile.value = files[0] || null
}

function onFileClear() {
  selectedFile.value = null
}

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {
      descrizione: f.descrizione.trim(),
      valido_dal: localDateToIso(f.valido_dal),
      valido_al: localDateToIso(f.valido_al),
      attivo: f.attivo,
    }
    const result = await execute(
      () => store.update(props.recordId, payload),
      { successMessage: t('config.modelli_documenti.asset.saved') },
    )
    if (result !== null) emit('saved', result)
  } else {
    // Build FormData multipart.
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    fd.append('codice', f.codice.trim())
    fd.append('codice_interno', f.codice_interno.trim())
    fd.append('descrizione', f.descrizione.trim())
    fd.append('asset_tipo_id', String(f.asset_tipo_id))
    fd.append('emittente_fiscale_id', String(f.emittente_fiscale_id))
    const dalIso = localDateToIso(f.valido_dal)
    if (dalIso) fd.append('valido_dal', dalIso)
    const alIso = localDateToIso(f.valido_al)
    if (alIso) fd.append('valido_al', alIso)
    fd.append('attivo', String(f.attivo))
    const result = await execute(
      () => store.upload(fd),
      { successMessage: t('config.modelli_documenti.asset.uploaded') },
    )
    if (result !== null) emit('saved', result)
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
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
        :title="t('config.modelli_documenti.asset.drawer_title')"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadOnlyEffective }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.asset.field_codice') }} *</label>
          <InputText
            v-model="form.codice"
            :disabled="isEdit || isReadOnlyEffective"
            maxlength="120"
          />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.asset.field_codice_interno') }} *</label>
          <InputText
            v-model="form.codice_interno"
            :disabled="isEdit || isReadOnlyEffective"
            maxlength="120"
          />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.asset.field_descrizione') }} *</label>
          <InputText
            v-model="form.descrizione"
            :disabled="isReadOnlyEffective"
            maxlength="500"
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
          <small v-if="isEdit" class="text-color-secondary">
            {{ t('config.modelli_documenti.asset.field_tipo_immutable_hint') }}
          </small>
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.field_emittente') }} *</label>
          <InputNumber
            v-model="form.emittente_fiscale_id"
            :disabled="isEdit || isReadOnlyEffective"
            :min="1"
            :useGrouping="false"
          />
          <small class="text-color-secondary">
            {{ t('config.modelli_documenti.field_emittente_hint') }}
          </small>
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.asset.field_valido_dal') }}</label>
          <DatePicker v-model="form.valido_dal" :disabled="isReadOnlyEffective" date-format="dd/mm/yy" />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.asset.field_valido_al') }}</label>
          <DatePicker v-model="form.valido_al" :disabled="isReadOnlyEffective" date-format="dd/mm/yy" />
        </div>
        <div class="form-field">
          <label>{{ t('common.attivo') }}</label>
          <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective" />
        </div>

        <template v-if="!isEdit">
          <div class="form-field form-field-wide">
            <label>{{ t('config.modelli_documenti.asset.field_file') }} *</label>
            <FileUpload
              mode="basic"
              :auto="false"
              :multiple="false"
              :max-file-size="ASSET_UPLOAD_MAX_BYTES"
              :choose-label="t('config.modelli_documenti.asset.choose_file')"
              :customUpload="true"
              @select="onFileSelect"
              @clear="onFileClear"
              :disabled="isReadOnlyEffective"
            />
            <small v-if="selectedFile" class="text-color-secondary">
              {{ selectedFile.name }} ({{ Math.round(selectedFile.size / 1024) }} KB)
            </small>
            <small class="text-color-secondary">
              {{ t('config.modelli_documenti.asset.field_file_hint') }}
            </small>
          </div>
        </template>

        <Message v-if="isEdit" severity="info" :closable="false">
          {{ t('config.modelli_documenti.asset.edit_metadati_only_hint') }}
        </Message>
      </div>

      <DrawerFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="close"
      />
    </div>
  </Drawer>
</template>
