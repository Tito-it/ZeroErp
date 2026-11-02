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
//
// ⭐ E' un aiuto di digitazione, non una regola: la forma del valore la decide
//    il DB (CHECK e guard), che risponde col campo in errore.
// ⚠️ Il vuoto resta stringa vuota, come per un `InputText`: il passaggio a
//    NULL e' del backend (`optional_str`), non del campo.
// ⚠️ Gli attributi non dichiarati (`maxlength`, `invalid`, `disabled`, `id`…)
//    passano all'`InputText`, che e' l'unica radice.

import { ref, nextTick } from 'vue'
import InputText from 'primevue/inputtext'

const valore = defineModel({ type: String, default: '' })
const campo = ref(null)

// Scopo: riscrive il valore digitato in maiuscolo.
// ⚠️ Quando la riscrittura cambia il testo, Vue riassegna il valore all'input
//    e il cursore salta in fondo: chi corregge una lettera in mezzo si
//    ritroverebbe a scrivere alla fine. Si rimette il cursore dov'era.
function aggiorna(v) {
  const scritto = v || ''
  const maiuscolo = scritto.toUpperCase()
  const input = campo.value?.$el
  const inizio = input?.selectionStart
  const fine = input?.selectionEnd
  valore.value = maiuscolo
  if (maiuscolo !== scritto && inizio != null) {
    nextTick(() => input.setSelectionRange(inizio, fine))
  }
}
</script>

<template>
  <InputText ref="campo" :model-value="valore" @update:model-value="aggiorna" />
</template>
