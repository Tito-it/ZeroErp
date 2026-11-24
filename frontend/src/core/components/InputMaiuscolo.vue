<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Un campo di testo che scrive in MAIUSCOLO mentre si digita: per i
//        valori il cui dominio e' maiuscolo (codice destinatario SDI,
//        estensione del civico). Nasce il 2026-10-10 (regola del 2, ok Tid,
//        brief-db-character-n-spazi-di-riempimento §6.1): la stessa riga
//        `@update:model-value="v => x = (v || '').toUpperCase()"` stava in
//        IndirizzoDrawer, IndirizzoSoggettoForm e DatiSocietariForm.
//
// Uso:
//   <InputMaiuscolo v-model="form.codice_sdi" maxlength="7"
//                   :invalid="campiErrati.includes('codice_sdi')" :disabled="disabled" />
//   <InputMaiuscolo v-model="form.codice_fiscale" senza-spazi />   (CF, IBAN…)
//
// ⭐ 2026-11-24 (brief-be-fe-BB-audit §7.1 F-2): la forma e il cursore stanno
//    in `core/utils/maiuscolo.js`, che usa anche l'IBAN (un `AutoComplete`).
//    `senzaSpazi` ha preso il posto di `normalizeUpperNoSpaces`, ritirato.
//
// ⭐ E' un aiuto di digitazione, non una regola: la forma del valore la decide
//    il DB (CHECK e guard), che risponde col campo in errore.
// ⚠️ Il vuoto resta stringa vuota, come per un `InputText`: il passaggio a
//    NULL e' del backend (`optional_str`), non del campo.
// ⚠️ Gli attributi non dichiarati (`maxlength`, `invalid`, `disabled`, `id`…)
//    passano all'`InputText`, che e' l'unica radice.

import { ref } from 'vue'
import InputText from 'primevue/inputtext'
import { riscriviDigitato } from '../utils/maiuscolo'

const props = defineProps({
  // Toglie ogni spazio mentre si digita (IBAN, codice fiscale).
  senzaSpazi: { type: Boolean, default: false },
})
const valore = defineModel({ type: String, default: '' })
const campo = ref(null)

// Scopo: riscrive il valore digitato in maiuscolo, col cursore dov'era.
function aggiorna(v) {
  valore.value = riscriviDigitato(campo.value?.$el, v, { senzaSpazi: props.senzaSpazi })
}
</script>

<template>
  <InputText ref="campo" :model-value="valore" @update:model-value="aggiorna" />
</template>
