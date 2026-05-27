<script setup>
// Scopo: Placeholder riutilizzabile per liste che partono vuote.
// Mostra icona search e messaggio "Eseguire una ricerca" finche' l'utente non applica filtri.
import { useI18n } from 'vue-i18n'

defineProps({
  message: { type: String, default: null }
})

const { t } = useI18n()
</script>

<template>
  <div class="search-hint">
    <i class="pi pi-search" />
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
  color: var(--text-color-secondary);
  font-size: 0.95rem;
}

.search-hint .pi-search {
  font-size: 2rem;
  opacity: 0.4;
}
</style>
