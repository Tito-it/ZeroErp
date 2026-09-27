<script setup>
// Scopo: Placeholder riutilizzabile per liste che partono vuote.
// Mostra icona search e messaggio "Eseguire una ricerca" finche' l'utente non applica filtri.
import { useI18n } from 'vue-i18n'
import { MANAGE_ICONS } from '../constants'

defineProps({
  message: { type: String, default: null }
})

const { t } = useI18n()
</script>

<template>
  <div class="search-hint">
    <i class="search-hint-icon" :class="MANAGE_ICONS.RICERCA" />
    <span>{{ message || t('common.eseguire_ricerca') }}</span>
  </div>
</template>

<style scoped>
.search-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  height: 100%;
  color: var(--app-text-muted);
  font-size: 0.95rem;
}

.search-hint-icon {
  font-size: 2rem;
  opacity: 0.4;
}
</style>
