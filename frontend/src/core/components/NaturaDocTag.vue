<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL Tag della NATURA di un documento fiscale (fattura, nota di
//        credito, nota di debito), in lista e in scheda.
//
// Estratto il 2026-09-17 alla rilettura critica del pezzo B di D19: lo stesso
// Tag — `descrizione || codice_interno`, severity da `naturaDocSeverity` — e
// lo stesso predicato «si dichiara solo se NON e' una fattura» stavano in
// cinque file (`FatturaDrawer`, `FattureSearchTable`, `LottoDrawer`, e i due
// nuovi del drawer distinta). Il predicato, in particolare, era la STESSA riga
// copiata tre volte: `!!codice && codice !== NATURA_DOC.FATTURA`.
//
// ⭐ DUE MODI, e li decide il contesto:
//   - default: si rende SOLO se la natura non e' ordinaria. E' la scheda e la
//     riga di un incasso: «Fattura» su una fattura e' rumore che toglie forza
//     al caso che conta — la nota di credito, che su una riga di incasso e'
//     il caso in cui il cliente ce la paga (D19-e) e va VISTA.
//   - `sempre`: si rende qualunque natura, e `—` se manca. E' la COLONNA
//     «Natura» di una lista, dove una cella vuota si leggerebbe come dato perso.
//
// ⚠️ `FATTURA` e' il default della colonna a DB: una testata senza natura e'
//    una fattura, non un dato mancante. ⛔ E mai `danger`: una nota di credito
//    non e' un errore, e' un documento di segno opposto — lo decide la mappa in
//    `severity.js`, non chi monta il Tag.
import { computed } from 'vue'
import Tag from 'primevue/tag'

import { NATURA_DOC } from '../constants'
import { naturaDocSeverity } from '../utils/severity'

const props = defineProps({
  // `natura_doc_codice_interno` del documento.
  codice: { type: [String, null], default: null },
  // `natura_doc_descrizione`; il ripiego e' il codice, fail-visible.
  descrizione: { type: [String, null], default: null },
  // `true` = anche «Fattura», e `—` se manca (colonna di lista).
  sempre: { type: Boolean, default: false },
})

// Scopo: «e' una natura che merita di essere detta?».
const nonOrdinaria = computed(
  () => !!props.codice && props.codice !== NATURA_DOC.FATTURA,
)
const visibile = computed(() => (props.sempre ? !!props.codice : nonOrdinaria.value))
</script>

<template>
  <Tag
    v-if="visibile"
    :value="descrizione || codice"
    :severity="naturaDocSeverity(codice)"
  />
  <span v-else-if="sempre">—</span>
</template>
