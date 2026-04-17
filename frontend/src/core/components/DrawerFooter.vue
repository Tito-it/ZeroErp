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
    <Button
      :label="cancelText"
      :icon="closeOnly ? 'pi pi-times' : undefined"
      severity="secondary"
      @click="emit('cancel')"
    />
    <Button
      v-if="showSave"
      :label="saveLabel || t('common.save')"
      :loading="loading"
      :disabled="disabled"
      @click="emit('save')"
    />
  </div>
</template>
