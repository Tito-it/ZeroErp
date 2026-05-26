<script setup>
// Scopo: footer standard per drawer con pulsanti Annulla/Salva o Chiudi.
// Riusabile in tutti i drawer del progetto.
// Modalita':
//  - default: Annulla + Salva (form create/edit)
//  - closeOnly: solo pulsante Chiudi (liste sub-entita')
// Auto-hide pulsante Salva: in modalita' sola lettura (inject) o se azione non abilitata.
// Il pulsante Annulla/Chiudi resta sempre visibile (chiusura drawer).
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
})

const emit = defineEmits(['save', 'cancel'])
const { t } = useI18n()
const isReadonly = useInjectReadonly()
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
  <div class="app-drawer-footer">
    <!-- Annulla: arrow-left (MANAGE_ICONS.BACK) — semantica "torna alla
         lista"; closeOnly mantiene pi-times (chiusura di lista sub-entita',
         non c'e' un form da abbandonare).
         Tooltip mantiene la label leggibile quando il CSS nasconde il testo
         sotto 1024px (pattern responsive standard, vedi main.css). -->
    <Button
      :label="cancelText"
      :icon="closeOnly ? MANAGE_ICONS.CANCEL : MANAGE_ICONS.BACK"
      severity="secondary"
      class="app-escape app-drawer-footer-btn"
      v-tooltip.top="cancelText"
      @click="emit('cancel')"
    />
    <!-- Salva: check verde (MANAGE_ICONS.CONFIRM) — segnala conferma form. -->
    <Button
      v-if="showSave"
      :label="saveLabel || t('common.save')"
      :icon="MANAGE_ICONS.CONFIRM"
      :loading="loading"
      :disabled="disabled"
      class="app-drawer-footer-btn"
      v-tooltip.top="saveLabel || t('common.save')"
      @click="emit('save')"
    />
  </div>
</template>
