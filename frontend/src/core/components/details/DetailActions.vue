<script setup>
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { MANAGE_ICONS } from '../../constants'

const { t } = useI18n()

const props = defineProps({
  row: { type: Object, required: true },
  detailRow: { type: Object, default: null }
})

const emit = defineEmits(['set-context', 'open-detail'])

// Scopo: costruisce il payload unendo riga padre (soggetto) e riga dettaglio (entita' specifica)
function buildPayload() {
  return { ...props.row, ...props.detailRow }
}
</script>

<template>
  <div class="detail-actions-inline">
    <Button
      :icon="MANAGE_ICONS.IMPOSTA_CONTESTO"
      size="small"
      rounded
      v-tooltip.top="t('search.set_context_hint')"
      @click="emit('set-context', buildPayload())"
    />
    <Button
      :icon="MANAGE_ICONS.VAI_A"
      size="small"
      rounded
      severity="secondary"
      text
      v-tooltip.top="t('search.open_detail_short')"
      @click="emit('open-detail', buildPayload())"
    />
  </div>
</template>

<style scoped>
.detail-actions-inline {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  align-items: center;
}
</style>
