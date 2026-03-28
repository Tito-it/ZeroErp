<script setup>
// Scopo: footer standard per drawer con pulsanti Annulla/Salva.
// Riusabile in tutti i drawer del progetto.
// Auto-hide: si nasconde in modalita' sola lettura (inject) o se l'azione non e' abilitata.
// Prop action opzionale: se presente, nasconde i pulsanti di scrittura (Salva).
// Il pulsante Annulla resta sempre visibile (chiusura drawer).
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
  action: { type: String, default: null }
})

const emit = defineEmits(['save', 'cancel'])
const { t } = useI18n()
const isReadonly = useInjectReadonly()
const auth = useAuthStore()

const isVisible = computed(() => {
  if (isReadonly.value) return false
  if (props.action && !auth.isActionAllowed(props.action)) return false
  return true
})

// Ctrl+S → salva (funziona anche dentro input/textarea)
function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    if (isVisible.value && !props.disabled && !props.loading) {
      emit('save')
    }
  }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div v-if="isVisible" class="app-drawer-footer">
    <Button
      :label="cancelLabel || t('common.cancel')"
      severity="secondary"
      @click="emit('cancel')"
    />
    <Button
      :label="saveLabel || t('common.save')"
      :loading="loading"
      :disabled="disabled"
      @click="emit('save')"
    />
  </div>
</template>
