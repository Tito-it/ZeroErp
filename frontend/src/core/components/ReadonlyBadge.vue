<script setup>
// Scopo: badge "Modalita' consultazione" per segnalare livello LETTURA.
// Riusabile in toolbar lista + header drawer. Auto-hide via inject:
// - visibile se isReadonly && !isBlocked (LETTURA puro)
// - nascosto se bloccato (il pannello lo rimpiazza gia') o se normale
// Responsive: mobile solo icona con tooltip, desktop icona + testo.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly, useInjectBlocked } from '../composables/useReadonlyMode'
import { STATUS_ICONS } from '../constants'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const isBlocked = useInjectBlocked()

const isVisible = computed(() => isReadonly.value && !isBlocked.value)
</script>

<template>
  <span
    v-if="isVisible"
    class="app-readonly-badge"
    v-tooltip.bottom="t('common.modalita_consultazione')"
    role="status"
  >
    <i class="app-readonly-badge__icon" :class="STATUS_ICONS.SOLA_LETTURA" />
    <span class="app-readonly-badge__text">{{ t('common.modalita_consultazione') }}</span>
  </span>
</template>

<style scoped>
.app-readonly-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--app-text-muted, #6c757d);
  background: color-mix(in srgb, var(--app-text-muted, #6c757d) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--app-text-muted, #6c757d) 30%, transparent);
  user-select: none;
  white-space: nowrap;
  line-height: 1;
}

.app-readonly-badge__icon {
  font-size: 0.8rem;
}

/* Mobile: solo icona, testo nascosto (il tooltip resta) */
@media (max-width: 767.98px) {
  .app-readonly-badge__text {
    display: none;
  }
  .app-readonly-badge {
    padding: 0.25rem 0.4rem;
  }
}
</style>
