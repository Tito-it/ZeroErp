<script setup>
// Scopo: Pulsante PDF stato-aware del contratto.
// - DRAFT: anteprima PDF temporanea, senza persistenza.
// - ATTIVO/CESSATO: apre la lista dei PDF gia' generati e salvati.

import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import PdfDocumentiSorgenteDialog from '../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import { useDocumentiPerSorgenteStore } from '../../documenti/stores/documentiPerSorgente'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { downloadBlob } from '../../core/utils/download'

const SORGENTE_CODE = 'CONTRATTO'
const STATI_CON_DOCUMENTO = new Set(['ATTIVO', 'CESSATO'])

const props = defineProps({
  contrattoId: { type: [Number, null], required: true },
  statoCodice: { type: [String, null], default: null },
  numero: { type: String, default: '' },
})

const { t } = useI18n()
const { execute, loading: previewing } = useApiHandler()
const docStore = useDocumentiPerSorgenteStore()

const dialogVisible = ref(false)

const baseDisabled = computed(
  () => !props.contrattoId || !props.statoCodice,
)

const mode = computed(() => {
  if (!props.statoCodice) return 'disabled'
  if (props.statoCodice === 'DRAFT') return 'preview'
  if (STATI_CON_DOCUMENTO.has(props.statoCodice)) return 'scarica'
  return 'disabled'
})

async function onPreviewClick() {
  if (baseDisabled.value) return
  docStore.setSorgente(SORGENTE_CODE, props.contrattoId)
  const result = await execute(() => docStore.anteprima({}))
  if (!result) return
  downloadBlob(result.blob, result.fileName)
}

function onScaricaClick() {
  if (baseDisabled.value) return
  dialogVisible.value = true
}
</script>

<template>
  <div class="contratto-pdf-button">
    <Button
      v-if="mode === 'preview'"
      icon="pi pi-file-pdf"
      :label="t('contratti.pdf.label_anteprima')"
      v-tooltip.top="t('contratti.pdf.tooltip_anteprima')"
      size="small"
      text
      :loading="previewing"
      :disabled="baseDisabled"
      class="app-pdf-btn app-escape"
      @click="onPreviewClick"
    />

    <Button
      v-else-if="mode === 'scarica'"
      icon="pi pi-file-pdf"
      :label="t('contratti.pdf.label_scarica')"
      v-tooltip.top="t('contratti.pdf.tooltip_scarica')"
      size="small"
      text
      :disabled="baseDisabled"
      class="app-pdf-btn app-escape"
      @click="onScaricaClick"
    />

    <Button
      v-else
      icon="pi pi-file-pdf"
      :label="t('contratti.pdf.label_scarica')"
      size="small"
      text
      disabled
      class="app-pdf-btn app-escape"
    />

    <PdfDocumentiSorgenteDialog
      v-model:visible="dialogVisible"
      sorgente-code="CONTRATTO"
      :sorgente-id="contrattoId"
      :title="numero ? t('contratti.pdf.dialog_title', { numero }) : ''"
    />
  </div>
</template>
