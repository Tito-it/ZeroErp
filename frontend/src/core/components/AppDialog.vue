<script setup>
// Scopo: building block standard per Dialog modali "azione" (conferma, form
// one-shot, registrazione esito). Mirror di AppDrawer per le Dialog.
//
// Incapsula il chrome uniforme:
//   - modal (default true) + closable (default true), entrambi override-abili
//   - width da scala centralizzata DIALOG_WIDTH (sm|md|lg|xl) — niente px
//     hardcoded sparsi nei singoli dialog
//   - v-model:visible standard
//   - footer = FormFooter integrato di default (icone ← / ✓, responsive
//     icon-only sotto 1024px, shortcut Ctrl+S). Override via slot #footer
//     per i casi speciali (severity dinamica, wizard multi-step).
//
// Uso tipico:
//   <AppDialog v-model:visible="visible" :header="t('...')" width="sm"
//     :loading="loading" :save-disabled="!canSave" :save-label="t('...')"
//     @save="onSave" @cancel="onCancel">
//     <!-- body -->
//   </AppDialog>
//
// Footer custom (es. terzo bottone, severity dinamica):
//   <AppDialog ...><template #footer> ... </template></AppDialog>
//
// Dialog informativo senza footer:
//   <AppDialog ... hide-footer>...</AppDialog>
import { computed, provide } from 'vue'
import Dialog from 'primevue/dialog'
import FormFooter from './FormFooter.vue'
import { DIALOG_WIDTH } from '../constants'
import { READONLY_KEY, useInjectReadonly } from '../composables/useReadonlyMode'

const props = defineProps({
  visible: { type: Boolean, required: true },
  header: { type: String, default: '' },
  // Taglia da DIALOG_WIDTH: 'sm' | 'md' | 'lg' | 'xl'. Default 'md'.
  width: { type: String, default: 'md' },
  modal: { type: Boolean, default: true },
  closable: { type: Boolean, default: true },
  closeOnEscape: { type: Boolean, default: true },
  dismissableMask: { type: Boolean, default: false },
  // --- Footer FormFooter integrato (pass-through) ---
  loading: { type: Boolean, default: false },
  saveDisabled: { type: Boolean, default: false },
  saveLabel: { type: String, default: null },
  cancelLabel: { type: String, default: null },
  saveSeverity: { type: String, default: null },
  closeOnly: { type: Boolean, default: false },
  // Nessun footer (dialog puramente informativo / lista).
  hideFooter: { type: Boolean, default: false },
  // Override esplicito del contesto readonly per il contenuto/footer del
  // dialog. Default `undefined` = eredita il readonly dell'albero (parent
  // drawer/view). I dialog d'AZIONE lanciati da un drawer "locked-by-stato"
  // (es. cessazione contratto da contratto ATTIVO) devono passare qui il
  // readonly-da-PERMESSI puro (non quello combinato con lo stato), altrimenti
  // FormFooter eredita readonly=true e nasconde il pulsante di conferma —
  // pur essendo l'azione legittima sullo stato corrente.
  readonly: { type: Boolean, default: undefined },
})

const emit = defineEmits(['update:visible', 'save', 'cancel'])

// Scopo: risolve la larghezza dalla scala; fallback 'md' se taglia ignota.
const resolvedWidth = computed(() => DIALOG_WIDTH[props.width] || DIALOG_WIDTH.md)

// Contesto readonly per i discendenti del dialog (FormFooter + eventuali
// campi). Se `readonly` non e' passata -> ri-fornisce il valore ereditato
// (comportamento invariato). Se passata -> ha precedenza, scollegando il
// footer del dialog dal readonly combinato del drawer padre.
const parentReadonly = useInjectReadonly()
provide(
  READONLY_KEY,
  computed(() => (props.readonly === undefined ? parentReadonly.value : props.readonly)),
)

function onCancel() {
  emit('cancel')
  emit('update:visible', false)
}

function onSave() {
  emit('save')
}
</script>

<template>
  <Dialog
    :visible="visible"
    :header="header"
    :modal="modal"
    :closable="closable"
    :close-on-escape="closeOnEscape"
    :dismissable-mask="dismissableMask"
    :style="{ width: resolvedWidth }"
    @update:visible="emit('update:visible', $event)"
  >
    <slot />

    <template v-if="!hideFooter" #footer>
      <!-- Default: FormFooter standard. Slot #footer per override (terzo
           bottone, severity dinamica, wizard) mantenendo il chrome AppDialog. -->
      <slot name="footer">
        <FormFooter
          :save-label="saveLabel"
          :cancel-label="cancelLabel"
          :save-severity="saveSeverity"
          :loading="loading"
          :disabled="saveDisabled"
          :close-only="closeOnly"
          @cancel="onCancel"
          @save="onSave"
        />
      </slot>
    </template>
  </Dialog>
</template>
