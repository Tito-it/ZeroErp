<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL NUMERO SU UN PULSANTE D'AZIONE (2026-10-04, regola del 2, ok Tid).
//        Il pallino col conteggio sopra l'icona — «Gestisci righe» con 5
//        righe, «Personalizza colonne» con 8 colonne nuove — e la sua variante
//        PUNTO per il kebab compatto, che dice «qui dentro c'e' un numero»
//        senza sommarne di eterogenei (il numero esatto resta nella voce del
//        menu, «Gestisci righe (5)», da `useActionBar`).
//        Era scritto in `DrawerActionsBar`; la barra delle liste
//        (`PageActionsBar`) non ce l'aveva, e «Personalizza colonne» metteva
//        il numero nell'etichetta di un pulsante a sola icona: non si vedeva.
//
// ⚠️ Va dentro un involucro POSIZIONATO (`.app-action-tooltip-wrap`, che e'
//    `position: relative`): il pallino e' assoluto rispetto a lui.
//
// Uso:
//   <span class="app-action-tooltip-wrap">
//     <Button … />
//     <ActionBadge :valore="a.badge" />
//   </span>
//   <ActionBadge punto :valore="haBadge ? 1 : null" />   (kebab compatto)
import { haBadge } from '../composables/useActionBar'

defineProps({
  // Il numero (o il testo breve). Vuoto (null, undefined, '') = niente pallino.
  valore: { type: [Number, String, null], default: null },
  // Solo il punto, senza numero.
  punto: { type: Boolean, default: false },
})
</script>

<template>
  <span
    v-if="haBadge({ badge: valore })"
    class="app-action-badge"
    :class="{ 'app-action-badge--punto': punto }"
    aria-hidden="true"
  >{{ punto ? '' : valore }}</span>
</template>
