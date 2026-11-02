<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL PERIODO come UN filtro — i due estremi `da`/`a` resi insieme, su
//        una riga sola, in linea su desktop e dentro il drawer dei filtri.
//
// ⭐ LA REGOLA (ok Tid, 2026-09-22): `data_da` e `data_a` **non sono due
//    filtri**, sono un filtro con due estremi. Ne discende tutto il resto —
//    che stiano su una riga sola non e' una scelta di layout («le date sono
//    strette»), e' la forma della cosa: spezzarli su due righe rompe cio' che
//    l'operatore legge come una.
//    ⛔ Prima di questo BB la coppia si riconosceva dal WIDGET — una regola CSS
//    su `.p-datepicker` dentro il drawer — cioe' da un fatto tecnico invece
//    che dal modello: bastava un terzo DatePicker non del periodo (il
//    «scadenza mese» dei contratti) per far pagare la regola a chi non
//    c'entrava.
//
// Uso (il binding in una riga, la resa in una):
//   const { bindPeriodo } = useStoreFilterBindings(store, applyFilters)
//   const periodo = bindPeriodo()                    // 'data_da' / 'data_a'
//   const periodo = bindPeriodo('data_da', 'data_a', { clearToDa: defaultFiltroDataDa })
//   …
//   <FiltroPeriodo :periodo="periodo" />
//
// ⛔ IL VERSO DEGLI EVENTI VIVE QUI, ed e' la ragione meno visibile per cui il
//    BB esiste. Nelle diciotto liste che scrivevano la coppia a mano il
//    cablaggio era divergente: `@date-select` + `@clear-click` quasi ovunque,
//    `@update:modelValue` nei contratti. Non sono equivalenti — col primo una
//    data **digitata** nella casella non applica il filtro: l'operatore vede
//    la data che ha scritto e una lista che non l'ha ricevuta, senza nessun
//    errore. Qui si usa `@update:model-value`, che copre scelta dal
//    calendario, digitazione e svuotamento.
//
// ⚠️ `periodo.da`/`periodo.a` sono REF dentro un oggetto passato per prop, e li'
//    l'auto-unwrap del template NON vale (vale solo per i ref di primo livello
//    del setup, stampo `feedback_defineexpose_unwrap`): si leggono con `.value`.
// ⛔ E NON SI SCRIVONO DA QUI, che e' come l'avevo fatto la prima volta: un
//    `v-model` su un ref che sta in una prop scrive in casa d'altri —
//    funziona, e nasconde chi possiede lo stato. Lo ha respinto il lint
//    (`vue/no-mutating-props`), e la correzione e' stata nell'API, non nella
//    regola: `bindPeriodo` espone `setDa`/`setA`, quindi qui si LEGGE il valore
//    e si CHIEDE il cambio — legame in un verso solo, proprietario uno solo.
// ⛔ NESSUN `min-date`/`max-date` INCROCIATO, e la prima stesura ce l'aveva:
//    sembra il guard ovvio («un intervallo non si inverte») ed e' una trappola
//    d'uso — con `max-date` legato all'altro estremo, spostare la finestra in
//    AVANTI diventa impossibile finche' non si tocca prima l'altra data.
//    ⭐ E l'invariante NON vive qui: `da > a` non puo' esistere (D8, Tid
//    2026-09-22) e il meccanismo — «l'estremo che si tocca vince, l'altro si
//    apre» — sta in `bindPeriodo`, dove ci sono i valori e lo store. Questo
//    componente RENDE e basta: due sedi per la stessa regola sarebbero due
//    regole appena una lista chiama `bindPeriodo` senza `<FiltroPeriodo>`.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import DatePicker from 'primevue/datepicker'
import { DATE_FORMAT } from '../constants'

const props = defineProps({
  // La coppia da `bindPeriodo`: `{ da, a, setDa, setA }` — due ref e due setter.
  periodo: { type: Object, required: true },
  // Le etichette dei due estremi. I default coprono ogni lista di oggi; una
  // lista che filtra su una data DI DOMINIO («Validità dal») le dichiara.
  placeholderDa: { type: String, default: null },
  placeholderA: { type: String, default: null },
})

const { t } = useI18n()

const etichettaDa = computed(() => props.placeholderDa ?? t('common.data_da'))
const etichettaA = computed(() => props.placeholderA ?? t('common.data_a'))
</script>

<template>
  <!-- UN solo elemento per chi lo ospita: nella toolbar in linea e' un blocco
       della riga flex, nella griglia del drawer e' UNA cella (che occupa la
       riga e si divide in due). E' cosi' che «il periodo sta su una riga» vale
       senza che nessuno lo ripeta. -->
  <div class="app-filtro-periodo">
    <DatePicker
      :model-value="periodo.da.value"
      class="app-filter-w-sm"
      :placeholder="etichettaDa"
      :date-format="DATE_FORMAT"
      show-icon
      show-button-bar
      @update:model-value="periodo.setDa"
    />
    <DatePicker
      :model-value="periodo.a.value"
      class="app-filter-w-sm"
      :placeholder="etichettaA"
      :date-format="DATE_FORMAT"
      show-icon
      show-button-bar
      @update:model-value="periodo.setA"
    />
  </div>
</template>
