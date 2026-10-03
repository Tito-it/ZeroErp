<script setup>
// Scopo: Dialog modale generico per l'export di una lista
//        configurabile (DEF-1). Espone scelta del formato (CSV/Excel)
//        e bottone "Scarica" che emette `@export(format)` al parent.
//
//        Il parent rimane responsabile della chiamata API: il dialog
//        e' un "form di scelta formato", non chiama il backend e non
//        gestisce il download. Questo permette al parent di costruire
//        la query string corretta (filtri attivi della lista chiamante)
//        e di delegare il download a `useFileDownload`.
//
//        Su Chrome/Edge moderni HTTPS l'utente vedra' poi il dialog
//        nativo "Salva con nome" del sistema operativo (gestito da
//        `useFileDownload`). Su Firefox/Safari il file finisce nella
//        cartella download default del browser. Mostriamo un hint
//        coerente nel dialog tramite `isFileSystemAccessSupported()`.
//
//        Riusabile cross-dominio: ogni lista in DEF-8 lo adotta
//        passando i propri `formati` (default `['csv','xlsx']`) e
//        ascoltando `@export`.

import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppDialog from './AppDialog.vue'
import SelectButton from 'primevue/selectbutton'
import Message from 'primevue/message'
import { isFileSystemAccessSupported } from '../composables/useFileDownload'
import { MANAGE_ICONS } from '../constants'
import { useFotografiaDialog } from '../composables/useFotografiaDialog'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Formati ammessi. Ogni voce: { code, label, icon }. Default
  // CSV + Excel (DEF-1 v1). Il caller puo' restringere se serve.
  formati: {
    type: Array,
    default: () => [
      { code: 'csv', labelKey: 'lista_config.export_csv', icon: MANAGE_ICONS.FORMATO_CSV },
      { code: 'xlsx', labelKey: 'lista_config.export_xlsx', icon: MANAGE_ICONS.FORMATO_XLSX },
    ],
  },
  // Stato loading guidato dal parent (durante la chiamata API).
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'export'])

const { t } = useI18n()

// Formato selezionato (default primo della lista).
const selectedFormat = ref(props.formati[0]?.code ?? 'csv')

// Reset al primo formato quando il dialog viene riaperto, cosi' la
// scelta non "ricorda" la sessione precedente — pattern coerente con
// dialog modali "azione one-shot".
watch(() => props.visible, (vis) => {
  if (vis) selectedFormat.value = props.formati[0]?.code ?? 'csv'
})

// Opzioni SelectButton: traduzione lazy + icona PrimeIcons inline.
const formatOptions = computed(() =>
  props.formati.map((f) => ({
    label: t(f.labelKey || f.label || `lista_config.export_${f.code}`),
    value: f.code,
    icon: f.icon,
  })),
)

const fsApiHint = computed(() =>
  isFileSystemAccessSupported()
    ? t('export_dialog.hint_fs_api')
    : t('export_dialog.hint_browser_default'),
)

function onConfirm() {
  emit('export', selectedFormat.value)
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ selectedFormat: selectedFormat.value }), { visibile: () => props.visible })
</script>

<template>
  <!-- Pilota building block AppDialog (chrome + FormFooter integrato).
       width='sm' = DIALOG_WIDTH.sm (480px, invariato). Il cancel chiude via
       update:visible propagato da AppDialog. ESC spento durante l'export lo
       fa il BB da `loading` (2026-09-18): qui non si riscrive. -->
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    @update:visible="(v) => emit('update:visible', v)"
    :header="t('export_dialog.title')"
    width="sm"
    :loading="loading"
    :save-label="t('export_dialog.scarica')"
    @save="onConfirm"
  >
    <div class="export-dialog-content">
      <div class="form-field">
        <label>{{ t('export_dialog.formato_label') }}</label>
        <SelectButton
          v-model="selectedFormat"
          :options="formatOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
        >
          <template #option="{ option }">
            <i v-if="option.icon" :class="option.icon" />
            <span>{{ option.label }}</span>
          </template>
        </SelectButton>
      </div>

      <Message severity="info" :closable="false" size="small">
        {{ fsApiHint }}
      </Message>
    </div>
  </AppDialog>
</template>

<style scoped>
.export-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.5rem 0;
}
.export-dialog-content :deep(.p-selectbutton .p-button) {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}
</style>
