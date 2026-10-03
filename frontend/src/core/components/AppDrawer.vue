<script setup>
// Scopo: LA SEDE DEL CHROME DEI DRAWER LATERALI (riscritto il 2026-10-03,
//        D-3 di work-done/analisi-fe-chrome-drawer.md, ok Tid).
//        Mirror di `AppDialog` per i drawer: tutto cio' che 82 drawer
//        riscrivevano a mano sta qui una volta, e il chiamante porta solo il
//        CONTENUTO.
//
// ⭐ CHE COSA E' CHROME (e quindi sta qui):
//    · la testata — `DrawerTitle` con titolo, icona, azione, «modificato», il
//      conteggio delle cose nuove e il badge di sola lettura;
//    · la larghezza — un valore della scala `DRAWER_WIDTH`, e solo quello;
//    · l'uscita — X, ESC, clic fuori, Annulla/Chiudi passano TUTTE da
//      `confermaUscita` (il `chiudiConConferma` di useDrawerFormPreserve o di
//      unisciFotografie): e' un gesto solo, «esco»;
//    · il montaggio a fine animazione — `useDrawerContentReady` interno: il
//      contenuto pesante non si monta durante lo slide (niente rimbalzo);
//    · il corpo — `app-drawer-content`, con `app-readonly` dalla catena (salvo
//      `proteggiCorpo: false`, per i drawer che proteggono nascondendo le azioni);
//    · il footer — FISSO in basso (slot `#footer` di PrimeVue, decisione D-2
//      di Tid del 2026-10-03): il Salva resta a vista su un form lungo.
//
// ⛔ CHE COSA NON E' CHROME (e resta del chiamante, nello slot di default):
//    `DrawerEntityHeader`, `DrawerActionsBar`, le schede, le liste
//    (`DrawerTabLista`), il form inline con il suo Annulla/Salva, il
//    caricamento del dettaglio. Sono BB di contenuto che esistono gia': una
//    sede che li assorbisse diventerebbe un drawer-di-tutto.
//
// FOOTER — `footer`:
//    'form'    Annulla + Salva (default): emette `save`; Annulla = uscita.
//    'chiudi'  il solo «Chiudi» (drawer di lista / consultazione).
//    'nessuno' niente: il caso delle forme master-detail mentre il form inline
//              e' aperto (`:footer="formAperto ? 'nessuno' : 'chiudi'"`) — il
//              form ha gia' il suo Annulla/Salva, un «Chiudi» lo duplicherebbe.
//    Lo slot `#footer-azioni` AGGIUNGE pulsanti a sinistra del footer standard
//    (il «Ripristina» delle personalizzazioni: 2026-10-03, regola del 2, ok
//    Tid — era scritto uguale in due drawer, col CSS gia' divergente).
//    Lo slot `#footer` sostituisce tutto, per i casi veri (wizard): chi lo usa
//    si prende anche l'uscita, con `chiudi` dello slot.
//
// READONLY — la catena (`READONLY_KEY`) arriva gia' dal provider della vista.
//    `readonly` la puo' solo STRINGERE (es. un documento non in bozza): il
//    guscio la ri-provide in OR, cosi' testata, FormFooter e ogni figlio la
//    vedono senza che il chiamante faccia `provide`.
//
// Uso:
//   <AppDrawer
//     :visible="visible" @update:visible="(v) => emit('update:visible', v)"
//     :title="t('…')" :icon="MANAGE_ICONS.X" :action="t('common.edit')"
//     :width="DRAWER_WIDTH.STANDARD"
//     :modificato="modificato" :conferma-uscita="chiudiConConferma"
//     :loading="loading" :save-disabled="!canSave" @save="onSave"
//   >
//     <div class="form-grid">…</div>
//   </AppDrawer>
//
// Doc: frontend-standards §«Drawer (nuovo e modifica)», catalogo BB frontend.
import { computed, inject, provide, ref } from 'vue'
import Drawer from 'primevue/drawer'
import DrawerTitle from './DrawerTitle.vue'
import FormFooter from './FormFooter.vue'
import { gestoreVisibile } from '../composables/useDrawerFormPreserve'
import { useDrawerContentReady } from '../composables/useDrawerContentReady'
import { READONLY_KEY } from '../composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../constants'

const props = defineProps({
  visible: { type: Boolean, required: true },
  title: { type: String, required: true },
  icon: { type: String, default: '' },
  action: { type: String, default: '' },
  // Un numero accanto al titolo («N nuove»): vedi DrawerTitle. A 0 non si vede.
  conteggio: { type: Number, default: 0 },
  conteggioTooltip: { type: String, default: null },
  // ⛔ Solo un valore della scala: `'1000px'` scritto a mano e' il difetto che
  //    l'analisi ha trovato (D-4). Il validatore avvisa in sviluppo, e il guard
  //    `check-drawer-width.mjs` ferma il valore scritto nel tag.
  width: {
    type: String,
    default: DRAWER_WIDTH.STANDARD,
    validator: (v) => Object.values(DRAWER_WIDTH).includes(v),
  },
  // Clic fuori chiude? Un'espressione ha senso: `!hasChildOpen` (non si
  // chiude il padre mentre un figlio e' aperto), `!loading`.
  dismissable: { type: Boolean, default: true },
  // Modifiche non salvate: `modificato` colora l'azione nella testata,
  // `confermaUscita(chiudi)` decide se chiedere prima di uscire.
  modificato: { type: Boolean, default: false },
  confermaUscita: { type: Function, default: (chiudi) => chiudi() },
  readonly: { type: Boolean, default: false },
  // ⚠️ `app-readonly` sul corpo (pointer-events: none salvo filtri, paginazione,
  //    schede, `.app-escape`) protegge un FORM. Un drawer che protegge la sola
  //    lettura NASCONDENDO le azioni — consultazione, liste con menu di riga,
  //    personalizzazioni dell'utente — passa `:proteggi-corpo="false"`: la
  //    catena readonly arriva lo stesso ai figli (FormFooter, DrawerTitle), ma
  //    il corpo resta cliccabile. Senza, in sola lettura si spegnevano anche il
  //    kebab di riga (`RowActionsMenu` non e' `.app-escape`) e i pulsanti di
  //    consultazione (trovato il 2026-10-03 migrando i drawer).
  proteggiCorpo: { type: Boolean, default: true },
  footer: { type: String, default: 'form', validator: (v) => ['form', 'chiudi', 'nessuno'].includes(v) },
  // Passati tali e quali a FormFooter (footer 'form').
  loading: { type: Boolean, default: false },
  saveDisabled: { type: Boolean, default: false },
  saveLabel: { type: String, default: null },
  saveSeverity: { type: String, default: null },
  cancelLabel: { type: String, default: null },
  // Override del readonly del SOLO footer 'form' (`readonly` di FormFooter):
  // `undefined` = eredita la catena. Per l'eccezione di dominio salvabile in un
  // contesto in sola lettura (riferimenti dell'atto di un contratto ATTIVO).
  footerReadonly: { type: Boolean, default: undefined },
})

const emit = defineEmits(['update:visible', 'save', 'cancel', 'after-show'])

// La catena readonly, eventualmente stretta dal chiamante. ⚠️ OR con il
// padre, mai sostituzione: e' la convenzione di `READONLY_KEY`.
const readonlyPadre = inject(READONLY_KEY, ref(false))
const isReadonly = computed(() => props.readonly || readonlyPadre.value)
provide(READONLY_KEY, isReadonly)

const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
// ⭐ `after-show` esce anche verso il chiamante: chi ha logica che deve
//    aspettare la fine dell'animazione (l'auto-salvataggio della bozza dei
//    documenti, `useDrawerAutosaveBozza`) ascolta questo, non PrimeVue.
function suAfterShow() {
  onAfterShow()
  emit('after-show')
}

// Scopo: l'uscita, unica. `cancel` resta per chi deve sapere che si e' usciti
//        senza salvare (reset, notifiche al padre).
function chiudi() {
  props.confermaUscita(() => {
    emit('cancel')
    emit('update:visible', false)
  })
}
const suVisibile = gestoreVisibile(emit, chiudi)
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width }"
    :dismissable="dismissable"
    @update:visible="suVisibile"
    @after-show="suAfterShow"
  >
    <template #header>
      <DrawerTitle
        :title="title"
        :icon="icon"
        :action="action"
        :modificato="modificato"
        :conteggio="conteggio"
        :conteggio-tooltip="conteggioTooltip"
      />
    </template>

    <div
      v-if="contentReady"
      class="app-drawer-content"
      :class="{ 'app-readonly': proteggiCorpo && isReadonly }"
    >
      <slot />
    </div>

    <!-- ⛔ Il footer nasce col contenuto (`contentReady`), non prima: Salva e
         Ctrl+S attivi durante lo slide salverebbero il form del record
         aperto PRIMA, che il drawer non ha ancora sostituito (difetto trovato
         il 2026-10-03: prima della sede il FormFooter stava nel corpo, dentro
         lo stesso `v-if`). Il cancello sui DATI resta del chiamante
         (`save-disabled`, o `footer` secondo lo stato). -->
    <template v-if="contentReady && ($slots.footer || footer !== 'nessuno')" #footer>
      <slot name="footer" :chiudi="chiudi">
        <!-- `#footer-azioni`: pulsanti IN PIU' a sinistra del footer standard
             (il «Ripristina» delle personalizzazioni), che resta del guscio
             con la sua uscita. -->
        <div :class="{ 'app-drawer-footer-azioni': $slots['footer-azioni'] }">
          <slot name="footer-azioni" />
          <FormFooter
            v-if="footer === 'form'"
            :save-label="saveLabel"
            :save-severity="saveSeverity"
            :cancel-label="cancelLabel"
            :loading="loading"
            :disabled="saveDisabled"
            :readonly="footerReadonly"
            @cancel="chiudi"
            @save="emit('save')"
          />
          <FormFooter v-else close-only @cancel="chiudi" />
        </div>
      </slot>
    </template>
  </Drawer>
</template>
