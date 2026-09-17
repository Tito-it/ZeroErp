<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: l'interruttore «mostra i nascosti» di una lista — ToggleSwitch +
//        etichetta + «(N)», dove N e' quanto l'elenco sta lasciando fuori
//        finche' l'interruttore e' spento.
//
// Estratto il 2026-09-12 alla seconda occorrenza (regola del 2, ok Tid):
// «Mostra archiviate» delle code (`CodaFiltriToolbar`) e «Mostra annullati»
// della lista Lotti erano lo stesso gesto scritto due volte, con due CSS
// scoped e due chiavi i18n plurali che dicevano la stessa cosa in due modi.
//
// ⭐ IL NUMERO NON E' DECORATIVO: spento e senza numero, «elenco pulito» e
//    «tre righe messe via» si leggono uguali. E' la stessa disciplina di
//    `ritirate_count` sul giornale della fattura e di `archiviate_count`
//    sulle code — il BE dichiara quanti ne nasconde, qui si mostra.
// ⚠️ `(N)` compare SOLO a interruttore spento: acceso, non c'e' piu' niente di
//    nascosto e un numero accanto direbbe una cosa falsa.
// ⚠️ `label` e `hint` arrivano GIA' TRADOTTI (stesso patto di `AttivoTag` e
//    `PageActionsBar`): il BB non conosce la famiglia i18n del chiamante.
//
// Uso:
//   <ToggleNascoste v-model="filtri.annullati" :label="t('...')"
//                   :hint="t('...')" :count="annullatiCount"
//                   @change="onChange" />
//   La classe sul tag si fonde sul root (`<label>`): un chiamante che vuole il
//   look dei filtri di cruscotto passa `class="app-dash-filter-toggle"`.
import ToggleSwitch from 'primevue/toggleswitch'

const modelValue = defineModel({ type: Boolean, default: false })

defineProps({
  // Testo dell'interruttore, gia' tradotto («Mostra annullati»).
  label: { type: String, required: true },
  // Tooltip sull'interruttore, gia' tradotto. Vuoto = nessun tooltip.
  hint: { type: String, default: '' },
  // Quanti elementi restano fuori dall'elenco finche' e' spento (dal BE).
  count: { type: Number, default: 0 },
})

// `change` porta il valore nuovo: chi ricarica una lista da pagina 1 non ne
// ha bisogno, chi deve distinguere acceso/spento ce l'ha senza rileggere.
defineEmits(['change'])
</script>

<template>
  <label class="app-toggle-nascoste">
    <ToggleSwitch
      v-model="modelValue"
      :aria-label="label"
      v-tooltip.bottom="hint || undefined"
      @update:model-value="$emit('change', $event)"
    />
    <span>
      {{ label }}<span
        v-if="!modelValue && count > 0"
        class="app-toggle-nascoste-count"
      > ({{ count }})</span>
    </span>
  </label>
</template>
