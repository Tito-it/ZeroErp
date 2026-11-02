<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Il contenitore della cella AZIONI di `ListaConfigurabile`: fornisce
//        ai discendenti la decisione «azioni a kebab» del packing responsive
//        (`useAzioniRigaCompatte`), cosi' `RowActionsMenu` la legge da se' e il
//        caller non deve girare lo scope `compact` a mano.
// ⚠️ Esiste solo perche' `provide` vuole un componente: una cella di
//    `<Column>` non ne ha uno suo. Non rende niente oltre lo slot.
import { toRef } from 'vue'
import { provideAzioniRigaCompatte } from '../composables/useAzioniRigaCompatte'

const props = defineProps({
  compact: { type: Boolean, default: false },
})

provideAzioniRigaCompatte(toRef(props, 'compact'))
</script>

<template>
  <slot />
</template>
