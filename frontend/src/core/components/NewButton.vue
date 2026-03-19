<script setup>
// Scopo: pulsante "Nuovo/a" standard per tutte le toolbar lista.
// Label fisso, tooltip contestuale. Responsive: solo icona su mobile.
// In modalita' sola lettura (provide/inject) si nasconde automaticamente.
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import Button from 'primevue/button'

defineProps({
  tooltip: { type: String, default: '' }
})

const emit = defineEmits(['click'])
const { t } = useI18n()
const isReadonly = useInjectReadonly()
</script>

<template>
  <Button
    v-if="!isReadonly"
    :label="t('common.new')"
    icon="pi pi-plus"
    v-tooltip.bottom="tooltip"
    class="app-page-action"
    @click="emit('click')"
  />
</template>
