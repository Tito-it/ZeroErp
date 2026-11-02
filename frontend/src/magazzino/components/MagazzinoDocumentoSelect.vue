<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la tendina del MAGAZZINO DI UN DOCUMENTO commerciale — partenza e
//        arrivo della bolla, rientro del reso (Lotto 3 D-L3-a, 3-bis D-3b-a;
//        piano-be-fe-magazzino-lotto-3, A2). Regola del 2: lo stesso campo sta
//        sulla testata di due documenti di vendita.
//
// ⭐ Propone solo i magazzini dell'EMITTENTE del documento (M-6: un'operazione
//    non attraversa due emittenti; decisione di Tid del 2026-10-12): il lookup
//    porta `emittente_fiscale_id` per riga e il filtro e' quello di
//    `LookupSelect`. Senza emittente (create, prima del default) li mostra tutti
//    quelli visibili. La regola resta del DB (`script.fn_magazzino_dell_emittente`):
//    qui si evita solo di proporre una scelta che verrebbe rifiutata.
// ⭐ `record` + `campo` = il magazzino che il documento HA, letto dal dettaglio
//    (`<campo>_id`, `<campo>_codice`, `<campo>_descrizione`: la forma che i
//    dettagli di bolla e reso portano): se intanto e' stato disattivato la
//    tendina lo mostra lo stesso, marcato «non attivo», invece di un campo
//    vuoto con un valore dentro. Il componente compone la voce da se': i form
//    non la ricostruiscono ognuno a modo suo.
// ⚠️ Quale campo serve, quando, e se e' obbligatorio lo dicono il documento e
//    la capability (il motivo «magazzino mancante» all'emissione): questo
//    componente non lo decide.
import { computed } from 'vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { LOOKUP_REL_MAGAZZINI } from '../vocabolari'

const props = defineProps({
  modelValue: { type: Number, default: null },
  // L'emittente del documento: filtra i magazzini proposti.
  emittenteId: { type: Number, default: null },
  // Il dettaglio del documento e il prefisso del campo (`magazzino`,
  // `magazzino_arrivo`): da li' la voce che il documento ha gia'.
  record: { type: Object, default: null },
  campo: { type: String, default: 'magazzino' },
  // Il magazzino da non proporre: l'arrivo non puo' essere la partenza.
  excludeValue: { type: Number, default: null },
  disabled: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
  placeholder: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const voceCorrente = computed(() => {
  const id = props.record?.[`${props.campo}_id`]
  if (id == null) return null
  return {
    id,
    codice: props.record[`${props.campo}_codice`],
    descrizione: props.record[`${props.campo}_descrizione`],
  }
})
</script>

<template>
  <LookupSelect
    :model-value="modelValue"
    :rel="LOOKUP_REL_MAGAZZINI"
    filter-field="emittente_fiscale_id"
    :filter-value="emittenteId"
    :exclude-value="excludeValue"
    :voce-corrente="voceCorrente"
    :disabled="disabled"
    :invalid="invalid"
    :placeholder="placeholder"
    show-code
    show-clear
    @update:model-value="v => emit('update:modelValue', v ?? null)"
  />
</template>
