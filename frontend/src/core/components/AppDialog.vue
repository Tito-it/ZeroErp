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
//   - ⭐ il tasto DETTO in alto a destra (2026-10-11, Tid): l'etichetta «Esc»
//     (`app-kbd`), come accanto alla X del drawer — ma qui SENZA X (la regola
//     qui sopra resta). Non e' un pulsante: dice che ESC chiude, come Annulla.
//     Non c'e' dove ESC e' spento (`closeOnEscape=false`: dirlo sarebbe
//     falso) ne' su un dispositivo senza tastiera fisica (`ui.isCompatto`).
//     Il titolo lo rende lo slot `#header` (PrimeVue lo sostituisce intero):
//     l'id per `aria-labelledby` lo diamo noi (`useId`), via `pt.root`.
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
import { computed, provide, ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import FormFooter from './FormFooter.vue'
import { DIALOG_CHROME, DIALOG_WIDTH } from '../constants'
import { READONLY_KEY, useInjectReadonly } from '../composables/useReadonlyMode'
import { TASTO, nomeTasto } from '../utils/scorciatoie'
import { useUiStore } from '../../stores/ui'

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
  // ⭐ USCIRE CON DATI INSERITI CHIEDE (2026-10-03, D-14 di
  //    work-done/analisi-fe-chrome-drawer.md, decisione di Tid). Ogni
  //    uscita — X, ESC, clic sulla maschera, Annulla, e il `chiudi` dello slot
  //    `#footer` — passa da `confermaUscita(chiudi)`: un dialog con dei campi
  //    gli passa il `chiudiConConferma` della sua fotografia
  //    (useDrawerFormPreserve), che chiede solo se qualcosa e' cambiato. Fino a
  //    quel giorno i 43 dialog con campi si chiudevano in silenzio, buttando
  //    cio' che si era scritto (rilievo di Tid sul dialog dei componenti).
  //    Mirror di `AppDrawer`. Presidio: `check-dialog-chrome.mjs` (un
  //    `AppDialog` con campi deve passarla).
  confermaUscita: { type: Function, default: (chiudi) => chiudi() },
})

const emit = defineEmits(['update:visible', 'save', 'cancel'])

const { t, te } = useI18n()
const ui = useUiStore()
const titoloId = useId()

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

// ⭐ IL FUOCO ENTRA NEL DIALOG ALL'APERTURA (2026-10-11, rilievo di Tid: «ESC
//    funziona su qualcuno, non su tutti»). L'ESC qui sopra si sente solo se
//    il fuoco e' DENTRO il dialog. PrimeVue lo porta dentro da se' solo verso
//    un `[autofocus]` o, in mancanza, verso la SUA X — che con `closable:
//    false` non c'e'. Senza un campo `autofocus` il fuoco restava fuori (sul
//    pulsante del drawer sotto, o sul body): l'ESC arrivava a `document`,
//    `escapeSoloInCima` lo ingoiava, e il dialog non si chiudeva. Funzionava
//    quindi solo nei dialog che un `autofocus` ce l'avevano, per caso.
//    Qui il fuoco va sulla RADICE (`tabindex=-1`, non e' una tappa del Tab),
//    se non e' gia' dentro: un `[autofocus]` lo sposta poi PrimeVue a fine
//    animazione, e vince lui.
const dialogRef = ref(null)
function onShow() {
  const radice = dialogRef.value?.container
  if (radice && !radice.contains(document.activeElement)) radice.focus({ preventScroll: true })
}

// Le sezioni pass-through di PrimeVue: la radice `.p-dialog` — testa, corpo e
// footer compresi — riceve il keydown, in discesa e in risalita.
// `app-riquadro` sul contenuto: le soglie dei form dentro la dialog si
// misurano sulla dialog, non sulla finestra (main.css, «I riquadri»).
const pt = {
  root: { 'aria-labelledby': titoloId, tabindex: '-1', onKeydownCapture: onRootKeydownCapture, onKeydown: onRootKeydown },
  content: { class: 'app-riquadro' },
}

// Contesto readonly per i discendenti del dialog (FormFooter + eventuali
// campi). Se `readonly` non e' passata -> ri-fornisce il valore ereditato
// (comportamento invariato). Se passata -> ha precedenza, scollegando il
// footer del dialog dal readonly combinato del drawer padre.
const parentReadonly = useInjectReadonly()
provide(
  READONLY_KEY,
  computed(() => (props.readonly === undefined ? parentReadonly.value : props.readonly)),
)

// Scopo: l'UNICA uscita senza salvare — footer Annulla/Chiudi, ESC, `chiudi`
//        dello slot (e la X o la maschera, se un consumer le riaccende).
//        `chiudi` esce e basta, ordine fisso: prima `cancel`, poi
//        `update:visible=false`; `onCancel` ci arriva passando da
//        `confermaUscita`.
function chiudi() {
  emit('cancel')
  emit('update:visible', false)
}
function onCancel() {
  props.confermaUscita(chiudi)
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
    ref="dialogRef"
    :visible="visible"
    :header="header"
    :modal="modal"
    :closable="closable"
    :close-on-escape="false"
    :dismissable-mask="dismissableMask"
    :style="{ width: resolvedWidth }"
    :pt="pt"
    @update:visible="onDialogVisible"
    @show="onShow"
  >
    <template #header="{ class: classeTitolo }">
      <span :id="titoloId" :class="classeTitolo">{{ header }}</span>
      <kbd v-if="closeOnEscape && !ui.isCompatto" class="app-kbd app-dialog-tasto" aria-hidden="true">
        {{ nomeTasto(t, te, TASTO.ESC) }}
      </kbd>
    </template>

    <slot />

    <template #footer>
      <!-- Default: FormFooter standard. Slot #footer per override (terzo
           bottone, severity dinamica, wizard) mantenendo il chrome AppDialog. -->
      <slot name="footer" :chiudi="onCancel">
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
