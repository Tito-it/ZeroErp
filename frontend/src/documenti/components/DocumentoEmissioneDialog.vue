<script setup>
// Scopo: Building block generico "genera documento + allegati" per
//        l'emissione / avanzamento di stato di una sorgente documentale
//        (offerta -> poi preventivi/contratti). Mostra l'anteprima del PDF
//        che verra' generato e consente di allegare file (PDF/immagini)
//        prima di confermare.
//
//        Due modalita' via `advances-state`:
//         - true  (BOZZA -> stato avanzato): la Conferma avanza lo stato +
//           genera + persiste documento e allegati in UNA transazione lato
//           BE; l'Annulla NON persiste nulla (i file scelti si perdono,
//           warning) e lo stato resta invariato (Annulla = abbandono).
//         - false (append): aggiunge allegati a un documento gia' generato
//           (es. offerta gia' EMESSA, finche' lo stato lo consente).
//
//        Il componente e' presentazionale: raccoglie i file in staging
//        (caricati solo alla Conferma) e mostra l'anteprima. Il COMMIT lo
//        esegue il parent via `@confirm` (draft: chiama l'endpoint emetti
//        multipart del dominio; append: chiama aggiungi-allegati). Il
//        riepilogo specifico di dominio va nello slot `#riepilogo`.
//
//        AppDialog e' usato controllato: intercettiamo ogni richiesta di
//        chiusura (Annulla / X / Esc / mask) per mostrare il warning di
//        abbandono quando ci sono file in staging.
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import AppDialog from '../../core/components/AppDialog.vue'
import { useDocumentiPerSorgenteStore } from '../stores/documentiPerSorgente'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { downloadBlob } from '../../core/utils/download'

// MIME ammessi di default per gli allegati (allineato alla whitelist BE).
const ACCEPT_DEFAULT = 'application/pdf,image/jpeg,image/png'

const props = defineProps({
  visible: { type: Boolean, required: true },
  sorgenteCode: { type: String, required: true },
  sorgenteId: { type: [Number, null], default: null },
  // true = avanza stato (mostra anteprima); false = append a doc esistente.
  advancesState: { type: Boolean, default: true },
  header: { type: String, default: '' },
  confirmLabel: { type: String, default: null },
  // Stato di caricamento esterno (il commit lo fa il parent su @confirm).
  loading: { type: Boolean, default: false },
  // Disabilita la Conferma per ragioni di dominio (es. offerta senza
  // versione listino: il BE rifiuterebbe comunque, ma blocchiamo prima).
  confirmDisabled: { type: Boolean, default: false },
  // Filtro file input (whitelist MIME lato client, ridondante col BE).
  accept: { type: String, default: ACCEPT_DEFAULT },
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

const { t } = useI18n()
const docStore = useDocumentiPerSorgenteStore()
const { confirmAction } = useConfirmAction()

const stagedFiles = ref([])
const fileInput = ref(null)
const previewUrl = ref(null)
const previewBlob = ref(null)
const previewLoading = ref(false)
const previewError = ref(null)

const dialogWidth = computed(() => (props.advancesState ? 'xl' : 'md'))

// In append mode confermare senza file non ha senso; in draft mode invece
// si puo' emettere anche senza allegati.
const saveDisabled = computed(
  () => props.loading
    || props.confirmDisabled
    || (!props.advancesState && stagedFiles.value.length === 0),
)

watch(
  () => props.visible,
  (open) => {
    if (open) {
      stagedFiles.value = []
      if (props.advancesState) loadPreview()
    } else {
      revokePreview()
    }
  },
)

// Scopo: Rilascia l'object URL dell'anteprima (evita leak di memoria).
function revokePreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
  previewBlob.value = null
  previewError.value = null
}

// Scopo: Carica l'anteprima PDF temporanea (no persist) del documento che
//        verra' generato. Errore parlante se manca il template (il BE
//        risponde E_DOCUMENTI_NOT_FOUND).
async function loadPreview() {
  if (!props.sorgenteId) return
  revokePreview()
  previewLoading.value = true
  try {
    docStore.setSorgente(props.sorgenteCode, props.sorgenteId)
    const { blob } = await docStore.anteprima({})
    previewBlob.value = blob
    previewUrl.value = URL.createObjectURL(blob)
  } catch (err) {
    previewError.value =
      err?.response?.data?.error?.message
      || t('documenti.emissione.anteprima_errore')
  } finally {
    previewLoading.value = false
  }
}

function openFilePicker() {
  fileInput.value?.click()
}

function onFilesSelected(event) {
  const picked = Array.from(event.target.files || [])
  stagedFiles.value = [...stagedFiles.value, ...picked]
  // Reset per consentire la riselezione dello stesso file.
  event.target.value = ''
}

function removeFile(index) {
  stagedFiles.value.splice(index, 1)
}

// Scopo: KB/MB leggibili per la lista allegati staged.
function formatSize(bytes) {
  if (!bytes && bytes !== 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function onAnteprimaDownload() {
  if (previewBlob.value) {
    downloadBlob(previewBlob.value, t('documenti.emissione.anteprima_filename'))
  }
}

function onSave() {
  emit('confirm', { files: stagedFiles.value })
}

// Scopo: Intercetta ogni richiesta di chiusura. Con file in staging mostra
//        il warning di abbandono (in draft mode lo stato resta invariato).
function requestClose() {
  if (stagedFiles.value.length > 0) {
    confirmAction({
      title: t('documenti.emissione.abbandona_titolo'),
      message: props.advancesState
        ? t('documenti.emissione.abbandona_messaggio_draft')
        : t('documenti.emissione.abbandona_messaggio'),
      danger: true,
      acceptLabel: t('documenti.emissione.abbandona_conferma'),
      onAccept: doClose,
    })
    return
  }
  doClose()
}

function doClose() {
  stagedFiles.value = []
  emit('cancel')
  emit('update:visible', false)
}

// AppDialog e' controllato: ogni `update:visible(false)` passa dal warning.
function onDialogVisible(val) {
  if (!val) requestClose()
}

onBeforeUnmount(revokePreview)
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="header || t('documenti.emissione.titolo')"
    :width="dialogWidth"
    :loading="loading"
    :save-disabled="saveDisabled"
    :save-label="confirmLabel || t('documenti.emissione.conferma')"
    @update:visible="onDialogVisible"
    @save="onSave"
  >
    <div class="documento-emissione">
      <!-- Riepilogo di dominio (listino/versione/eccezioni per l'offerta). -->
      <div v-if="$slots.riepilogo" class="documento-emissione__riepilogo">
        <slot name="riepilogo" />
      </div>

      <!-- Anteprima del documento che verra' generato (solo draft mode). -->
      <div v-if="advancesState" class="documento-emissione__preview">
        <div class="documento-emissione__preview-head">
          <span class="documento-emissione__preview-title">
            {{ t('documenti.emissione.anteprima_titolo') }}
          </span>
          <Button
            v-if="previewBlob"
            icon="pi pi-download"
            :label="t('documenti.emissione.anteprima_scarica')"
            size="small"
            text
            class="app-escape"
            @click="onAnteprimaDownload"
          />
        </div>

        <div v-if="previewLoading" class="documento-emissione__preview-loading">
          <ProgressSpinner style="width: 2.5rem; height: 2.5rem" stroke-width="4" />
        </div>
        <Message
          v-else-if="previewError"
          severity="warn"
          :closable="false"
          size="small"
        >
          {{ previewError }}
        </Message>
        <iframe
          v-else-if="previewUrl"
          :src="previewUrl"
          class="documento-emissione__iframe"
          :title="t('documenti.emissione.anteprima_titolo')"
        />
      </div>

      <!-- Allegati in staging (caricati solo alla Conferma). -->
      <div class="documento-emissione__allegati">
        <div class="documento-emissione__allegati-head">
          <span class="documento-emissione__allegati-title">
            {{ t('documenti.emissione.allegati_titolo') }}
          </span>
          <Button
            icon="pi pi-paperclip"
            :label="t('documenti.emissione.aggiungi_allegati')"
            size="small"
            outlined
            @click="openFilePicker"
          />
          <input
            ref="fileInput"
            type="file"
            multiple
            :accept="accept"
            style="display: none"
            @change="onFilesSelected"
          />
        </div>

        <ul v-if="stagedFiles.length" class="documento-emissione__file-list">
          <li v-for="(f, idx) in stagedFiles" :key="idx" class="documento-emissione__file">
            <i class="pi pi-file" />
            <span class="documento-emissione__file-name">{{ f.name }}</span>
            <span class="documento-emissione__file-size">{{ formatSize(f.size) }}</span>
            <Button
              icon="pi pi-times"
              text
              rounded
              size="small"
              severity="danger"
              :aria-label="t('common.remove')"
              @click="removeFile(idx)"
            />
          </li>
        </ul>
        <div v-else class="documento-emissione__allegati-empty">
          {{ t('documenti.emissione.allegati_vuoto') }}
        </div>
      </div>
    </div>
  </AppDialog>
</template>

<style scoped>
.documento-emissione {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.documento-emissione__preview-head,
.documento-emissione__allegati-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}
.documento-emissione__preview-title,
.documento-emissione__allegati-title {
  font-weight: 600;
}
.documento-emissione__iframe {
  width: 100%;
  height: 55vh;
  border: 1px solid var(--app-border-color, var(--p-content-border-color));
  border-radius: var(--app-radius, 6px);
}
.documento-emissione__preview-loading {
  display: flex;
  justify-content: center;
  padding: 2rem 0;
}
.documento-emissione__file-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.documento-emissione__file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--app-border-color, var(--p-content-border-color));
  border-radius: var(--app-radius, 6px);
}
.documento-emissione__file-name {
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.documento-emissione__file-size {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
}
.documento-emissione__allegati-empty {
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
}
</style>
