<script setup>
// Scopo: Pagina pubblica di attivazione della veste operatore (/attivazione/:token).
// E' il building block AttivazioneVestePage sulla porta OPERATORE: forma
// (password o un clic), verifica e conferma sono le stesse di ogni veste.
import AttivazioneVestePage from '../components/AttivazioneVestePage.vue'
import { PORTE_ATTIVAZIONE } from '../api/attivazioneVeste'
</script>

<template>
  <AttivazioneVestePage :porta="PORTE_ATTIVAZIONE.OPERATORE" />
</template>
