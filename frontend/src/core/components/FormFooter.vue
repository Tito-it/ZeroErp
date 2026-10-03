<script setup>
// Scopo: footer standard "Annulla / Salva" per form, agnostico al contenitore.
// Usabile sia dentro un <Drawer> (footer slot o footer slot vuoto + render
// libero) sia dentro un <Dialog> via `#footer` slot. Mantiene icone, tooltip
// e collapse responsive (icon-only sotto 1024px) coerenti su tutto il progetto.
//
// Esempio Drawer:
//   <Drawer><FormFooter @cancel="..." @save="..." /></Drawer>
//
// Esempio Dialog (rifattorizzazione progressiva dei dialog hand-rolled):
//   <Dialog>
//     <template #footer><FormFooter :save-label="..." @cancel="..." @save="..." /></template>
//   </Dialog>
//
// Modalita':
//  - default:   Annulla (icona pi-arrow-left "torna indietro") + Salva (pi-check)
//  - closeOnly: solo pulsante Chiudi (icona pi-times) — per drawer di liste sub-entita'.
// Auto-hide pulsante Salva: in modalita' sola lettura (inject) o se action non abilitata.
// ⭐ `readonly` (2026-10-03, decisione di Tid): override ESPLICITO della catena,
//    default `undefined` = la eredita (come `AppDialog`). Serve all'eccezione di
//    dominio che resta salvabile dentro un contesto in sola lettura — i
//    riferimenti dell'atto di un contratto ATTIVO. ⛔ Chi la passa a `false`
//    risponde dei permessi: la condizione deve gia' escludere l'area in lettura.
//    Il controllo `action` resta comunque.
// Il pulsante Annulla/Chiudi resta sempre visibile (chiusura form).
import { computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import { MANAGE_ICONS } from '../constants'
import Button from 'primevue/button'

const props = defineProps({
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  saveLabel: { type: String, default: null },
  cancelLabel: { type: String, default: null },
  action: { type: String, default: null },
  // Se true, mostra solo il pulsante Chiudi (niente Salva). Per drawer lista.
  closeOnly: { type: Boolean, default: false },
  // Severity PrimeVue del pulsante di conferma (es. 'danger' per azioni
  // distruttive come cessazione/rifiuto, 'warn' per cautela). Default null =
  // primary (verde) — l'azione positiva standard. L'icona resta sempre il
  // check: a cambiare e' solo il colore, per segnalare la gravita' dell'azione.
  saveSeverity: { type: String, default: null },
  readonly: { type: Boolean, default: undefined },
})

const emit = defineEmits(['save', 'cancel'])
const { t } = useI18n()
const readonlyCatena = useInjectReadonly()
const isReadonly = computed(() => (props.readonly === undefined ? readonlyCatena.value : props.readonly))
const auth = useAuthStore()

const showSave = computed(() => {
  if (props.closeOnly) return false
  if (isReadonly.value) return false
  if (props.action && !auth.isActionAllowed(props.action)) return false
  return true
})

const cancelText = computed(() => {
  if (props.cancelLabel) return props.cancelLabel
  return props.closeOnly ? t('common.close') : t('common.cancel')
})

// Ctrl+S → salva (funziona anche dentro input/textarea)
function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    if (showSave.value && !props.disabled && !props.loading) {
      emit('save')
    }
  }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="app-form-footer">
    <!-- Annulla: arrow-left (MANAGE_ICONS.BACK) — semantica "torna alla
         lista"; closeOnly mantiene pi-times (chiusura di lista sub-entita',
         non c'e' un form da abbandonare).
         Tooltip mantiene la label leggibile quando il CSS nasconde il testo
         sotto 1024px (pattern responsive standard, vedi main.css). -->
    <Button
      :label="cancelText"
      :icon="closeOnly ? MANAGE_ICONS.CANCEL : MANAGE_ICONS.BACK"
      severity="secondary"
      class="app-escape app-form-footer-btn"
      v-tooltip.top="cancelText"
      @click="emit('cancel')"
    />
    <!-- Salva/Conferma: check (MANAGE_ICONS.CONFIRM). Colore = saveSeverity
         (default primary verde; 'danger'/'warn' per azioni gravi). -->
    <Button
      v-if="showSave"
      :label="saveLabel || t('common.save')"
      :icon="MANAGE_ICONS.CONFIRM"
      :severity="saveSeverity || undefined"
      :loading="loading"
      :disabled="disabled"
      class="app-form-footer-btn"
      v-tooltip.top="saveLabel || t('common.save')"
      @click="emit('save')"
    />
  </div>
</template>
