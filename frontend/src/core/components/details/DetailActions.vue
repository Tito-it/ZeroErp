<script setup>
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'

const { t } = useI18n()

defineProps({
  row: { type: Object, required: true }
})

const emit = defineEmits(['set-context', 'open-detail'])
</script>

<template>
  <div class="detail-actions">
    <Button
      :label="t('search.set_context')"
      icon="pi pi-check"
      size="small"
      @click="emit('set-context', row)"
    />
    <Button
      :label="t('search.open_detail')"
      icon="pi pi-external-link"
      size="small"
      severity="secondary"
      text
      @click="emit('open-detail', row)"
    />
  </div>
</template>

<style scoped>
.detail-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  padding-top: 0.5rem;
}
</style>
