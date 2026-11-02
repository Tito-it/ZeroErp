<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: monta il drawer aperto da un'AZIONE DI RIGA contribuita
//        (`useAzioniEstese`). Il drawer appartiene al dominio che l'ha
//        contribuito: qui non si sa quale sia.
// ------------------------------------------------------------
// Uso: <EstensioneDrawerHost :stato="aperto" @update:visible="impostaVisibile" />
const props = defineProps({
  // Lo stato di `useAzioniEstese().aperto`: { componente, props, visible }.
  stato: { type: Object, default: null },
})
const emit = defineEmits(['update:visible'])
</script>

<template>
  <component
    :is="props.stato.componente"
    v-if="props.stato"
    v-bind="props.stato.props"
    :visible="props.stato.visible"
    @update:visible="v => emit('update:visible', v)"
  />
</template>
