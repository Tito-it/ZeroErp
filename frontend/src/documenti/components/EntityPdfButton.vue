<script setup>
// Scopo: Building block "Pulsante PDF stato-aware" per qualunque entita'
//        documentale (preventivi, contratti, offerte, ...). Estratto
//        dall'unione dei tre cloni `*PdfButton.vue` (regola "estrai BB
//        alla seconda occorrenza", memoria `feedback_regola_del_2_estrai_bb`).
//
// Tre modalita' del bottone, dedotte da `statoCodice`:
//   - `preview`:  stati pre-emissione (es. BOZZA/DRAFT) -> anteprima
//                 on-the-fly via store `documentiPerSorgente.anteprima`,
//                 nessun record DB, scarica/apre subito;
//   - `scarica`:  stati post-emissione (es. EMESSA/ATTIVO/CESSATO) ->
//                 apre `PdfDocumentiSorgenteDialog` con la lista
//                 archiviata; il PDF e' gia' stato generato dal BE alla
//                 transizione di emissione;
//   - `disabled`: stato sconosciuto / detail non caricato / id mancante.
//
// L'append allegati (post-emissione) e' opzionale, abilitato quando lo
// stato corrente e' incluso in `statiAppendAllegati`.
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
import { downloadBlob } from '../../core/utils/download'

const props = defineProps({
  // Codice sorgente registrato lato BE/FE (whitelist documenti).
  sorgenteCode: { type: String, required: true },
  // Id dell'entita' sorgente (preventivo, contratto, offerta, ...).
  entityId: { type: [Number, null], required: true },
  // Stato corrente dell'entita' (codice interno).
  statoCodice: { type: [String, null], default: null },
  // Stati in cui mostrare il bottone "Anteprima" (preview on-the-fly).
  statiPreview: { type: Array, default: () => [] },
  // Stati in cui mostrare "Scarica PDF" (lista dei PDF gia' generati).
  statiConDocumento: { type: Array, default: () => [] },
  // Stati in cui abilitare l'append allegati (per-riga nel dialog).
  statiAppendAllegati: { type: Array, default: () => [] },
  // Prefix i18n per le label/tooltip del bottone (es. 'contratti.pdf').
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

const baseDisabled = computed(
  () => !props.entityId || !props.statoCodice,
)

const mode = computed(() => {
  if (!props.statoCodice) return 'disabled'
  if (props.statiPreview.includes(props.statoCodice)) return 'preview'
  if (props.statiConDocumento.includes(props.statoCodice)) return 'scarica'
  return 'disabled'
})

const allowAllegati = computed(
  () => props.statiAppendAllegati.includes(props.statoCodice),
)

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
  <div class="entity-pdf-button">
    <!-- Unico Button: label/tooltip/disabled/handler derivati da `mode`.
         `mode === 'disabled'` -> baseDisabled true e niente click handler.
         Lo stato `loading` di preview applica solo in modalita' preview. -->
    <Button
      icon="pi pi-file-pdf"
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
