<script setup>
// Scopo: Pulsante "Genera PDF" generico riusabile (Tranche M motore
//        documentale). Comportamento (Decisione FE):
//         - 0 template applicabili -> toast warn "Nessun template
//           configurato";
//         - 1 template applicabile  -> POST genera/ diretto + toast
//           success + emit `generated`;
//         - >1 template applicabili -> apre `SceltaTemplateDocumentoDialog`,
//           POST genera/ con il template selezionato.
//
//        Stile: `app-pdf-btn` (rosso PDF, classe centralizzata
//        analoga a `app-edit-btn`/`app-delete-btn` — pattern
//        building block backend frontend-standards). Icona
//        `pi pi-file-pdf`.
//
//        Riusabile per qualsiasi sorgente del motore documentale: il
//        caller passa `sorgenteCode` (es. 'PREVENTIVO') + `sorgenteId` +
//        `emittenteFiscaleId` + `sorgenteTipoId`. Lo store mappa
//        `sorgenteCode` -> client API (`SORGENTE_CLIENT_MAP`).
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { useDocumentiPerSorgenteStore } from '../stores/documentiPerSorgente'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { lookupCodici } from '../../core/apiCore'
import { downloadBlob } from '../../core/utils/download'
import { listTemplateApplicabili } from '../api/templateDocumentiLookup'
import SceltaTemplateDocumentoDialog from './SceltaTemplateDocumentoDialog.vue'

const props = defineProps({
  sorgenteCode: { type: String, required: true },
  sorgenteId: { type: [Number, null], required: true },
  emittenteFiscaleId: { type: [Number, null], required: true },
  // tipo_documento_output_id opzionale: filtra ulteriormente quando
  // la stessa sorgente puo' produrre piu' tipi di output (es. PREVENTIVO
  // -> PDF + email).
  tipoDocumentoOutputId: { type: [Number, null], default: null },
  disabled: { type: Boolean, default: false },
  // Se true: dopo generate, scarica automaticamente il PDF.
  autoDownload: { type: Boolean, default: false },
  // Tooltip e label personalizzabili (default i18n).
  tooltip: { type: String, default: '' },
  label: { type: String, default: '' },
  size: { type: String, default: 'small' },
})
const emit = defineEmits(['generated'])

const { t } = useI18n()
const store = useDocumentiPerSorgenteStore()
const { execute, loading: generating } = useApiHandler()
const notify = useNotify()

// Cache modulo-level (memoria feedback_global_lookup): tutte le istanze
// di GeneraPdfButton condividono la stessa fetch della whitelist
// `config.sorgenti`. La lookup contiene 1 riga per sorgente, totale
// poche decine di record.
const sorgentiLookup = useGlobalLookup(
  'config.sorgenti',
  () => lookupCodici('config.sorgenti', { page_size: 200 }),
  { immediate: true },
)

// Scopo: Risolve `sorgente_tipo_id` dalla lookup `config.sorgenti` a
//        partire dal `sorgenteCode` (es. 'PREVENTIVO'). Ritorna null
//        finche' la lookup non ha caricato.
const sorgenteTipoId = computed(() => {
  const list = sorgentiLookup.items.value
  if (!list?.length) return null
  const match = list.find(s => s.codice === props.sorgenteCode)
  return match ? match.id : null
})

const dialogVisible = ref(false)
const dialogTemplates = ref([])
const dialogLoading = ref(false)
const lookupLoading = ref(false)

const canClick = () =>
  !props.disabled
  && !generating.value
  && !lookupLoading.value
  && !sorgentiLookup.loading.value
  && props.sorgenteId != null
  && props.emittenteFiscaleId != null
  && sorgenteTipoId.value != null

// Scopo: Avvia la generazione. Risolve i template applicabili -> branch
//        in base al numero (0/1/>1).
async function onClick() {
  if (!canClick()) return
  lookupLoading.value = true
  try {
    const res = await listTemplateApplicabili({
      sorgenteTipoId: sorgenteTipoId.value,
      emittenteFiscaleId: props.emittenteFiscaleId,
      tipoDocumentoOutputId: props.tipoDocumentoOutputId,
    })
    const templates = res.data?.data?.results || []
    if (templates.length === 0) {
      notify.warn(t('documenti.genera_pdf.no_template'))
      return
    }
    if (templates.length === 1) {
      await runGenerazione(templates[0].id)
      return
    }
    // >1: dialog scelta.
    dialogTemplates.value = templates
    dialogVisible.value = true
  } catch (err) {
    notify.error(t('documenti.genera_pdf.lookup_error'))
    console.error('listTemplateApplicabili', err)
  } finally {
    lookupLoading.value = false
  }
}

// Scopo: Esegue la POST /genera con il template scelto. Il store
//        gestisce setSorgente + chiamata + refresh lista interna.
async function runGenerazione(templateDocumentoId) {
  store.setSorgente(props.sorgenteCode, props.sorgenteId)
  const result = await execute(
    () => store.genera({
      template_documento_id: templateDocumentoId,
      tipo_documento_output_id: props.tipoDocumentoOutputId,
    }),
    { successMessage: t('documenti.genera_pdf.success') },
  )
  if (result === null) return
  emit('generated', result)
  if (props.autoDownload) {
    await downloadDocumento(result.id)
  }
}

// Scopo: Scarica il PDF appena generato (o un altro documento) usando
//        l'helper condiviso `downloadBlob` (core/utils/download).
async function downloadDocumento(documentoId) {
  try {
    const { blob, fileName } = await store.download(documentoId)
    downloadBlob(blob, fileName)
  } catch (err) {
    notify.error(t('documenti.genera_pdf.download_error'))
    console.error('downloadDocumento', err)
  }
}

function onDialogSelect(templateId) {
  dialogVisible.value = false
  runGenerazione(templateId)
}
</script>

<template>
  <Button
    :icon="'pi pi-file-pdf'"
    :label="label || t('documenti.genera_pdf.label')"
    :tooltip="tooltip || t('documenti.genera_pdf.tooltip')"
    :size="size"
    :loading="generating || lookupLoading"
    :disabled="!canClick()"
    class="app-pdf-btn"
    text
    @click="onClick"
  />

  <SceltaTemplateDocumentoDialog
    :visible="dialogVisible"
    @update:visible="v => dialogVisible = v"
    :templates="dialogTemplates"
    :loading="dialogLoading || generating"
    @select="onDialogSelect"
    @cancel="dialogVisible = false"
  />
</template>
