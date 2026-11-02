<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: ⭐ IL FILTRO PER GRAVITÀ — un `SelectButton` in cui ogni voce porta il
// COLORE del suo livello, non solo il nome. «Critiche · Avvisi · Attenzioni»
// smette di essere un elenco di parole e diventa una scala che si legge di
// colpo, con la stessa scala cromatica dei `Tag :severity` che l'operatore
// vede ovunque nell'applicazione.
//
// Nato nel drawer del lotto di fatturazione (2026-08-21) ed estratto subito a
// BB per richiesta di Tid: un filtro per gravità è la forma che ricapita —
// code di lavoro, diari, cruscotti — e due copie divergerebbero sul colore,
// che qui è proprio l'informazione.
//
// ⭐ PARLA IL LINGUAGGIO DELLE SEVERITY, NON DEI CODICI DI DOMINIO. Ogni
// opzione dichiara `severity` ('danger' | 'warn' | 'info' | 'success' |
// 'secondary'), le stesse che restituiscono gli helper di
// `core/utils/severity.js`. Il chiamante traduce il proprio vocabolario
// (`C`/`W`/`I`, `CRITICO`/`ALTO`/…) una volta sola, e questo componente non
// deve sapere niente di lotti, resi o code.
//
// ⚠️ IL COLORE STA IN DUE POSTI, E LA RIDONDANZA È VOLUTA:
//   1. il PALLINO, che il colore ce l'ha sempre;
//   2. una tinta leggera sul chip SELEZIONATO, agganciata con `:has()` perché
//      l'unico appiglio per-opzione è il contenuto dello slot, che sta DENTRO
//      il bottone reso da PrimeVue.
// Su un browser senza `:has()` sparisce solo la tinta: il pallino resta, e il
// filtro non perde il suo segnale. Affidare il colore a un meccanismo solo
// avrebbe voluto dire perderlo tutto.
//
// 📌 I colori arrivano dai token `--app-severity-*` di `theme.css`, mai da
// esadecimali qui dentro (memoria feedback_css_centralizzazione). È anche il
// posto dove è scritto perché `warn` è giallo e non arancio.
import SelectButton from 'primevue/selectbutton'

defineProps({
  // Valore selezionato (v-model). Il tipo lo decide il chiamante: qui si
  // trasporta e basta.
  modelValue: { type: [String, Number, null], default: null },
  // Le voci: `{ value, label, severity }`. `severity` assente → 'secondary',
  // cioè neutro — una voce senza gravità dichiarata non deve inventarsene una.
  options: { type: Array, required: true },
  size: { type: String, default: 'small' },
  // ⚠️ Default `false`: un filtro di gravità senza selezione mostrerebbe
  // «tutto» o «niente» a seconda del chiamante, cioè un terzo stato implicito
  // che nessuno ha dichiarato. Chi lo vuole lo accende di proposito.
  allowEmpty: { type: Boolean, default: false },
})

defineEmits(['update:modelValue'])
</script>

<template>
  <SelectButton
    :model-value="modelValue"
    :options="options"
    option-label="label"
    option-value="value"
    :allow-empty="allowEmpty"
    :size="size"
    class="app-gravita-filtro"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template #option="{ option }">
      <span :class="['app-gravita', `app-gravita--${option.severity || 'secondary'}`]">
        <i class="app-gravita-pallino" />
        {{ option.label }}
      </span>
    </template>
  </SelectButton>
</template>

<style scoped>
.app-gravita {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.app-gravita-pallino {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: currentColor;
  flex: 0 0 auto;
}

.app-gravita--danger { color: var(--app-severity-danger); }
.app-gravita--warn { color: var(--app-severity-warn); }
.app-gravita--info { color: var(--app-severity-info); }
.app-gravita--success { color: var(--app-severity-success); }
.app-gravita--secondary { color: var(--app-severity-secondary); }

/* Il chip selezionato prende la tinta del suo livello. `:deep` perché il
   bottone lo rende PrimeVue fuori dal nostro scope. */
.app-gravita-filtro :deep(.p-togglebutton-checked:has(.app-gravita--danger)) {
  background: color-mix(in srgb, var(--app-severity-danger) var(--app-severity-fill), transparent);
}
.app-gravita-filtro :deep(.p-togglebutton-checked:has(.app-gravita--warn)) {
  background: color-mix(in srgb, var(--app-severity-warn) var(--app-severity-fill), transparent);
}
.app-gravita-filtro :deep(.p-togglebutton-checked:has(.app-gravita--info)) {
  background: color-mix(in srgb, var(--app-severity-info) var(--app-severity-fill), transparent);
}
.app-gravita-filtro :deep(.p-togglebutton-checked:has(.app-gravita--success)) {
  background: color-mix(in srgb, var(--app-severity-success) var(--app-severity-fill), transparent);
}
</style>
