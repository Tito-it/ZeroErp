<script setup>
// Scopo: Empty-state "onesto" delle liste dei cruscotti (pattern
//        usePagedDashFetch.loaded): il messaggio positivo "nessun elemento"
//        SOLO dopo una fetch riuscita; prima del caricamento (o dopo un
//        errore) placeholder neutro — mai un all-clear su dati mai arrivati.
//        Estratto 2026-07-07 (regola del 2, ok Tid): blocco template
//        duplicato in DashboardBacklogView e SituazioneApertaView.
import { STATUS_ICONS } from '../constants'

defineProps({
  // true = almeno una fetch riuscita (usePagedDashFetch.loaded).
  loaded: { type: Boolean, required: true },
  // Messaggio positivo (lista davvero vuota), tradotto dal caller.
  emptyText: { type: String, required: true },
  // Placeholder neutro (dati non caricati), tradotto dal caller.
  placeholderText: { type: String, required: true },
})
</script>

<template>
  <div class="app-empty-state">
    <i :class="loaded ? STATUS_ICONS.TUTTO_OK : STATUS_ICONS.VUOTO" />
    <p>{{ loaded ? emptyText : placeholderText }}</p>
  </div>
</template>
