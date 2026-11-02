<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la SEZIONE DELLA MERCE di un documento nel suo drawer — da dove esce
//        (i prelievi della bolla) o dove rientra (i rientri del reso): legge la
//        situazione, compare solo se il documento muove merce, avvisa se manca
//        il magazzino, e mette in fila le voci. Il blocco della voce lo da' il
//        chiamante (slot `voce`). Regola del 2 (2026-10-13, ok Tid): era lo
//        scheletro di `DdtPrelieviSection` e `ResoRientriSection`, uguale
//        riga per riga; restano involucri sottili con lettura, testi e voce.
//
// ⭐ Il contratto della risposta e' quello dei due endpoint di situazione
//    (`…/ddt/<id>/prelievi/`, `…/resi/<id>/rientri/`): `muove_merce`,
//    `magazzino_id`, `voci: [...]`. La regola «muove merce» la decide il DB
//    (`vendite.fn_ddt_muove_merce`, `vendite.fn_reso_muove_merce`).
// ⭐ `lettura` cambia a ogni lettura ed entra nella chiave delle voci: le voci
//    rinascono e rileggono i loro lookup coi magazzini di adesso (un magazzino
//    cambiato sulla testata cambia ubicazioni e seriali proponibili).
// ⭐ Senza magazzino la sezione non lascia scrivere (`modificabile` dello slot
//    falso): lotti, seriali e scaffali dipendono da lui.
// ⚠️ La ricarica la chiede il drawer (`carica`, esposta), a ogni rilettura
//    della testata; alla prima apertura la sezione legge da se'. Un gesto
//    nella voce lo segnala il chiamante col suo `changed`: il drawer rilegge
//    la testata (la capability e il suo motivo cambiano) e con lei la sezione.
import { ref, computed } from 'vue'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import Divider from 'primevue/divider'

const props = defineProps({
  // La lettura della situazione: una funzione che ritorna la Promise axios.
  leggi: { type: Function, required: true },
  titolo: { type: String, required: true },
  intro: { type: String, default: '' },
  // La frase quando il documento muove merce ma non ha ancora un magazzino.
  senzaMagazzinoTesto: { type: String, default: '' },
  // La chiave stabile di una voce (riga, o riga + componente del kit).
  chiaveVoce: { type: Function, required: true },
  // Si scrive (bozza, permessi): il chiamante lo sa, la sezione toglie il
  // caso «senza magazzino».
  modificabile: { type: Boolean, default: false },
})
const { execute } = useApiHandler()

const situazione = ref(null)
const lettura = ref(0)

async function carica() {
  const dati = await execute(() => props.leggi())
  if (dati !== null) {
    situazione.value = dati
    lettura.value += 1
  }
}

const visibile = computed(() => situazione.value?.muove_merce === true)
const senzaMagazzino = computed(() => visibile.value && situazione.value.magazzino_id == null)

defineExpose({ carica })
carica()
</script>

<template>
  <template v-if="visibile">
    <Divider />
    <section class="app-drawer-section">
      <h4 style="margin: 0 0 0.25rem 0; font-size: 1rem;">{{ titolo }}</h4>
      <small v-if="intro" class="app-text-muted" style="display: block;">{{ intro }}</small>
      <small v-if="senzaMagazzino && senzaMagazzinoTesto" class="app-text-muted"
             style="display: block; margin-top: 0.25rem;">
        {{ senzaMagazzinoTesto }}
      </small>
      <template v-for="voce in situazione.voci" :key="`${lettura}-${chiaveVoce(voce)}`">
        <slot name="voce" :voce="voce" :situazione="situazione"
              :modificabile="modificabile && !senzaMagazzino" />
      </template>
    </section>
  </template>
</template>
