<script setup>
// Scopo: building block standard per Dialog modali "azione" (conferma, form
// one-shot, registrazione esito). Mirror di AppDrawer per le Dialog.
//
// ⛔ `primevue/dialog` si importa SOLO qui (presidio: scripts/check-dialog-chrome.mjs).
//
// Incapsula il chrome uniforme:
//   - chrome (modal/closable/closeOnEscape/dismissableMask) con i default di
//     DIALOG_CHROME (core/constants.js) — LA sede unica, condivisa con la
//     ConfirmDialog globale. Un cambio di layout e' una riga la', non un giro
//     sui 48 dialog. ⛔ Niente X in alto: il footer di un dialog e' sempre
//     visibile, ogni dialog ha gia' Annulla/Chiudi (decisione Tid, 2026-09-18).
//   - `header` OBBLIGATORIO: un Dialog PrimeVue senza titolo rende comunque la
//     riga di testa, e l'unico figlio (le azioni) finisce a sinistra — era la
//     «X a sinistra» vista in-app, non un secondo chrome.
//   - ESC = Annulla, e si spegne mentre `loading`: a salvataggio in volo il
//     dialog non si chiude sotto la risposta. Era riscritto a mano in due
//     dialog (ExportDialog, AttivaVersioneDialog): ora lo fa il BB.
//     ⭐ E chiude SOLO QUESTO dialog: ESC si gestisce sulla RADICE del dialog
//     (`pt.root.onKeydown`, che nella risalita sta prima di `document`), non
//     col listener `document` di PrimeVue — che convive con quello del Drawer
//     sotto, e un ESC li chiudeva entrambi (rilievo di Tid, 2026-09-18). Il
//     listener di PrimeVue resta spento (`close-on-escape=false`) e
//     `core/utils/escapeSoloInCima` ingoia l'ESC che sfugge alla radice.
//     Un campo con la TENDINA APERTA (AutoComplete, Select, DatePicker...)
//     tiene l'ESC per se': la chiude lui, il dialog resta.
//   - UNA via d'uscita: Annulla/Chiudi ed ESC passano dallo stesso handler ed
//     emettono `cancel` e poi `update:visible=false`. Un consumer che pulisce
//     stato su `@cancel` lo vede da qualunque uscita.
//   - width da scala centralizzata DIALOG_WIDTH (sm|md|lg|xl) — niente px
//     hardcoded sparsi nei singoli dialog
//   - v-model:visible standard
//   - footer = FormFooter integrato di default (icone ← / ✓, responsive
//     icon-only sotto 1024px, shortcut Ctrl+S). Override via slot #footer
//     per i casi speciali (severity dinamica, wizard multi-step).
//     ⛔ Un footer c'e' SEMPRE: senza X, un dialog senza footer non avrebbe
//     nessuna uscita visibile. `hideFooter` e' stato tolto il 2026-09-18.
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
// Override di chrome sul tag = una decisione, e si commenta sopra al tag
// (unico oggi: EmittenteAttivoDialog, `:close-on-escape="false"`).
import { computed, provide } from 'vue'
import Dialog from 'primevue/dialog'
import FormFooter from './FormFooter.vue'
import { DIALOG_CHROME, DIALOG_WIDTH } from '../constants'
import { READONLY_KEY, useInjectReadonly } from '../composables/useReadonlyMode'

const props = defineProps({
  visible: { type: Boolean, required: true },
  header: { type: String, required: true },
  // Taglia da DIALOG_WIDTH: 'sm' | 'md' | 'lg' | 'xl'. Default 'md'.
  width: { type: String, default: 'md' },
  modal: { type: Boolean, default: DIALOG_CHROME.modal },
  closable: { type: Boolean, default: DIALOG_CHROME.closable },
  closeOnEscape: { type: Boolean, default: DIALOG_CHROME.closeOnEscape },
  dismissableMask: { type: Boolean, default: DIALOG_CHROME.dismissableMask },
  // --- Footer FormFooter integrato (pass-through) ---
  loading: { type: Boolean, default: false },
  saveDisabled: { type: Boolean, default: false },
  saveLabel: { type: String, default: null },
  cancelLabel: { type: String, default: null },
  saveSeverity: { type: String, default: null },
  closeOnly: { type: Boolean, default: false },
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

// Scopo: ESC chiude solo se il dialog non sta lavorando — la regola sta qui e
//        non nei consumer.
const escapeAttivo = computed(() => props.closeOnEscape && !props.loading)

// ⭐ ESC in DISCESA (capture): il dialog lo vede per PRIMO, prima del campo a
//    fuoco. Se quel campo ha la TENDINA APERTA (AutoComplete della lookup,
//    Select, DatePicker, MultiSelect) l'ESC e' suo — chiude la tendina, il
//    dialog resta. Il segnale e' lo standard ARIA `aria-expanded="true"`, che
//    tutti i componenti mettono sul controllo — letto qui, prima che lo
//    abbassino. Altrimenti si chiude subito, e non dopo, perche' il `Select` di
//    PrimeVue 4 su ESC ferma la risalita per conto suo anche a tendina chiusa
//    (un `@todo` loro): in risalita l'ESC non arriverebbe.
//    ⛔ Non `event.defaultPrevented`: l'AutoComplete di PrimeVue 4 fa
//    `preventDefault()` su ESC SEMPRE, anche a tendina chiusa — e cosi' ESC in
//    «Abbina fattura» non chiudeva niente (rilievo di Tid, 2026-09-18).
function onRootKeydownCapture(event) {
  if (event.code !== 'Escape') return
  if (event.target?.closest?.('[aria-expanded="true"]')) return
  if (escapeAttivo.value) onCancel()
}

// Scopo: ESC in RISALITA: si ferma qui e non arriva a `document`, dove il
//        Drawer sotto si chiuderebbe. Vale anche per l'ESC di una tendina.
function onRootKeydown(event) {
  if (event.code === 'Escape') event.stopPropagation()
}

// Le sezioni pass-through di PrimeVue: la radice `.p-dialog` — testa, corpo e
// footer compresi — riceve il keydown, in discesa e in risalita.
const pt = { root: { onKeydownCapture: onRootKeydownCapture, onKeydown: onRootKeydown } }

// Contesto readonly per i discendenti del dialog (FormFooter + eventuali
// campi). Se `readonly` non e' passata -> ri-fornisce il valore ereditato
// (comportamento invariato). Se passata -> ha precedenza, scollegando il
// footer del dialog dal readonly combinato del drawer padre.
const parentReadonly = useInjectReadonly()
provide(
  READONLY_KEY,
  computed(() => (props.readonly === undefined ? parentReadonly.value : props.readonly)),
)

// Scopo: l'UNICA uscita senza salvare — footer Annulla/Chiudi ed ESC (e la X o
//        la maschera, se un consumer le riaccende). Ordine fisso: prima
//        `cancel`, poi `update:visible=false`.
function onCancel() {
  emit('cancel')
  emit('update:visible', false)
}

// Scopo: il Dialog PrimeVue emette `update:visible` solo con `false` (ESC,
//        X, maschera): lo si porta sulla stessa via del footer.
function onDialogVisible(v) {
  if (!v) onCancel()
  else emit('update:visible', v)
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
    :close-on-escape="false"
    :dismissable-mask="dismissableMask"
    :style="{ width: resolvedWidth }"
    :pt="pt"
    @update:visible="onDialogVisible"
  >
    <slot />

    <template #footer>
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
