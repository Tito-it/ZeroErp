<script setup>
// Scopo: Pulsante PDF stato-aware del preventivo. Tre comportamenti
//        guidati da `statoCodice`:
//
//         - DRAFT (BOZZA) -> "Anteprima": render on-the-fly via store
//           `documentiPerSorgente.anteprima`. Niente record DB, niente
//           file persistito. UX: il PDF viene scaricato/aperto al volo.
//
//         - EMESSO -> "Genera PDF": riusa `GeneraPdfButton` con prop
//           `beforeGenerate` per intercettare il click e chiedere
//           conferma all'utente ("esiste gia' la versione N del
//           DD/MM/YYYY; verra' creata la versione N+1, le precedenti
//           restano in archivio"). Le rigenerazioni accumulano versioni;
//           niente sostituzione (memoria modello documenti_generati).
//
//         - ACCETTATO / RIFIUTATO / SCADUTO / ANNULLATO -> "Scarica
//           PDF": apre `PdfDocumentiSorgenteDialog` con la lista
//           archiviata; l'utente sceglie quale versione scaricare.
//           Niente generazione: PDF cristallizzati post-emissione.
//
//        Pre-condizione: `preventivoId` e `emittenteFiscaleId` valorizzati
//        e `statoCodice` letto dal `detail.stato_codice_interno`.
//        Altrimenti il pulsante si renderizza disabilitato.

import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import GeneraPdfButton from '../../../documenti/components/GeneraPdfButton.vue'
import PdfDocumentiSorgenteDialog from '../../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import { useDocumentiPerSorgenteStore } from '../../../documenti/stores/documentiPerSorgente'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { downloadBlob } from '../../../core/utils/download'

const SORGENTE_CODE = 'PREVENTIVO'

// Stati post-emissione dove il PDF e' cristallizzato (niente
// rigenerazione). Coerenti con i codice_interno di
// config.stati_doc_preventivi.
const STATI_TERMINALI = new Set([
  'ACCETTATO', 'RIFIUTATO', 'SCADUTO', 'ANNULLATO',
])

const props = defineProps({
  preventivoId: { type: [Number, null], required: true },
  emittenteFiscaleId: { type: [Number, null], required: true },
  statoCodice: { type: [String, null], default: null },
})

const { t } = useI18n()
const { execute, loading: previewing } = useApiHandler()
const confirm = useConfirm()
const docStore = useDocumentiPerSorgenteStore()

const dialogVisible = ref(false)

const baseDisabled = computed(
  () => !props.preventivoId
    || !props.emittenteFiscaleId
    || !props.statoCodice,
)

const mode = computed(() => {
  if (!props.statoCodice) return 'disabled'
  if (props.statoCodice === 'DRAFT') return 'preview'
  if (props.statoCodice === 'EMESSO') return 'genera'
  if (STATI_TERMINALI.has(props.statoCodice)) return 'scarica'
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

// ── EMESSO: hook beforeGenerate per dialog conferma ──
// Resolve true (procedi) / false (abort) tramite Promise wrapper sopra
// useConfirmAction (che e' callback-based). Lookup leggero della lista
// versioni per popolare il messaggio con il progressivo + data.
async function confirmRigenerazione() {
  docStore.setSorgente(SORGENTE_CODE, props.preventivoId)
  try {
    await docStore.fetchList({ page: 1, page_size: 1 })
  } catch {
    // Errore lookup non blocca: chiediamo conferma generica.
  }
  const versioni = docStore.totalRecords ?? 0
  const ultima = docStore.items?.[0]
  const dataUltima = ultima?.generato_at
    ? new Date(ultima.generato_at).toLocaleString('it-IT')
    : null
  const message = versioni > 0 && dataUltima
    ? t('preventivi.pdf.confirm_rigenera_message', {
        versione: ultima.progressivo_sorgente,
        data: dataUltima,
        prossima: versioni + 1,
      })
    : t('preventivi.pdf.confirm_genera_first_message')

  return new Promise(resolve => {
    confirm.require({
      header: t('preventivi.pdf.confirm_genera_header'),
      message,
      icon: 'pi pi-file-pdf',
      acceptLabel: t('common.confirm'),
      rejectLabel: t('common.cancel'),
      rejectClass: 'p-button-secondary',
      accept: () => resolve(true),
      reject: () => resolve(false),
      onHide: () => resolve(false),
    })
  })
}

// ── Stato terminale: dialog lista PDF per scarica ──
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
      class="app-pdf-btn"
      @click="onPreviewClick"
    />

    <!-- EMESSO: Genera con conferma. Riusa GeneraPdfButton (lookup
         template + branch 0/1/>1) iniettando la conferma via prop. -->
    <GeneraPdfButton
      v-else-if="mode === 'genera'"
      sorgente-code="PREVENTIVO"
      :sorgente-id="preventivoId"
      :emittente-fiscale-id="emittenteFiscaleId"
      :before-generate="confirmRigenerazione"
      :label="t('preventivi.pdf.label_genera')"
      :tooltip="t('preventivi.pdf.tooltip_genera')"
      :disabled="baseDisabled"
      auto-download
      size="small"
    />

    <!-- Stato terminale: solo Scarica via dialog lista. -->
    <Button
      v-else-if="mode === 'scarica'"
      icon="pi pi-file-pdf"
      :label="t('preventivi.pdf.label_scarica')"
      v-tooltip.top="t('preventivi.pdf.tooltip_scarica')"
      size="small"
      text
      :disabled="baseDisabled"
      class="app-pdf-btn"
      @click="onScaricaClick"
    />

    <!-- Stato non riconosciuto / detail non caricato. -->
    <Button
      v-else
      icon="pi pi-file-pdf"
      :label="t('preventivi.pdf.label_genera')"
      size="small"
      text
      disabled
      class="app-pdf-btn"
    />

    <PdfDocumentiSorgenteDialog
      v-model:visible="dialogVisible"
      sorgente-code="PREVENTIVO"
      :sorgente-id="preventivoId"
    />
  </div>
</template>
