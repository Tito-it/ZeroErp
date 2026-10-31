<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: La tendina della PERIODICITA' di un canone (`config.periodicita`, il
//        lookup generico, D-6): sulla riga a canone di contratto e offerta, sulla
//        riga e sul kit del listino. Il valore e' il `codice`, quello della FK;
//        l'ordine e' il ritmo (`mesi`, la colonna extra del lookup), non
//        l'alfabeto.
// ⭐ Regola del 2 anticipata (ok Tid 2026-10-31): tre consumatori nello stesso
//    giro; la chiave del lookup e il suo ordinamento in un posto solo — la cache
//    globale tiene il transform del PRIMO che la chiede.
// ⛔ Che la periodicita' sia obbligatoria lo dice il DB (il controllo
//    all'attivazione del listino, il guard della riga): la tendina non lo ricopia.
import LookupSelect from '../../../core/components/LookupSelect.vue'

defineProps({
  placeholder: { type: String, default: '' },
  showClear: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
})

const model = defineModel({ type: String, default: null })

function perRitmo(res) {
  return [...(res?.data?.data?.results ?? [])].sort((a, b) => (a.mesi ?? 0) - (b.mesi ?? 0))
}
</script>

<!-- `invalid` non e' una prop di LookupSelect: passa al suo Select (radice
     unica) come attributo. Niente ricerca: sei voci. -->
<template>
  <LookupSelect
    v-model="model"
    rel="config.periodicita"
    value-field="codice"
    :transform="perRitmo"
    :filter="false"
    :placeholder="placeholder"
    :show-clear="showClear"
    :disabled="disabled"
    :invalid="invalid"
  />
</template>
