<script setup>
// Scopo: pulsante "Nuovo/a" standard per tutte le toolbar lista.
// Label fisso, tooltip contestuale. Responsive: solo icona su mobile.
// Auto-hide: si nasconde in modalita' sola lettura (inject) o se l'azione non e' abilitata.
// Prop action opzionale: se presente, controlla visibilita' via permessi azione processo.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import { MANAGE_ICONS } from '../constants'
import Button from 'primevue/button'

const props = defineProps({
  tooltip: { type: String, default: '' },
  action: { type: String, default: null }
})

const emit = defineEmits(['click'])
const { t } = useI18n()
const isReadonly = useInjectReadonly()
const auth = useAuthStore()

const isVisible = computed(() => {
  if (isReadonly.value) return false
  if (props.action && !auth.isActionAllowed(props.action)) return false
  return true
})
</script>

<template>
  <Button
    v-if="isVisible"
    :label="t('common.new')"
    :icon="MANAGE_ICONS.ADD"
    v-tooltip.bottom="tooltip"
    class="app-page-action"
    @click="emit('click')"
  />
</template>
