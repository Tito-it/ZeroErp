<script setup>
// Scopo: Pulsante PDF stato-aware dell'offerta commerciale. Mirror di
//        ContrattoPdfButton/PreventivoPdfButton.
//  - BOZZA: anteprima PDF temporanea (no persist). La generazione/persistenza
//    avviene all'emissione (vedi OffertaEmissioneDialog).
//  - EMESSA/…: apre la lista dei PDF gia' generati. In EMESSA e' abilitato
//    l'append di allegati al documento (regola "fino a EMESSA compresa").
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import PdfDocumentiSorgenteDialog from '../../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import { useDocumentiPerSorgenteStore } from '../../../documenti/stores/documentiPerSorgente'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { downloadBlob } from '../../../core/utils/download'

const SORGENTE_CODE = 'OFFERTA_COMMERCIALE'
// Stati in cui il documento e' gia' stato generato (emissione in poi).
const STATI_CON_DOCUMENTO = new Set([
  'EMESSA', 'ACCETTATA', 'RIFIUTATA', 'SUPERATA', 'ANNULLATA',
])

const props = defineProps({
  offertaId: { type: [Number, null], required: true },
  statoCodice: { type: [String, null], default: null },
  codice: { type: String, default: '' },
})

const { t } = useI18n()
const { execute, loading: previewing } = useApiHandler()
const docStore = useDocumentiPerSorgenteStore()

const dialogVisible = ref(false)

const baseDisabled = computed(() => !props.offertaId || !props.statoCodice)

const mode = computed(() => {
  if (!props.statoCodice) return 'disabled'
  if (props.statoCodice === 'BOZZA') return 'preview'
  if (STATI_CON_DOCUMENTO.has(props.statoCodice)) return 'scarica'
  return 'disabled'
})

// Append allegati consentito solo in EMESSA (regola dominio offerta).
const allowAllegati = computed(() => props.statoCodice === 'EMESSA')

async function onPreviewClick() {
  if (baseDisabled.value) return
  docStore.setSorgente(SORGENTE_CODE, props.offertaId)
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
  <div class="offerta-pdf-button">
    <Button
      v-if="mode === 'preview'"
      icon="pi pi-file-pdf"
      :label="t('vendite.offerte.pdf.label_anteprima')"
      v-tooltip.top="t('vendite.offerte.pdf.tooltip_anteprima')"
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
      :label="t('vendite.offerte.pdf.label_scarica')"
      v-tooltip.top="t('vendite.offerte.pdf.tooltip_scarica')"
      size="small"
      text
      :disabled="baseDisabled"
      class="app-pdf-btn app-escape"
      @click="onScaricaClick"
    />

    <Button
      v-else
      icon="pi pi-file-pdf"
      :label="t('vendite.offerte.pdf.label_scarica')"
      size="small"
      text
      disabled
      class="app-pdf-btn app-escape"
    />

    <PdfDocumentiSorgenteDialog
      v-model:visible="dialogVisible"
      :sorgente-code="SORGENTE_CODE"
      :sorgente-id="offertaId"
      :allow-allegati="allowAllegati"
      :title="codice ? t('vendite.offerte.pdf.dialog_title', { codice }) : ''"
    />
  </div>
</template>
