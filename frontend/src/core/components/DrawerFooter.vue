<script setup>
// Scopo: footer standard per drawer con pulsanti Annulla/Salva.
// Riusabile in tutti i drawer del progetto.
// In modalita' sola lettura (provide/inject) si nasconde automaticamente.
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import Button from 'primevue/button'

defineProps({
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  saveLabel: { type: String, default: null },
  cancelLabel: { type: String, default: null }
})

const emit = defineEmits(['save', 'cancel'])
const { t } = useI18n()
const isReadonly = useInjectReadonly()
</script>

<template>
  <div v-if="!isReadonly" class="app-drawer-footer">
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
