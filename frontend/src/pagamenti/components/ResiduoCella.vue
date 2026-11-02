<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA CELLA DEL RESIDUO di una rata in una lista — il numero, oppure
//        cosa quel numero SIGNIFICA quando dirlo come numero mentirebbe.
//
// Estratto il 2026-09-18 (regola del 2, ok Tid): la stessa cella —
// `Tag warn` con `residuoNegativo` sotto zero, `formatCurrency` altrimenti —
// stava nel picker delle rate e nella lista delle rate fuori capienza; il
// picker aveva in piu' il ramo «esaurita». Due copie della stessa regola di
// lettura divergono alla prima sfumatura nuova, e su una lista di denaro la
// divergenza si vede solo su una delle due schermate.
//
// ⛔ Il residuo NEGATIVO non si mostra come numero negativo: «-120,00» si legge
//    come un guasto anche quando racconta correttamente il mondo. Si dice cosa
//    significa, e a deciderlo e' la NATURA del documento (una sede:
//    `useEtichettePagamenti().residuoNegativo`): «di troppo» sulla fattura,
//    «da rimborsare» sulla nota di credito — il segno e' lo stesso, cambia cosa
//    vuol dire.
//
// ⭐ `nota` e' il terzo stato, e resta del CHIAMANTE: il picker sa che una rata
//    con spazio zero e' «esaurita» (predicato `rataEsaurita` + la sua chiave),
//    la lista fuori capienza non ha niente da aggiungere. La cella rende la
//    nota come Tag neutro quando il residuo non e' negativo; il predicato e la
//    frase non entrano qui — sarebbero la regola del picker scritta in un
//    componente che il picker non e'.
//
// ⚠️ Vive nel dominio: entrambi i consumatori sono degli incassi. Passa in
//    `core/` se ne nascera' uno in `vendite`, come `RataSelect`.
import { computed } from 'vue'
import Tag from 'primevue/tag'

import { formatCurrency } from '../../core/utils/format'
import { useEtichettePagamenti } from '../etichette'

const props = defineProps({
  // Il residuo della rata (stringa decimale dal backend o numero).
  residuo: { type: [String, Number, null], default: null },
  // `natura_doc_codice_interno` del documento: decide la frase del negativo.
  naturaCodice: { type: [String, null], default: null },
  // Una frase del chiamante da rendere al posto del numero, quando il residuo
  // NON e' negativo (es. «esaurita»). `null` = il numero.
  nota: { type: [String, null], default: null },
})

const { residuoNegativo } = useEtichettePagamenti()

// `null` non e' zero: senza residuo non c'e' niente da dire, ne' come numero
// ne' come frase.
const negativo = computed(() => props.residuo != null && Number(props.residuo) < 0)
</script>

<template>
  <Tag
    v-if="negativo"
    :value="residuoNegativo(residuo, naturaCodice)"
    severity="warn"
  />
  <Tag v-else-if="nota" :value="nota" severity="secondary" />
  <span v-else>{{ formatCurrency(residuo) }}</span>
</template>
