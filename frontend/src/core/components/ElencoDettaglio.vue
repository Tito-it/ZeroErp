<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: ELENCO A SINISTRA, DETTAGLIO A DESTRA — un catalogo corto di
//        voci-contenitore (es. le aree funzionali) e il contenuto della voce
//        scelta. Il markup delle classi `app-elenco-dettaglio-*` (main.css).
//
// ⭐ PERCHE' ESISTE (2026-10-31, regola del 2, ok Tid). Le classi CSS erano
//    condivise dal 2026-10-04, ma il markup intorno — la voce attiva, il segno
//    «modificata», la ricaduta sulla prima voce a vista, lo stato vuoto — era
//    scritto dentro `OperatorePermessiTab`. Il profilo di un reparto, rifatto
//    per area come il pannello dell'operatore, ne sarebbe stato la copia.
//
// ⛔ IL BB NON CONOSCE IL DOMINIO. Sa che ci sono delle VOCI con una chiave e
//    un'etichetta, che una e' scelta e che alcune hanno modifiche non salvate.
//    I segni di riga (livello, conteggi, avvisi), i filtri e il dettaglio li
//    disegna il chiamante negli slot.
//
// ⭐ LA VOCE MOSTRATA e' quella scelta se ancora a vista, altrimenti la PRIMA a
//    vista: un filtro che nasconde la voce scelta non lascia il dettaglio vuoto
//    ne' fermo su una voce che non si vede piu'. La scelta (`v-model`) resta
//    del chiamante, che la azzera dove vuole (apertura, cambio d'entita').
//
// Slot:
//   #filtri               → sopra il layout (ricerca, interruttori); senza
//                           lo slot la riga dei filtri non c'e'
//   #segni="{ voce }"     → dopo l'etichetta, nella voce dell'elenco
//   #dettaglio="{ voce }" → il contenuto della voce mostrata
import { computed, useSlots } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const slots = useSlots()

const props = defineProps({
  // Le voci A VISTA (gia' filtrate dal chiamante), nell'ordine dell'elenco.
  voci: { type: Array, required: true },
  // `voce -> chiave stabile`. Nessun default `id`: un default indovinato
  // farebbe collidere in silenzio due cataloghi con chiavi diverse.
  chiave: { type: Function, required: true },
  // `voce -> testo` della voce nell'elenco.
  etichetta: { type: Function, required: true },
  // `voce -> bool`: la voce ha modifiche non salvate (testo arancio + tooltip).
  modificata: { type: Function, default: () => false },
  // La chiave della voce scelta (`v-model`). `null` = la prima a vista.
  modelValue: { type: [Number, String], default: null },
  // Il testo quando nessuna voce e' a vista.
  testoVuoto: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const voceCorrente = computed(() =>
  props.voci.find(v => props.chiave(v) === props.modelValue) ?? props.voci[0] ?? null
)
const attiva = (voce) => voceCorrente.value != null
  && props.chiave(voceCorrente.value) === props.chiave(voce)
</script>

<template>
  <div>
    <div v-if="slots.filtri" class="app-elenco-dettaglio-filtri">
      <slot name="filtri" />
    </div>

    <div class="app-elenco-dettaglio">
      <nav class="app-elenco-dettaglio-elenco">
        <button
          v-for="voce in voci"
          :key="chiave(voce)"
          type="button"
          class="app-elenco-dettaglio-voce"
          :class="{
            'app-elenco-dettaglio-voce--attiva': attiva(voce),
            'app-elenco-dettaglio-voce--modificata': modificata(voce),
          }"
          :aria-current="attiva(voce) ? 'true' : null"
          v-tooltip.right="modificata(voce) ? t('common.modifiche_non_salvate.indicatore') : null"
          @click="emit('update:modelValue', chiave(voce))"
        >
          <span class="app-elenco-dettaglio-voce-testo">{{ etichetta(voce) }}</span>
          <slot name="segni" :voce="voce" />
        </button>
        <span v-if="!voci.length" class="app-elenco-dettaglio-vuoto">
          {{ testoVuoto || t('common.no_results') }}
        </span>
      </nav>

      <section v-if="voceCorrente" class="app-elenco-dettaglio-dettaglio">
        <slot name="dettaglio" :voce="voceCorrente" />
      </section>
    </div>
  </div>
</template>
