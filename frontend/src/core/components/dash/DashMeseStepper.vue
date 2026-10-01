<script setup>
// Scopo: Stepper compatto anno/mese dei cruscotti fatturazione — visibile
//        SOLO su piccoli schermi (CSS .app-dash-stepper), sostituisce il
//        pannello 12 mesi. BB condiviso dashboard 5-card / Lente Competenza
//        (estratto 2026-07-06, regola del 2, ok Tid). Il badge del mese
//        corrente resta del caller (slot #badge).
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { MANAGE_ICONS } from '../../constants'

defineProps({
  anno: { type: Number, required: true },
  meseIdx: { type: Number, required: true },
  nomiMesi: { type: Array, required: true },
})

const emit = defineEmits(['step'])

const { t } = useI18n()
</script>

<template>
  <div class="app-dash-stepper">
    <Button
      :icon="MANAGE_ICONS.PRECEDENTE"
      text
      rounded
      size="small"
      :aria-label="t('dash_mesi.mese_precedente')"
      @click="emit('step', -1)"
    />
    <span class="app-dash-stepper-label">
      {{ nomiMesi[meseIdx] }} {{ anno }}
      <slot name="badge" />
    </span>
    <Button
      :icon="MANAGE_ICONS.SUCCESSIVO"
      text
      rounded
      size="small"
      :aria-label="t('dash_mesi.mese_successivo')"
      @click="emit('step', 1)"
    />
  </div>
</template>
