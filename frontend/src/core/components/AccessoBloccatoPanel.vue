<script setup>
// Scopo: pannello sostitutivo per liste/schermate con livello oggetto BLOCCATO.
// Usato al posto di toolbar + datatable quando useInjectBlocked() e' true.
// Variante A del pattern permessi v2: nessun controllo visibile, solo messaggio
// esplicito. L'utente capisce subito che non puo' operare qui.
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div class="app-blocked-panel">
    <i class="pi pi-lock app-blocked-panel__icon" />
    <h3 class="app-blocked-panel__title">
      {{ t('common.accesso_negato_elenco') }}
    </h3>
    <p class="app-blocked-panel__hint">
      {{ t('common.accesso_negato_hint') }}
    </p>
  </div>
</template>

<style scoped>
.app-blocked-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1.5rem;
  min-height: 320px;
  text-align: center;
  color: var(--app-text-muted, #6c757d);
}

.app-blocked-panel__icon {
  font-size: 3.5rem;
  margin-bottom: 1rem;
  color: var(--app-text-muted, #6c757d);
  opacity: 0.65;
}

.app-blocked-panel__title {
  font-size: 1.15rem;
  font-weight: 500;
  margin: 0 0 0.5rem 0;
  color: var(--app-text-primary, inherit);
}

.app-blocked-panel__hint {
  font-size: 0.95rem;
  margin: 0;
  max-width: 440px;
}
</style>
