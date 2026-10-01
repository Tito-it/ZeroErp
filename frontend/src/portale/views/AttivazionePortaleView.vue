<script setup>
// Scopo: Pagina pubblica di attivazione della veste portale cliente/fornitore (/attivazione-portale/:token).
// E' il building block AttivazioneVestePage sulla porta PORTALE: forma
// (password o un clic), verifica e conferma sono le stesse di ogni veste.
import AttivazioneVestePage from '../../core/components/AttivazioneVestePage.vue'
import { PORTE_ATTIVAZIONE } from '../../core/api/attivazioneVeste'
</script>

<template>
  <AttivazioneVestePage :porta="PORTE_ATTIVAZIONE.PORTALE" />
</template>
