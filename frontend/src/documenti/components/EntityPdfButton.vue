<script setup>
// Scopo: Building block "Pulsante PDF stato-aware" per qualunque entita'
//        documentale (preventivi, contratti, offerte, ...). Estratto
//        dall'unione dei tre cloni `*PdfButton.vue` (regola "estrai BB
//        alla seconda occorrenza", memoria `feedback_regola_del_2_estrai_bb`).
//
// Tre modalita' del bottone, DATA-DRIVEN dalla capability `pdf` del detail
// BE (`fn_available_actions_*` -> blocco `pdf {mode, allow_allegati}`, letto
// da `config.stati_doc_*.pdf_mode/pdf_allow_allegati`). Mappa `pdf.mode`:
//   - `PREVIEW` -> `preview`:  stati pre-emissione (es. BOZZA/DRAFT) ->
//                 anteprima on-the-fly via store `documentiPerSorgente.anteprima`,
//                 nessun record DB, scarica/apre subito;
//   - `ARCHIVE` -> `scarica`:  stati post-emissione (es. EMESSA/ATTIVO/CESSATO)
//                 -> apre `PdfDocumentiSorgenteDialog` con la lista archiviata;
//                 il PDF e' gia' stato generato dal BE alla transizione di
//                 emissione;
//   - `NONE`/null -> `disabled`: stato senza gestione PDF (es. ANNULLATO),
//                 detail non caricato o id mancante.
//
// Prima questa mappa era hardcoded lato caller (liste `STATI_*_ANTEPRIMA_PDF`
// / `_CON_DOCUMENTO` in `constants.js`): un nuovo stato non riflesso degradava
// il bottone a disabled. Ora la verita' sta nel modello, come `available_actions`
// (brief `brief-db-pdf-capabilities-data-driven.md`).
//
// L'append allegati (post-emissione) e' data-driven da `pdf.allow_allegati`.
//
// Convenzione i18n: il caller passa `i18nPrefix` (es. `'vendite.offerte.pdf'`)
// e il BB risolve `<prefix>.label_anteprima` / `tooltip_anteprima` /
// `label_scarica` / `tooltip_scarica`. Il titolo del dialog scarica e'
// invece passato gia' t-formattato (`dialogTitle`), per evitare logica
// i18n nel BB.

import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import PdfDocumentiSorgenteDialog from './PdfDocumentiSorgenteDialog.vue'
import { useDocumentiPerSorgenteStore } from '../stores/documentiPerSorgente'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { MANAGE_ICONS } from '../../core/constants'
import { downloadBlob } from '../../core/utils/download'
import { PDF_MODE } from '../constants'

const props = defineProps({
  // Codice sorgente registrato lato BE/FE (whitelist documenti).
  sorgenteCode: { type: String, required: true },
  // Id dell'entita' sorgente (preventivo, contratto, offerta, ...).
  entityId: { type: [Number, null], required: true },
  // Capability PDF data-driven dal detail BE: `{ mode, allow_allegati }`
  // (blocco `pdf` di `fn_available_actions_*`). `mode` in
  // PREVIEW|ARCHIVE|NONE; `allow_allegati` boolean. null = detail non
  // caricato (create pre-save) -> bottone disabled.
  pdf: { type: [Object, null], default: null },
  // Prefix i18n per le label/tooltip del bottone (es. 'vendite.contratti.pdf').
  i18nPrefix: { type: String, required: true },
  // Titolo del dialog "Scarica PDF" — gia' t-formattato dal caller
  // (i diversi domini usano parametri differenti: {numero} vs {codice}).
  // Vuoto/null = default del dialog.
  dialogTitle: { type: String, default: '' },
})

const { t } = useI18n()
const { execute, loading: previewing } = useApiHandler()
const docStore = useDocumentiPerSorgenteStore()

const dialogVisible = ref(false)

const baseDisabled = computed(() => !props.entityId)

const mode = computed(() => {
  switch (props.pdf?.mode) {
    case PDF_MODE.PREVIEW: return 'preview'
    case PDF_MODE.ARCHIVE: return 'scarica'
    default: return 'disabled' // PDF_MODE.NONE | null (detail non caricato)
  }
})

const allowAllegati = computed(() => props.pdf?.allow_allegati === true)

// Etichetta + tooltip dinamici sulla modalita' corrente. Per `disabled`
// (stato sconosciuto / id mancante) usiamo la label "scarica" come
// fallback neutro — coerente col pattern precedente dei 3 wrapper.
const buttonLabel = computed(() => {
  const key = mode.value === 'preview' ? 'label_anteprima' : 'label_scarica'
  return t(`${props.i18nPrefix}.${key}`)
})

const buttonTooltip = computed(() => {
  if (mode.value === 'disabled') return ''
  const key = mode.value === 'preview' ? 'tooltip_anteprima' : 'tooltip_scarica'
  return t(`${props.i18nPrefix}.${key}`)
})

function onButtonClick() {
  if (mode.value === 'preview') return onPreviewClick()
  if (mode.value === 'scarica') return onScaricaClick()
}

async function onPreviewClick() {
  if (baseDisabled.value) return
  docStore.setSorgente(props.sorgenteCode, props.entityId)
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
  <div>
    <!-- Unico Button: label/tooltip/disabled/handler derivati da `mode`.
         Disabled se manca l'id (baseDisabled) OPPURE se lo stato non ha
         gestione PDF (`mode === 'disabled'`, es. ANNULLATO o detail non
         caricato). `onButtonClick` non fa nulla fuori da preview/scarica.
         Lo stato `loading` di preview applica solo in modalita' preview. -->
    <Button
      :icon="MANAGE_ICONS.PDF"
      :label="buttonLabel"
      v-tooltip.top="buttonTooltip"
      size="small"
      text
      :loading="mode === 'preview' && previewing"
      :disabled="baseDisabled || mode === 'disabled'"
      class="app-pdf-btn app-escape"
      @click="onButtonClick"
    />

    <PdfDocumentiSorgenteDialog
      v-model:visible="dialogVisible"
      :sorgente-code="sorgenteCode"
      :sorgente-id="entityId"
      :allow-allegati="allowAllegati"
      :title="dialogTitle"
    />
  </div>
</template>
