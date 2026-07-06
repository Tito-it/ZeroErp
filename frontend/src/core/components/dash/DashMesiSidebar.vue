<script setup>
// Scopo: Pannello laterale anno + 12 mesi dei cruscotti fatturazione (BB
//        condiviso dashboard 5-card / Lente Competenza, estratto 2026-07-06
//        regola del 2, ok Tid). La semantica del semaforo/badge per mese
//        resta del caller (slot scoped #badge con l'indice del mese).
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'

defineProps({
  anno: { type: Number, required: true },
  // Array mesi dello store (serve la chiave stabile competenza_mese).
  mesi: { type: Array, required: true },
  meseIdx: { type: Number, required: true },
  nomiMesi: { type: Array, required: true },
})

const emit = defineEmits(['seleziona-mese', 'cambia-anno'])

const { t } = useI18n()
</script>

<template>
  <aside class="app-dash-mesi">
    <div class="app-dash-anno">
      <Button
        icon="pi pi-chevron-left"
        text
        rounded
        size="small"
        :aria-label="t('dash_mesi.anno_precedente')"
        v-tooltip.bottom="t('dash_mesi.anno_precedente')"
        @click="emit('cambia-anno', -1)"
      />
      <span>{{ anno }}</span>
      <Button
        icon="pi pi-chevron-right"
        text
        rounded
        size="small"
        :aria-label="t('dash_mesi.anno_successivo')"
        v-tooltip.bottom="t('dash_mesi.anno_successivo')"
        @click="emit('cambia-anno', 1)"
      />
    </div>
    <button
      v-for="(mese, idx) in mesi"
      :key="mese.competenza_mese"
      type="button"
      class="app-dash-mese-btn"
      :class="{ 'is-active': idx === meseIdx }"
      @click="emit('seleziona-mese', idx)"
    >
      <span class="app-dash-mese-nome">{{ nomiMesi[idx] }}</span>
      <slot name="badge" :idx="idx" />
    </button>
  </aside>
</template>
