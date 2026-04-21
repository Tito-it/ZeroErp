<script setup>
// Scopo: Selettore canale di login riusabile (§8.5.1 multi-face auth).
// Render: radio button orizzontale con label i18n.
//
// Usato da LoginView; riusabile per future pagine "scegli veste" (es.
// account multi-face che deve scegliere quale identita attivare).
//
// Props:
//   - modelValue (v-model): key del canale corrente ('ADMIN' | 'PORTALE' | 'SHOP')
//   - channels: lista di canali da mostrare. Default = tutti e 3 in ordine.
//     Permette di nascondere canali in contesti specifici (es. solo ADMIN+PORTALE).
//   - disabled: disabilita tutti i radio (usato durante submit in corso).
// Emits:
//   - update:modelValue: nuova key del canale
//
// Pattern DRY: le label vengono dalla chiave `i18n` di ogni canale
// (centralizzata in constants.CANALE_LOGIN); il componente non conosce
// i testi, li risolve via `$t()`.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import RadioButton from 'primevue/radiobutton'
import { CANALE_LOGIN_LIST } from '../constants'

const props = defineProps({
  modelValue: { type: String, required: true },
  channels: { type: Array, default: () => CANALE_LOGIN_LIST },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const selected = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})
</script>

<template>
  <div class="channel-selector" role="radiogroup" :aria-label="t('auth.canale.label')">
    <label
      v-for="ch in channels"
      :key="ch.key"
      class="channel-selector__item"
      :class="{ 'channel-selector__item--selected': selected === ch.key }"
    >
      <RadioButton
        :model-value="selected"
        @update:model-value="selected = $event"
        :value="ch.key"
        :input-id="`channel-${ch.key}`"
        :disabled="disabled"
      />
      <span>{{ t(ch.i18n) }}</span>
    </label>
  </div>
</template>

<style scoped>
.channel-selector {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: 0.5rem;
}

.channel-selector__item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: var(--app-font-size-sm, 0.85rem);
  cursor: pointer;
  user-select: none;
}

.channel-selector__item--selected {
  font-weight: 600;
}
</style>
