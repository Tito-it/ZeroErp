<script setup>
// Scopo: Pulsante PDF stato-aware del preventivo. Due comportamenti
//        guidati da `statoCodice`:
//
//         - DRAFT (BOZZA) -> "Anteprima": render on-the-fly via store
//           `documentiPerSorgente.anteprima`. Niente record DB, niente
//           file persistito. UX: il PDF viene scaricato/aperto al volo.
//
//         - EMESSO / ACCETTATO / EVASO / RIFIUTATO / SCADUTO / ANNULLATO ->
//           "Scarica PDF": apre `PdfDocumentiSorgenteDialog` con la lista
//           archiviata; l'utente sceglie quale versione scaricare. Il PDF
//           viene generato automaticamente dal BE alla transizione
//           *->EMESSO (invariante `preventivi_service`: EMESSO => almeno
//           una versione PDF esiste). Coerente col contratto ATTIVO: a
//           valle dell'emissione il documento e' cristallizzato e si
//           scarica, non si rigenera manualmente.
//
//        Pre-condizione: `preventivoId` valorizzato e `statoCodice` letto
//        dal `detail.stato_codice_interno`. Altrimenti il pulsante si
//        renderizza disabilitato. Niente piu' `emittenteFiscaleId`: serviva
//        solo al vecchio branch "genera" (rimosso). Anteprima e scarica non
//        dipendono dall'emittente (allineato a ContrattoPdfButton).

import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import PdfDocumentiSorgenteDialog from '../../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import { useDocumentiPerSorgenteStore } from '../../../documenti/stores/documentiPerSorgente'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { downloadBlob } from '../../../core/utils/download'
import { STATO_PREVENTIVO } from '../../constants'

const SORGENTE_CODE = 'PREVENTIVO'

// Stati con documento PDF gia' persistito (post-emissione): il PDF e'
// cristallizzato, si scarica dalla lista archiviata. Coerenti con i
// codice_interno di config.stati_doc_preventivi. EMESSO incluso: il BE
// genera il PDF alla transizione *->EMESSO.
const STATI_CON_DOCUMENTO = new Set([
  STATO_PREVENTIVO.EMESSO,
  STATO_PREVENTIVO.ACCETTATO,
  STATO_PREVENTIVO.EVASO,
  STATO_PREVENTIVO.RIFIUTATO,
  STATO_PREVENTIVO.SCADUTO,
  STATO_PREVENTIVO.ANNULLATO,
])

const props = defineProps({
  preventivoId: { type: [Number, null], required: true },
  statoCodice: { type: [String, null], default: null },
})

const { t } = useI18n()
const { execute, loading: previewing } = useApiHandler()
const docStore = useDocumentiPerSorgenteStore()

const dialogVisible = ref(false)

const baseDisabled = computed(
  () => !props.preventivoId || !props.statoCodice,
)

const mode = computed(() => {
  if (!props.statoCodice) return 'disabled'
  if (props.statoCodice === STATO_PREVENTIVO.DRAFT) return 'preview'
  if (STATI_CON_DOCUMENTO.has(props.statoCodice)) return 'scarica'
  return 'disabled'
})

// ── BOZZA: anteprima inline (niente save) ──
async function onPreviewClick() {
  if (baseDisabled.value) return
  docStore.setSorgente(SORGENTE_CODE, props.preventivoId)
  const result = await execute(() => docStore.anteprima({}))
  if (!result) return
  downloadBlob(result.blob, result.fileName)
}

// ── Stato post-emissione: dialog lista PDF per scarica ──
function onScaricaClick() {
  if (baseDisabled.value) return
  dialogVisible.value = true
}
</script>

<template>
  <div class="preventivo-pdf-button">
    <!-- DRAFT: Anteprima inline -->
    <Button
      v-if="mode === 'preview'"
      icon="pi pi-file-pdf"
      :label="t('preventivi.pdf.label_anteprima')"
      v-tooltip.top="t('preventivi.pdf.tooltip_anteprima')"
      size="small"
      text
      :loading="previewing"
      :disabled="baseDisabled"
      class="app-pdf-btn app-escape"
      @click="onPreviewClick"
    />

    <!-- Stato post-emissione (EMESSO + terminali): solo Scarica via dialog
         lista. Il PDF e' gia' stato generato dal BE all'emissione. -->
    <Button
      v-else-if="mode === 'scarica'"
      icon="pi pi-file-pdf"
      :label="t('preventivi.pdf.label_scarica')"
      v-tooltip.top="t('preventivi.pdf.tooltip_scarica')"
      size="small"
      text
      :disabled="baseDisabled"
      class="app-pdf-btn app-escape"
      @click="onScaricaClick"
    />

    <!-- Stato non riconosciuto / detail non caricato. -->
    <Button
      v-else
      icon="pi pi-file-pdf"
      :label="t('preventivi.pdf.label_scarica')"
      size="small"
      text
      disabled
      class="app-pdf-btn app-escape"
    />

    <PdfDocumentiSorgenteDialog
      v-model:visible="dialogVisible"
      sorgente-code="PREVENTIVO"
      :sorgente-id="preventivoId"
    />
  </div>
</template>
