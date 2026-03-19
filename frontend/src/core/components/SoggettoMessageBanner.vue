<script setup>
// Scopo: Banner riusabile per mostrare soggetto selezionato/associato.
// Usato in: OperatoreDrawer (crea + modifica), SoggettoResolver.
import Message from 'primevue/message'

defineProps({
  ragioneSociale: { type: String, default: '' },
  codiceFiscale: { type: String, default: null }
})
</script>

<template>
  <Message severity="success" :closable="false">
    <div class="flex align-items-center gap-2">
      <i class="pi pi-user" />
      <strong>{{ ragioneSociale }}</strong>
      <span v-if="codiceFiscale" class="text-sm text-color-secondary ml-2">
        CF: {{ codiceFiscale }}
      </span>
    </div>
  </Message>
</template>
