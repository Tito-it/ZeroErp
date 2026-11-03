<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il dialog «Informazioni»: logo, licenza in due righe, i link al
//        codice sorgente e al testo della licenza, il copyright. E' l'offerta
//        del sorgente a chi usa l'app (AGPL-3.0 §13): un operatore legge
//        «software libero», e il repository lo apre solo se gli interessa
//        (decisione di Tid, 2026-11-02). Lo aprono `LinkInformazioni` (pagine
//        di accesso) e la voce «Informazioni» del kebab utente (`AppTopbar`).
// ⛔ Il link al sorgente non si toglie: senza, il dialog non e' piu' l'offerta
//    che la licenza chiede.
import { useI18n } from 'vue-i18n'
import AppDialog from './AppDialog.vue'
import LogoBrand from './LogoBrand.vue'
import { CODICE_SORGENTE_URL, COPYRIGHT, LICENZA_SPDX, LICENZA_URL } from '../codiceSorgente'
import { MANAGE_ICONS } from '../constants'

defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible'])

const { t } = useI18n()
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="t('informazioni.titolo')"
    width="sm"
    close-only
    @update:visible="emit('update:visible', $event)"
  >
    <div class="informazioni">
      <LogoBrand size="large" />
      <p>{{ t('informazioni.licenza', { spdx: LICENZA_SPDX }) }}</p>
      <p>{{ t('informazioni.diritti') }}</p>
      <div class="informazioni-link">
        <a :href="CODICE_SORGENTE_URL" target="_blank" rel="noopener noreferrer">
          <i :class="MANAGE_ICONS.CODICE_SORGENTE" aria-hidden="true" />
          {{ t('informazioni.codice_sorgente') }}
        </a>
        <a :href="LICENZA_URL" target="_blank" rel="noopener noreferrer">
          <i :class="MANAGE_ICONS.TESTO_LICENZA" aria-hidden="true" />
          {{ t('informazioni.testo_licenza') }}
        </a>
      </div>
      <p class="informazioni-copyright">{{ COPYRIGHT }}</p>
    </div>
  </AppDialog>
</template>

<style scoped>
.informazioni {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  text-align: center;
}

.informazioni p {
  margin: 0;
}

.informazioni-link {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 1.5rem;
}

.informazioni-link a {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--app-accent-color);
}

.informazioni-copyright {
  font-size: var(--app-font-size-sm);
  color: var(--app-text-muted);
}
</style>
