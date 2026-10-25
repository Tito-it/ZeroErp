<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: I campi della chiave fisica di un indirizzo dopo la via — civico,
//        estensione, palazzina, scala, piano, interno — come colonne di
//        `anagrafiche.indirizzi_dettaglio`. Nasce il 2026-10-25 (regola del 2,
//        ok Tid, brief-db-unicita-civico-indirizzi-dettaglio §6): lo stesso
//        blocco stava in IndirizzoDrawer e IndirizzoSoggettoForm.
//
// Uso:
//   <CivicoDettaglioCampi :form="addr.form" :campi-errati="campiErrati" :disabled="disabled" />
//
// ⭐ La forma dei valori la decide il DB (normalize + guard della chiave), che
//    risponde col campo in errore: qui nessuna validazione da ricopiare.

import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import InputMaiuscolo from '../../core/components/InputMaiuscolo.vue'

const { t } = useI18n()

// Form reattivo del padre via defineModel: il figlio muta `form.value.xxx`
// (oggetto condiviso per riferimento), senza violare no-mutating-props.
const form = defineModel('form', { type: Object, required: true })

defineProps({
  // I nomi dei campi che il backend chiede di correggere (`campiErrati` del
  // drawer): il guard della chiave li manda per civico e dettagli.
  campiErrati: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false }
})
</script>

<template>
  <div class="form-grid-2col">
    <div class="form-field">
      <label>{{ t('indirizzi.campo_civico') }}</label>
      <!-- :min="0" e non "1": PrimeVue riporta al minimo il valore sotto soglia
           (blur, tasto Home), e uno 0 diventerebbe in silenzio il civico 1, un
           altro indirizzo. Con 0 il segno meno non si digita; lo 0 lo rifiuta il
           DB col campo (D2-a, SNC = campo vuoto). -->
      <InputNumber v-model="form.civico" :use-grouping="false" :min="0" :disabled="disabled" :invalid="campiErrati.includes('civico')" />
    </div>
    <div class="form-field">
      <label>{{ t('indirizzi.campo_estensione') }}</label>
      <InputMaiuscolo v-model="form.estensione_civico" :disabled="disabled" :invalid="campiErrati.includes('estensione_civico')" />
    </div>
    <div class="form-field">
      <label>{{ t('indirizzi.campo_palazzina') }}</label>
      <InputText v-model="form.palazzina" :disabled="disabled" :invalid="campiErrati.includes('palazzina')" />
    </div>
    <div class="form-field">
      <label>{{ t('indirizzi.campo_scala') }}</label>
      <InputText v-model="form.scala" :disabled="disabled" :invalid="campiErrati.includes('scala')" />
    </div>
    <div class="form-field">
      <label>{{ t('indirizzi.campo_piano') }}</label>
      <InputText v-model="form.piano" :disabled="disabled" :invalid="campiErrati.includes('piano')" />
    </div>
    <div class="form-field">
      <label>{{ t('indirizzi.campo_interno') }}</label>
      <InputText v-model="form.interno" :disabled="disabled" :invalid="campiErrati.includes('interno')" />
    </div>
  </div>
</template>
