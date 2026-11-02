<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Scopo: Banner inline (building block #4, refactor-prezzi 2026-06-01) per le
         violazioni L2 del pricing (sconto/maggiorazione eccessivi). Mostrato
         da preventivi, contratti e offerte al posto del toast standard, con
         CTA "richiedi approvazione" (workflow L3). Presentazionale puro: non
         rende nulla se `error` e' falsy; gli handler restano caller-side.
         Il prefisso i18n e' fuori dal componente: il caller passa le label
         gia' risolte (`label`/`labelLoading`/`tooltip`).
-->
<script setup>
import { computed } from 'vue'
import Message from 'primevue/message'
import Button from 'primevue/button'
import vTooltip from 'primevue/tooltip'
import { MANAGE_ICONS } from '../../../core/constants'

const props = defineProps({
  // Oggetto { code, message, detail } prodotto da `classifyL2Error`. Falsy → nessun render.
  error: { type: Object, default: null },
  // Stato submit: pilota `:loading` del bottone e lo swap label.
  loading: { type: Boolean, default: false },
  label: { type: String, required: true },
  labelLoading: { type: String, required: true },
  tooltip: { type: String, default: '' },
})

defineEmits(['richiedi'])

const ctaLabel = computed(() => (props.loading ? props.labelLoading : props.label))
</script>

<template>
  <Message v-if="error" severity="warn" :closable="false">
    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
      <strong>{{ error.message }}</strong>
      <small v-if="error.detail">{{ error.detail }}</small>
      <div>
        <Button
          :label="ctaLabel"
          :icon="MANAGE_ICONS.RICHIEDI_APPROVAZIONE"
          size="small"
          severity="secondary"
          :loading="loading"
          v-tooltip.bottom="tooltip"
          @click="$emit('richiedi')"
        />
      </div>
    </div>
  </Message>
</template>
