<script setup>
// Scopo: footer standard per drawer con pulsanti Annulla/Salva.
// Riusabile in tutti i drawer del progetto.
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'

defineProps({
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  saveLabel: { type: String, default: null },
  cancelLabel: { type: String, default: null }
})

const emit = defineEmits(['save', 'cancel'])
const { t } = useI18n()
</script>

<template>
  <div class="app-drawer-footer">
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
