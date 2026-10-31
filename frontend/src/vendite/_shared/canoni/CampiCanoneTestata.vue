<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: La sezione «Canoni» della testata di contratto e offerta: come si
//        addebitano i canoni e da che mese si contano i periodi (F-2, F-7). La
//        riga a canone senza generazione segue la testata; il passaggio
//        offerta → contratto le copia.
// ⚠️ Lo spegnimento arriva come DUE booleani e non come funzione: il drawer
//    scrive per esteso `testata.bloccato('generazione_canone')`, ed e' li' che
//    lo legge il presidio `campiFormTestata.spec.js`.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import { opzioniGenerazioneCanone, opzioniMesePartenza } from './campiCanone'

defineProps({
  bloccatoGenerazione: { type: Boolean, default: false },
  bloccatoMese: { type: Boolean, default: false },
  campiErrati: { type: Array, default: () => [] },
})

const generazione = defineModel('generazione', { type: String, default: null })
const mese = defineModel('mese', { type: Number, default: null })

const { t, locale } = useI18n()
const opzioniGenerazione = computed(() => opzioniGenerazioneCanone(t))
const opzioniMese = computed(() => opzioniMesePartenza(locale.value))
</script>

<template>
  <h4>{{ t('vendite.canoni.section_canoni') }}</h4>
  <div class="form-grid-2col">
    <div class="form-field">
      <label>{{ t('vendite.canoni.field_generazione_canone') }}</label>
      <Select
        v-model="generazione"
        :options="opzioniGenerazione"
        option-label="label" option-value="value"
        :placeholder="t('vendite.canoni.canoni_predefinito')"
        :disabled="bloccatoGenerazione"
        :invalid="campiErrati.includes('generazione_canone')"
      />
    </div>
    <div class="form-field">
      <label>{{ t('vendite.canoni.field_mese_partenza_canone') }}</label>
      <Select
        v-model="mese"
        :options="opzioniMese"
        option-label="label" option-value="value"
        :placeholder="t('vendite.canoni.canoni_predefinito')"
        :disabled="bloccatoMese"
        :invalid="campiErrati.includes('mese_partenza_canone')"
      />
      <small class="app-text-muted">{{ t('vendite.canoni.hint_mese_partenza_canone') }}</small>
    </div>
  </div>
</template>
