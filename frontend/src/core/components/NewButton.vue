<script setup>
// Scopo: pulsante "Nuovo/a" standard per tutte le toolbar lista.
// Label fisso, tooltip contestuale. Responsive: solo icona su mobile.
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'

defineProps({
  tooltip: { type: String, default: '' }
})

const emit = defineEmits(['click'])
const { t } = useI18n()
</script>

<template>
  <Button
    :label="t('common.new')"
    icon="pi pi-plus"
    v-tooltip.bottom="tooltip"
    class="app-page-action"
    @click="emit('click')"
  />
</template>
