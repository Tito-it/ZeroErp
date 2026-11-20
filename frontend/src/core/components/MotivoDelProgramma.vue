<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL MOTIVO sotto un campo spento perche' lo stabilisce il programma:
//        la riga e' nata dal seed di primo impianto, e il campo e' fra i suoi
//        `campi_del_software` (BB `campoDelSoftware`).
//
// Estratto il 2026-11-20 (regola del 2, ok Tid): lo stesso
//   <small v-if="delProgramma('x')" class="app-text-muted"
//          data-testid="motivo-x">{{ t('...') }}</small>
// stava 47 volte in cinque drawer (account e template email, definizioni,
// colonne e preset delle liste), col testid scritto a mano accanto al nome del
// campo: in uno dei cinque i due nomi gia' divergevano.
//
// ⭐ `fermo` e' lo STESSO predicato che il drawer passa a `senzaCampiFermi`:
//    il campo che il motivo spiega e' il campo che resta fuori dal PATCH, e il
//    drawer lo scrive una volta sola (anche quando nomi del form e colonne
//    divergono, come la password dell'account email).
// ⚠️ Il testo lo sceglie il drawer: dice CHE COSA e' la riga («l'account»,
//    «il template», «la riga»), e la chiave i18n resta del suo dominio.
// ⚠️ Rende solo il motivo: lo spegnimento del campo (`:disabled`) resta sul
//    campo, perche' spesso si somma ad altro (sola lettura, tipo di colonna).
import { computed } from 'vue'

const props = defineProps({
  // Il nome del campo nel form (anche nel testid: `motivo-<campo>`).
  campo: { type: String, required: true },
  // `(campo) => boolean`: il campo lo stabilisce il programma?
  fermo: { type: Function, required: true },
  // Il testo gia' tradotto.
  testo: { type: String, required: true },
})

const visibile = computed(() => props.fermo(props.campo) === true)
</script>

<template>
  <small v-if="visibile" class="app-text-muted app-motivo-campo" :data-testid="`motivo-${campo}`">
    {{ testo }}
  </small>
</template>
