<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: L'INTERRUTTORE DI FILTRO di una lista — ToggleSwitch + etichetta in
//        linea, e per gli interruttori che ALLARGANO l'elenco anche «(N)»,
//        dove N e' quanto l'elenco sta lasciando fuori finche' e' spento.
//
// Nato il 2026-09-12 come `ToggleNascoste` alla seconda occorrenza del solo
// «mostra i nascosti» («Mostra archiviate» delle code, «Mostra annullati» dei
// lotti). Il 2026-09-18 (regola del 2, ok Tid) e' diventato il BB di OGNI
// interruttore di filtro: lo stesso blocco — `<div style="display:flex…">` +
// `ToggleSwitch :input-id` + `<label :for style="…">` — era scritto a mano in
// CINQUE toolbar (offerte, preventivi, pratiche, disponibilita' x2), con lo
// stile inline ricopiato e un id da inventare per non collidere fra due
// schede. Le cinque copie erano questo componente senza il conteggio.
//
// ⭐ Il root e' un `<label>`: niente `input-id`, niente `for`, e il click sul
//    testo accende l'interruttore da se'. E' la ragione per cui le copie a mano
//    avevano un id ciascuna, e questo no.
//
// ⭐ IL NUMERO NON E' DECORATIVO, dove si applica: un interruttore che rimette
//    dentro cio' che la lista nasconde (archiviate, annullati) senza il numero
//    fa leggere uguali «elenco pulito» e «tre righe messe via». E' la stessa
//    disciplina di `ritirate_count` sul giornale della fattura e di
//    `archiviate_count` sulle code — il BE dichiara quanti ne nasconde, qui si
//    mostra. Un interruttore che RESTRINGE («solo negativa», «solo interne»)
//    non ha niente da contare e non passa `count`.
// ⚠️ `(N)` compare SOLO a interruttore spento: acceso, non c'e' piu' niente di
//    nascosto e un numero accanto direbbe una cosa falsa.
// ⚠️ `label` e `hint` arrivano GIA' TRADOTTI (stesso patto di `AttivoTag` e
//    `PageActionsBar`): il BB non conosce la famiglia i18n del chiamante.
//
// Uso:
//   <FiltroToggle v-model="soloNegativa" :label="t('...')" :hint="t('...')"
//                 @change="onSoloNegativaChange" />
//   <FiltroToggle v-model="filtri.annullati" :label="t('...')"
//                 :count="annullatiCount" @change="onChange" />
//   Il legame con `store.filters` lo da' `useStoreFilterBindings.bindToggle`.
//   La classe sul tag si fonde sul root (`<label>`): un chiamante che vuole il
//   look dei filtri di cruscotto passa `class="app-dash-filter-toggle"`.
import ToggleSwitch from 'primevue/toggleswitch'

const modelValue = defineModel({ type: Boolean, default: false })

defineProps({
  // Testo dell'interruttore, gia' tradotto («Mostra annullati», «Solo negativa»).
  label: { type: String, required: true },
  // Tooltip sull'interruttore, gia' tradotto. Vuoto = nessun tooltip.
  hint: { type: String, default: '' },
  // Quanti elementi restano fuori dall'elenco finche' e' spento (dal BE).
  // Solo per gli interruttori che allargano la lista; 0 = niente da mostrare.
  count: { type: Number, default: 0 },
})

// `change` porta il valore nuovo: chi ricarica una lista da pagina 1 non ne
// ha bisogno, chi deve distinguere acceso/spento ce l'ha senza rileggere.
defineEmits(['change'])
</script>

<template>
  <label class="app-filtro-toggle">
    <ToggleSwitch
      v-model="modelValue"
      :aria-label="label"
      v-tooltip.bottom="hint || undefined"
      @update:model-value="$emit('change', $event)"
    />
    <span>
      {{ label }}<span
        v-if="!modelValue && count > 0"
        class="app-filtro-toggle-count"
      > ({{ count }})</span>
    </span>
  </label>
</template>
