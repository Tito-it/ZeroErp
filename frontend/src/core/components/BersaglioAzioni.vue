<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: ⭐ I PULSANTI DEL BERSAGLIO — «Apri Fattura 835» — a partire dai
// bersagli grezzi di una riga. Niente altro: nessuna fetch, nessuno stato.
//
// ⭐ PERCHE' ESISTE (estratto alla 2a copia, regola del 2). Le superfici che
// mostrano un errore PERSISTITO sono due e cresceranno: l'icona di riga dei
// documenti (`ErroreRigaInfo`) e la scheda Segnalazioni del lotto. Facevano —
// o stavano per fare — la stessa cosa: normalizzare, risolvere coi permessi,
// rendere un `v-for` di pulsanti. Tre righe ciascuna, e la terza copia sarebbe
// arrivata con la prossima lista.
//
// ⛔ IL TOAST NON PASSA DI QUI, e non e' una dimenticanza. Quello riceve azioni
// GIA' COMPOSTE (`message.azioni`) perche' vive dentro il template di PrimeVue
// col suo `closeCallback`: fargli condividere questo componente vorrebbe dire
// portare i18n e store dentro un template di toast. Il pezzo condiviso vero e'
// piu' in basso — `azioniDaBersagli`, che usano entrambi.
//
// ⛔ E LA NORMALIZZAZIONE LA FA IL COMPONENTE, non il chiamante: e' un bug gia'
// commesso una volta. Il payload parla inglese (`{type, id}`), il resolver
// legge `tipo` — passare l'array grezzo non risolve niente e **il pulsante non
// compare mai**, senza errori e senza avvisi. Facendola qui, nessuna lista che
// monti questo componente puo' sbagliarla.
import { computed } from 'vue'
import Button from 'primevue/button'
import { useAuthStore } from '../../stores/auth'
import { normalizzaBersagli } from '../bersagli'
import { azioniDaBersagli } from '../bersaglioGesto'

const props = defineProps({
  // I bersagli come arrivano dal payload: `[{type, id}]`, oppure `null`.
  // ⚠️ `null` e' il caso NORMALE — la maggioranza degli errori non ha una
  // destinazione — e non e' un difetto: il messaggio si mostra lo stesso e
  // qui non compare niente. E' il patto «offerta, non promessa» (§4.3).
  bersagli: { type: [Array, null], default: null },
  size: { type: String, default: 'small' },
})

// Scopo: notifica al contenitore che il gesto e' stato eseguito, cosi' chi
//        vive in un pannello a scomparsa (un popover) puo' chiudersi:
//        resterebbe aperto davanti alla cosa che ha appena aperto.
const emit = defineEmits(['eseguita'])

const auth = useAuthStore()

// ⚠️ `computed` e non un calcolo nel template: la risoluzione legge i permessi,
// e su una tabella di righe ripeterla a ogni render sarebbe lavoro sprecato.
const azioni = computed(() =>
  azioniDaBersagli(normalizzaBersagli(props.bersagli), auth),
)

// Scopo: esegue il gesto e avvisa il contenitore. ⚠️ `finally`: se l'azione
//        sollevasse, chi deve chiudersi si chiude comunque.
function esegui(azione) {
  try {
    azione.esegui()
  } finally {
    emit('eseguita')
  }
}
</script>

<template>
  <!-- `wrap`: i bersagli possono essere fino a cinque, e una cella e' stretta. -->
  <div v-if="azioni.length" class="app-bersaglio-azioni">
    <Button
      v-for="(azione, i) in azioni"
      :key="i"
      :label="azione.label"
      :icon="azione.icon"
      :size="size"
      severity="secondary"
      outlined
      @click="esegui(azione)"
    />
  </div>
</template>

<style scoped>
.app-bersaglio-azioni {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>
