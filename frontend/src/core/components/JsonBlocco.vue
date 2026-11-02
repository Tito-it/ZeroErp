<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: BB «blocco JSON» — un valore jsonb reso leggibile in un <pre>:
//        pretty-print a due spazi, scroll interno, bordo rosso quando e' un
//        errore. Presentazionale e basta: non sa cosa contiene.
//
// ⭐ ESTRATTO IL 2026-09-19 (regola del 2, ok Tid). La prima occorrenza e'
//    `strumenti/JobDettaglioDrawer` (payload, esito, ultimo errore di un job
//    della coda lavori); la seconda e' il `context` di `dbops.error_log` nel
//    dettaglio della consultazione tecnica (pezzo E dell'osservabilita').
//    Stessa forma: `pretty()` + `<pre>` con lo stesso stile, e la variante
//    «errore» col bordo rosso.
//
// ⚠️ Il valore NON si riscrive ne' si ripulisce: sono gli appunti di chi ha
//    sollevato l'errore o eseguito il job, e devono restare com'erano
//    (vincolo del Passo A dell'osservabilita'). Se non e' serializzabile si
//    mostra `String(value)`, non niente.
import { computed } from 'vue'

const props = defineProps({
  value: { type: [Object, Array, String, Number, Boolean], default: null },
  // Bordo rosso: il blocco racconta un errore.
  errore: { type: Boolean, default: false },
})

// Scopo: pretty-print del valore; `null` quando non c'e' niente da mostrare.
const testo = computed(() => {
  if (props.value == null) return null
  try {
    return JSON.stringify(props.value, null, 2)
  } catch {
    return String(props.value)
  }
})
</script>

<template>
  <pre v-if="testo !== null" class="app-json-blocco" :class="{ 'app-json-blocco--errore': errore }">{{ testo }}</pre>
</template>

<style scoped>
.app-json-blocco {
  margin: 0;
  padding: 0.5rem;
  background: var(--app-card-bg);
  border: 1px solid var(--app-card-border);
  border-radius: 6px;
  font-size: 0.8em;
  overflow-x: auto;
  max-height: 240px;
}
.app-json-blocco--errore {
  /* Il token di gravita' dell'app, non `--p-red-500` diretto (standard: i
     componenti usano solo `--app-*`; il rosso di PrimeVue lo sceglie theme.css). */
  border-color: var(--app-severity-danger);
}
</style>
